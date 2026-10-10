"""Talks to the console over Aurora's FTP server: finds installed games, syncs tiles."""

import ftplib
import hashlib
import io
import struct

import netiso_iso

CONTENT_ROOT = "Content/0000000000000000"
GAME_CONTENT_TYPES = ("00007000", "00004000")  # Games on Demand, installed disc
TILE_FILES = ("default.xex", "netiso.cfg", "netiso_stub.log")
XEX_HEADER_READ = 0x8000
SCAN_DEPTH = 2


class ConsoleError(Exception):
    pass


def connect(host, user, password, port=21):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=15)
        ftp.login(user, password)
        return ftp
    except (OSError, ftplib.Error) as error:
        raise ConsoleError("connexion FTP impossible vers %s: %s. Aurora doit etre ouvert "
                           "sur la console." % (host, error))


def parse_list_line(line):
    """Returns (name, is_dir) for a Unix-style LIST line, or None."""
    parts = line.split(None, 8)
    if len(parts) < 9 or parts[0][0] not in "-dl":
        return None
    return parts[8], parts[0][0] == "d"


def list_dir(ftp, path):
    """Returns [(name, is_dir)], empty when the folder does not exist."""
    lines = []
    try:
        ftp.cwd(path)
        ftp.retrlines("LIST", lines.append)
    except ftplib.Error:
        return []
    entries = [parse_list_line(line) for line in lines]
    return [e for e in entries if e and e[0] not in (".", "..")]


def read_head(ftp, path, size):
    """Reads the first bytes of a remote file without downloading the rest."""
    data = b""
    conn = ftp.transfercmd("RETR " + path)
    try:
        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                break
            data += chunk
    finally:
        conn.close()
    try:
        ftp.voidresp()
    except ftplib.Error:
        pass  # the server reports the interrupted transfer; the bytes are already read
    return data


def xex_game_key(header):
    """Returns (title_id, disc) from the start of a default.xex, or None."""
    try:
        offset = netiso_iso.xex_execution_info_offset(header)
        _media, _ver, _base, title_id, _plat, _type, disc, _discs = struct.unpack_from(
            ">IIIIBBBB", header, offset)
    except (netiso_iso.IsoError, struct.error):
        return None
    return title_id, disc


def installed_games(ftp, game_folders, drives, skip_root, progress=None):
    """Returns the set of (title_id, disc) installed on the console.

    Looks for extracted games (a default.xex up to two levels under each game
    folder) and for Games on Demand under each drive's Content folder. Tiles
    under skip_root are ours and are not counted.
    """
    skip_root = "/" + skip_root.strip("/").lower()
    found = set()

    def walk(folder, depth):
        entries = list_dir(ftp, folder)
        xex = [name for name, is_dir in entries if not is_dir and name.lower() == "default.xex"]
        if xex:
            key = xex_game_key(read_head(ftp, "%s/%s" % (folder, xex[0]), XEX_HEADER_READ))
            if key:
                found.add(key)
                if progress:
                    progress("%s  %08X" % (folder, key[0]))
            return
        if depth > 0:
            for name, is_dir in entries:
                child = "%s/%s" % (folder, name)
                if is_dir and child.lower() != skip_root:
                    walk(child, depth - 1)

    for folder in game_folders:
        folder = "/" + folder.strip("/")
        if folder.lower() != skip_root:
            walk(folder, SCAN_DEPTH)

    for drive in drives:
        content = "/%s/%s" % (drive.strip("/"), CONTENT_ROOT)
        for name, is_dir in list_dir(ftp, content):
            if not is_dir or len(name) != 8:
                continue
            try:
                title_id = int(name, 16)
            except ValueError:
                continue
            types = {n for n, d in list_dir(ftp, "%s/%s" % (content, name)) if d}
            if types.intersection(GAME_CONTENT_TYPES):
                # A container does not tell its disc number from its folder name.
                found.add((title_id, None))
    return found


