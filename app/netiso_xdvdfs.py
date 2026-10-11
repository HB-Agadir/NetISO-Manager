"""Presents a folder of game files as an Xbox 360 disc image, without copying anything.

The console reads a disc by blocks. A VirtualDisc lays the folder out as an
XDVDFS game partition in memory (volume descriptor and directory tables) and
answers each block read from the right place of the right file.
"""

import bisect
import os
import struct

SECTOR = 2048
MAGIC = b"MICROSOFT*XBOX*MEDIA"
# Where a game partition starts on the two disc layouts the NetISO plugin looks for.
XGD2_OFFSET = 0xFD90000
XGD3_OFFSET = 0x2080000
XGD2_MAX_SECTORS = 3400000  # beyond this the game needs the larger XGD3 layout
DESCRIPTOR_SECTOR = 32
ATTRIBUTE_DIRECTORY = 0x10
ATTRIBUTE_FILE = 0x20
MAX_FILE_SIZE = 0xFFFFFFFF
MAX_TABLE_SIZE = 0xFFFF * 4
MAX_OPEN_FILES = 64


class DiscError(Exception):
    pass


def _sectors(size):
    return (size + SECTOR - 1) // SECTOR


def _sort_key(name):
    """XDVDFS directories are search trees ordered by upper-cased name."""
    return name.upper().encode("ascii")


class _Node:
    def __init__(self, name, path, is_dir):
        self.name = name
        self.path = path
        self.is_dir = is_dir
        self.size = 0
        self.sector = 0
        self.children = []
        self.table = b""


def _scan(path, name=""):
    """Reads a folder tree into nodes; names the format cannot hold are refused."""
    node = _Node(name, path, True)
    with os.scandir(path) as entries:
        for entry in entries:
            try:
                encoded = entry.name.encode("ascii")
            except UnicodeEncodeError:
                raise DiscError("non-ASCII file name: %s" % entry.path)
            if len(encoded) > 255:
                raise DiscError("file name too long: %s" % entry.path)
            if entry.is_dir(follow_symlinks=False):
                node.children.append(_scan(entry.path, entry.name))
            elif entry.is_file(follow_symlinks=False):
                child = _Node(entry.name, entry.path, False)
                child.size = entry.stat().st_size
                if child.size > MAX_FILE_SIZE:
                    raise DiscError("file larger than 4 GB: %s" % entry.path)
                node.children.append(child)
    node.children.sort(key=lambda child: _sort_key(child.name))
    return node


def _entry_size(node):
    return (14 + len(node.name) + 3) & ~3


def _tree_order(count):
    """Balanced search tree over sorted entries 0..count-1.

    Returns (order, left, right): the entries in the order they are written
    (a parent before its subtrees) and each entry's child, or None.
    """
    order, left, right = [], {}, {}

    def build(low, high):
        if low > high:
            return None
        middle = (low + high) // 2
        order.append(middle)
        left[middle] = build(low, middle - 1)
        right[middle] = build(middle + 1, high)
        return middle

    build(0, count - 1)
    return order, left, right


def _plan_table(node):
    """Decides where each entry of a directory table goes; returns the table size.

    An entry never straddles two sectors: the rest of the sector is left as padding.
    """
    order, left, right = _tree_order(len(node.children))
    offsets, position = {}, 0
    for index in order:
        size = _entry_size(node.children[index])
        if position // SECTOR != (position + size - 1) // SECTOR:
            position = (position // SECTOR + 1) * SECTOR
        offsets[index] = position
        position += size
    node.plan = (order, left, right, offsets)
    size = _sectors(position) * SECTOR
    if size > MAX_TABLE_SIZE:
        raise DiscError("too many files in one folder: %s" % node.path)
    return size


def _write_table(node, size):
    order, left, right, offsets = node.plan
    table = bytearray(b"\xff" * size)
    for index in order:
        child = node.children[index]
        name = child.name.encode("ascii")
        struct.pack_into(
            "<HHIIBB", table, offsets[index],
            offsets[left[index]] // 4 if left[index] is not None else 0,
            offsets[right[index]] // 4 if right[index] is not None else 0,
            child.sector, child.size,
            ATTRIBUTE_DIRECTORY if child.is_dir else ATTRIBUTE_FILE, len(name))
        table[offsets[index] + 14:offsets[index] + 14 + len(name)] = name
    return bytes(table)


class VirtualDisc:
    """A game folder seen as a disc image: size in bytes and random-access reads."""

    def __init__(self, folder):
        root = _scan(folder)
        directories = []

        def collect(node):
            if node.children:
                directories.append(node)
            for child in node.children:
                if child.is_dir:
                    collect(child)

        collect(root)
        if not root.children:
            raise DiscError("empty folder: %s" % folder)

        # Directory tables first, then the files, each on a sector boundary.
        sector = DESCRIPTOR_SECTOR + 1
        for node in directories:
            node.size = _plan_table(node)
            node.sector = sector
            sector += node.size // SECTOR
        files = []

        def place(node):
            nonlocal sector
            for child in node.children:
                if child.is_dir:
                    place(child)
                elif child.size:
                    child.sector = sector
                    sector += _sectors(child.size)
                    files.append(child)

        place(root)
        partition_sectors = sector
        self.partition = XGD2_OFFSET if partition_sectors <= XGD2_MAX_SECTORS else XGD3_OFFSET
        self.size = self.partition + partition_sectors * SECTOR
        self.descriptor_offset = self.partition + DESCRIPTOR_SECTOR * SECTOR

        descriptor = bytearray(SECTOR)
        descriptor[:len(MAGIC)] = MAGIC
        struct.pack_into("<II", descriptor, len(MAGIC), root.sector, root.size)
        descriptor[-len(MAGIC):] = MAGIC

        # Everything the image holds, as (offset, length, bytes or file path), in order.
        self._extents = [(self.descriptor_offset, SECTOR, bytes(descriptor))]
        for node in directories:
            self._extents.append((self.partition + node.sector * SECTOR, node.size,
                                  _write_table(node, node.size)))
        for node in files:
            self._extents.append((self.partition + node.sector * SECTOR, node.size, node.path))
        self._starts = [extent[0] for extent in self._extents]
        self._handles = {}

    def read(self, offset, length):
        """Returns length bytes of the image at offset; unused areas read as zeros."""
        out = bytearray(length)
        index = max(bisect.bisect_right(self._starts, offset) - 1, 0)
        end = offset + length
        while index < len(self._extents):
            start, size, source = self._extents[index]
            if start >= end:
                break
            low, high = max(offset, start), min(end, start + size)
            if low < high:
                if isinstance(source, bytes):
                    data = source[low - start:high - start]
                else:
                    handle = self._handles.get(source)
                    if handle is None:
                        if len(self._handles) >= MAX_OPEN_FILES:
                            self.close()
                        handle = self._handles[source] = open(source, "rb", buffering=0)
                    handle.seek(low - start)
                    data = handle.read(high - low)
                out[low - offset:low - offset + len(data)] = data
            index += 1
        return bytes(out)

    def close(self):
        for handle in self._handles.values():
            handle.close()
        self._handles = {}


class IsoFile:
    """An ISO file on disk, with the same interface as VirtualDisc."""

    def __init__(self, path):
        self._file = open(path, "rb", buffering=0)
        self._file.seek(0, 2)
        self.size = self._file.tell()
        self.descriptor_offset = None

    def read(self, offset, length):
        self._file.seek(offset)
        return self._file.read(length).ljust(length, b"\0")

    def close(self):
        self._file.close()
