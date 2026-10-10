"""Reads game identifiers from Xbox 360 ISO images and builds Aurora tiles."""

import hashlib
import os
import re
import struct

SECTOR = 2048
XDVDFS_MAGIC = b"MICROSOFT*XBOX*MEDIA"
# Offset of the game partition inside the image, by disc layout.
PARTITION_OFFSETS = (0x2080000, 0xFD90000, 0x18300000, 0)  # XGD3, XGD2, XGD1, raw XISO
XEX_EXECUTION_INFO = 0x00040006
# Offsets inside the XEX security info block.
XEX_HEADER_HASH = 0x164
XEX_HASHED_TAIL = 0x17C
FATX_NAME_MAX = 42


class IsoError(Exception):
    pass


class Game:
    """One ISO on the PC and the identifiers of the game it contains."""

    def __init__(self, path, name, title_id, media_id, disc, discs):
        self.path = path
        self.name = name  # tile folder name, also the name the server lists
        self.title_id = title_id
        self.media_id = media_id
        self.disc = disc
        self.discs = discs
        self.size = os.path.getsize(path)


def find_partition(f):
    for offset in PARTITION_OFFSETS:
        f.seek(offset + 32 * SECTOR)
        if f.read(len(XDVDFS_MAGIC)) == XDVDFS_MAGIC:
            return offset
    raise IsoError("partition de jeu introuvable")


def find_root_file(f, partition, wanted):
    """Returns (sector, size) of a file in the root directory of the partition."""
    f.seek(partition + 32 * SECTOR + len(XDVDFS_MAGIC))
    root_sector, root_size = struct.unpack("<II", f.read(8))
    f.seek(partition + root_sector * SECTOR)
    table = f.read(root_size)
    wanted = wanted.lower()
    pending = [0]
    seen = set()
    while pending:
        pos = pending.pop()
        if pos in seen or pos + 14 > len(table):
            continue
        seen.add(pos)
        left, right, sector, size, _attr, name_len = struct.unpack_from("<HHIIBB", table, pos)
        if left == 0xFFFF and right == 0xFFFF:
            continue
        name = table[pos + 14:pos + 14 + name_len].decode("ascii", "replace")
        if name.lower() == wanted:
            return sector, size
        # The directory is a binary tree; child offsets are in 4-byte units.
        for child in (left, right):
            if child not in (0, 0xFFFF):
                pending.append(child * 4)
    raise IsoError("%s absent de la racine du disque" % wanted)


def xex_execution_info_offset(header):
    if header[:4] != b"XEX2":
        raise IsoError("default.xex n'est pas un fichier XEX2")
    count = struct.unpack_from(">I", header, 0x14)[0]
    for i in range(count):
        key, value = struct.unpack_from(">II", header, 0x18 + i * 8)
        if key == XEX_EXECUTION_INFO:
            return value
    raise IsoError("default.xex sans en-tete d'execution")


def read_iso_ids(path):
    """Returns (title_id, media_id, disc, discs) read from default.xex inside the ISO."""
    with open(path, "rb") as f:
        partition = find_partition(f)
        sector, size = find_root_file(f, partition, "default.xex")
        f.seek(partition + sector * SECTOR)
        header = f.read(min(size, 0x10000))
    offset = xex_execution_info_offset(header)
    media_id, _version, _base, title_id, _platform, _exe_type, disc, discs = struct.unpack_from(
        ">IIIIBBBB", header, offset)
    return title_id, media_id, disc, discs


def xex_header_hash(data):
    """SHA-1 the kernel expects in the XEX security info for these headers.

    It covers the headers after the hash field's block (from the allowed
    media types to the start of the image), then the start of the file up to
    the RSA signature.
    """
    data_offset, _reserved, security = struct.unpack_from(">III", data, 8)
    covered = bytes(data[security + XEX_HASHED_TAIL:data_offset]) + bytes(data[:security + 8])
    return hashlib.sha1(covered).digest()


def stamp_stub(stub, game):
    """Returns a copy of the launcher stub carrying the game's Title ID and Media ID."""
    data = bytearray(stub)
    security = struct.unpack_from(">I", data, 0x10)[0]
    hash_at = security + XEX_HEADER_HASH
    if xex_header_hash(data) != bytes(data[hash_at:hash_at + 20]):
        raise IsoError("lanceur inattendu: empreinte d'en-tete non reconnue")
    offset = xex_execution_info_offset(data)
    struct.pack_into(">I", data, offset, game.media_id)
    struct.pack_into(">I", data, offset + 12, game.title_id)
    # The IDs sit in the hashed part of the headers: without a fresh hash the
    # console refuses to load the file.
    data[hash_at:hash_at + 20] = xex_header_hash(data)
    return bytes(data)


def tile_name(iso_path, taken):
    """Folder name for the tile: FATX-safe, at most 42 characters, unique."""
    stem = os.path.splitext(os.path.basename(iso_path))[0]
    name = re.sub(r"[^A-Za-z0-9 !#$%&'()\-.@\[\]^_`{}~]", "_", stem).strip(" .")
    name = name[:FATX_NAME_MAX].rstrip(" .") or "game"
    base, n = name, 2
    while name.lower() in taken:
        suffix = " %d" % n
        name = base[:FATX_NAME_MAX - len(suffix)] + suffix
        n += 1
    taken.add(name.lower())
    return name


def find_isos(folders, recursive):
    found = []
    for folder in folders:
        if not os.path.isdir(folder):
            continue
        if recursive:
            for root, _dirs, files in os.walk(folder):
                found += [os.path.join(root, n) for n in files if n.lower().endswith(".iso")]
        else:
            found += [os.path.join(folder, n) for n in os.listdir(folder)
                      if n.lower().endswith(".iso")]
    unique = {os.path.normcase(os.path.abspath(p)): p for p in found}
    return sorted(unique.values(), key=lambda p: os.path.basename(p).lower())


def scan(folders, recursive):
    """Returns (games, errors) for every ISO in the folders; errors are (path, message)."""
    games, errors, taken = [], [], set()
    for path in find_isos(folders, recursive):
        try:
            title_id, media_id, disc, discs = read_iso_ids(path)
        except (IsoError, OSError, struct.error) as error:
            errors.append((path, str(error)))
            continue
        games.append(Game(path, tile_name(path, taken), title_id, media_id, disc, discs))
    return games, errors


def tile_files(stub, game):
    """Returns the files of a game's tile as {filename: bytes}."""
    return {
        "default.xex": stamp_stub(stub, game),
        "netiso.cfg": (game.name + "\r\n").encode("ascii"),
    }