def is_installed(game, installed):
    return (game.title_id, game.disc) in installed or (game.title_id, None) in installed


def plan_sync(games, installed, existing_tiles):
    """Decides what to do with each tile.

    Returns (to_send, to_remove): games whose tile must be on the console, and
    names of tiles to delete because the game is installed on the console or
    its ISO is gone from the PC.
    """
    to_send = [game for game in games if not is_installed(game, installed)]
    wanted = {game.name.lower() for game in to_send}
    to_remove = [name for name in existing_tiles if name.lower() not in wanted]
    return to_send, to_remove


def existing_tiles(ftp, remote_root):
    """Names of the folders under remote_root that hold one of our tiles."""
    tiles = []
    for name, is_dir in list_dir(ftp, remote_root):
        if is_dir:
            files = {n.lower() for n, d in list_dir(ftp, "%s/%s" % (remote_root, name)) if not d}
            if "netiso.cfg" in files:
                tiles.append(name)
    return tiles


def remove_tile(ftp, remote_root, name):
    """Deletes one of our tiles. Only the files a tile is made of are removed."""
    tile_dir = "%s/%s" % (remote_root, name)
    present = {n.lower(): n for n, d in list_dir(ftp, tile_dir) if not d}
    for filename in TILE_FILES:
        if filename in present:
            ftp.delete("%s/%s" % (tile_dir, present[filename]))
    try:
        ftp.cwd(remote_root)
        ftp.rmd(tile_dir)
    except ftplib.Error:
        pass  # the folder holds something else; leave it


def _ensure_dir(ftp, path):
    try:
        ftp.cwd(path)
        return
    except ftplib.Error:
        pass
    try:
        ftp.mkd(path)
    except ftplib.Error as error:
        raise ConsoleError("creation de %s refusee: %s" % (path, error))


def send_tile(ftp, remote_root, name, files):
    """Uploads one tile and reads every file back to check it."""
    tile_dir = "%s/%s" % (remote_root, name)
    _ensure_dir(ftp, remote_root)
    _ensure_dir(ftp, tile_dir)
    for filename, data in files.items():
        path = "%s/%s" % (tile_dir, filename)
        ftp.storbinary("STOR " + path, io.BytesIO(data))
        readback = io.BytesIO()
        ftp.retrbinary("RETR " + path, readback.write)
        if hashlib.sha256(readback.getvalue()).digest() != hashlib.sha256(data).digest():
            raise ConsoleError("%s est different sur la console apres l'envoi" % path)


def sync(settings, games, stub, log):
    """Brings the console's tiles in line with the PC's ISOs.

    Returns {game name: state} where state is "console" (installed there, no
    tile) or "netiso" (tile sent).
    """
    remote_root = "/" + settings["remote_root"].strip("/")
    drives = sorted({f.strip("/").split("/")[0] for f in settings["console_game_folders"]
                     if f.strip("/")} | {remote_root.strip("/").split("/")[0]})
    ftp = connect(settings["console_ip"], settings["ftp_user"], settings["ftp_password"])
    try:
        log("Recherche des jeux deja installes sur la console...")
        installed = installed_games(ftp, settings["console_game_folders"], drives, remote_root)
        log("%d jeu(x) installe(s) sur la console" % len(installed))
        to_send, to_remove = plan_sync(games, installed, existing_tiles(ftp, remote_root))
        for name in to_remove:
            remove_tile(ftp, remote_root, name)
            log("Tuile retiree: %s" % name)
        for number, game in enumerate(to_send, 1):
            send_tile(ftp, remote_root, game.name, netiso_iso.tile_files(stub, game))
            log("  %d/%d  %s" % (number, len(to_send), game.name))
        sent = {game.name for game in to_send}
        return {game.name: "netiso" if game.name in sent else "console" for game in games}
    except (OSError, ftplib.Error) as error:
        raise ConsoleError("erreur FTP: %s" % error)
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass
