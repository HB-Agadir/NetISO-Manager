"""Reads game identifiers from Xbox 360 ISO images and builds Aurora tiles."""

import hashlib
import os
import re
import struct

from netiso_i18n import tr

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
    """One ISO on the PC and the identifiers of the disc it contains."""

    def __init__(self, path, name, title_id, media_id, disc, discs):
        self.path = path
        self.name = name  # readable game title, without region, language or disc tags
        self.title_id = title_id
        self.media_id = media_id
        self.disc = disc
        self.discs = discs
        self.size = os.path.getsize(path)


class Tile:
    """One entry in Aurora: a game, with every disc of it found on the PC."""

    def __init__(self, name, games):
        self.name = name  # tile folder name, also the name the server lists
        self.games = sorted(games, key=lambda game: game.disc)
        self.active = self.games[0].disc  # disc served when the tile is launched

    @property
    def title_id(self):
        return self.games[0].title_id

    @property
    def media_id(self):
        return self.games[0].media_id

    @property
    def multi_disc(self):
        return len(self.games) > 1

    def game(self):
        """The disc currently selected for this tile."""
        for game in self.games:
            if game.disc == self.active:
                return game
        return self.games[0]

    def step_disc(self, step):
        """Selects the following (1) or previous (-1) disc, wrapping around; returns its number."""
        numbers = [game.disc for game in self.games]
        self.active = numbers[(numbers.index(self.game().disc) + step) % len(numbers)]
        return self.active

    def next_disc(self):
        return self.step_disc(1)


def find_partition(f):
    for offset in PARTITION_OFFSETS:
        f.seek(offset + 32 * SECTOR)
        if f.read(len(XDVDFS_MAGIC)) == XDVDFS_MAGIC:
            return offset
    raise IsoError(tr("no_partition"))


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
    raise IsoError(tr("file_missing", name=wanted))


def xex_execution_info_offset(header):
    if header[:4] != b"XEX2":
        raise IsoError(tr("not_xex2"))
    count = struct.unpack_from(">I", header, 0x14)[0]
    for i in range(count):
        key, value = struct.unpack_from(">II", header, 0x18 + i * 8)
        if key == XEX_EXECUTION_INFO:
            return value
    raise IsoError(tr("no_exec_info"))


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
        raise IsoError(tr("bad_stub"))
    offset = xex_execution_info_offset(data)
    struct.pack_into(">I", data, offset, game.media_id)
    struct.pack_into(">I", data, offset + 12, game.title_id)
    # The IDs sit in the hashed part of the headers: without a fresh hash the
    # console refuses to load the file.
    data[hash_at:hash_at + 20] = xex_header_hash(data)
    return bytes(data)


DISC_TAG = re.compile(r"\s*[(\[][^)\]]*dis[ck][^)\]]*[)\]]", re.I)


def clean_title(iso_path):
    """Game title from an ISO file name, without the (region) and (languages) tags.

    Tags that mention a disc, such as (Disc 2) or (Add-On Content Disc), are
    kept: they tell apart discs that are separate entries in Aurora.
    """
    stem = os.path.splitext(os.path.basename(iso_path))[0]
    kept = lambda match: match.group(0) if DISC_TAG.fullmatch(match.group(0)) else " "
    title = re.sub(r"\s*(\([^)]*\)|\[[^\]]*\])", kept, stem)
    title = re.sub(r"\s+", " ", title).strip(" -_.")
    return title or stem


def tile_name(title, taken):
    """Folder name for a tile: FATX-safe, at most 42 characters, unique."""
    name = re.sub(r"[^A-Za-z0-9 !#$%&'()\-.@\[\]^_`{}~]", "_", title).strip(" .")
    name = name[:FATX_NAME_MAX].rstrip(" .") or "game"
    base, n = name, 2
    while name.lower() in taken:
        suffix = " %d" % n
        name = base[:FATX_NAME_MAX - len(suffix)] + suffix
        n += 1
    taken.add(name.lower())
    return name


DISC_NUMBER = re.compile(r"dis[ck]\s*(\d+)", re.I)


def number_discs_from_names(games):
    """Recognises multi-disc sets whose discs do not say so themselves.

    Some games ship several discs that each claim to be "disc 1 of 1". When
    ISOs share a Title ID, all make that claim, and their file names carry
    different disc numbers, those numbers are trusted instead.
    """
    by_title = {}
    for game in games:
        by_title.setdefault(game.title_id, []).append(game)
    for group in by_title.values():
        if len(group) < 2 or any(game.discs > 1 for game in group):
            continue
        numbers = [DISC_NUMBER.search(game.name) for game in group]
        if not all(numbers):
            continue
        numbers = [int(match.group(1)) for match in numbers]
        if len(set(numbers)) != len(numbers):
            continue
        for game, number in zip(group, numbers):
            game.disc, game.discs = number, max(numbers)


def build_tiles(games, group_discs=True):
    """Turns the ISOs into tiles.

    With group_discs, the discs of a multi-disc game share a single tile; a
    second copy of a disc already seen (another region, a duplicate file) gets
    a tile of its own. Without it, every ISO is a tile, as in a plain list.
    """
    if group_discs:
        number_discs_from_names(games)
    groups, order = {}, []
    for game in games:
        grouped = group_discs and game.discs > 1
        key = (game.title_id,) if grouped else (game.title_id, id(game))
        if key in groups and any(other.disc == game.disc for other in groups[key]):
            key = (game.title_id, id(game))
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(game)
    taken = set()
    tiles = [Tile(None, groups[key]) for key in order]
    tiles.sort(key=lambda tile: tile.games[0].name.lower())
    for tile in tiles:
        title = tile.games[0].name
        if tile.multi_disc:
            # One tile stands for every disc: its name must not single one out.
            title = DISC_TAG.sub("", title).strip() or title
        tile.name = tile_name(title, taken)
    return tiles


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


def snapshot(folders, recursive):
    """Returns {path: size} for every ISO in the folders; cheap enough to poll."""
    result = {}
    for path in find_isos(folders, recursive):
        try:
            result[path] = os.path.getsize(path)
        except OSError:
            pass
    return result


def is_being_written(path):
    """True while another program (a copy, a download) still holds the file open for writing."""
    if not os.access(path, os.W_OK):
        return False  # read-only file: nothing is writing to it
    try:
        with open(path, "r+b"):
            return False
    except OSError:
        return True


def scan(folders, recursive, group_discs=True):
    """Returns (tiles, errors) for every ISO in the folders; errors are (path, message)."""
    games, errors = [], []
    for path in find_isos(folders, recursive):
        try:
            title_id, media_id, disc, discs = read_iso_ids(path)
        except (IsoError, OSError, struct.error) as error:
            errors.append((path, str(error)))
            continue
        games.append(Game(path, clean_title(path), title_id, media_id, disc, discs))
    return build_tiles(games, group_discs), errors


def tile_files(stub, tile, message=""):
    """Returns the files of a tile as {filename: bytes}.

    netiso.cfg holds the tile name on its first line, on the second the text
    the launcher shows on the console when the PC cannot be reached, and on
    the third the number of discs of the game.
    """
    config = b"\r\n".join((tile.name.encode("ascii"), message.encode("utf-8"),
                            str(len(tile.games)).encode("ascii"), b""))
    return {"default.xex": stamp_stub(stub, tile), "netiso.cfg": config}
