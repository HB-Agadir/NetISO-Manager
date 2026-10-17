"""What the console holds, and moving things to and from it.

Built on what was found on a real console on 2026-10-16:

- Aurora's FTP root lists the drives that are plugged in (Hdd1, Usb0...).
- Its FTP server answers XCRC <path> with the CRC32 of a remote file, so a
  copy is checked without downloading it again.
- content.db / settings.db: ContentItems (games), ScanPaths and MountedDevices
  (which drive a game lives on), UserRecentGames (date of each launch, per
  profile), TitleUpdates.
- Game:\\Data\\GameData\\<TitleID>_<n>\\GameCoverInfo.bin is JSON listing the
  game's covers on XboxUnity, as JPEG/PNG addresses.
- Title updates and DLC are STFS packages: content type at 0x344, Title ID at
  0x360, display name (UTF-16) at 0x411. They go in
  Content\\0000000000000000\\<TitleID>\\<content type>\\.
- Aurora's web server starts a title with POST /title/launch, form fields
  path (device path of the folder), exec (file name), type (0 = xex).

Nothing here deletes anything on the console.
"""

import datetime
import ftplib
import json
import os
import re
import sqlite3
import struct
import tempfile
import urllib.parse
import zlib

import netiso_console
import netiso_nova
from netiso_i18n import tr

CONTENT_ROOT = "/Hdd1/Content/0000000000000000"
GAMEDATA_ROOT = "/Game/Data/GameData"
SYSTEM_DRIVES = {"Game", "System", "OnBoardMU", "HddX", "Flash"}
FTP_TO_DEVICE = {"Hdd1": "\\Device\\Harddisk0\\Partition1"}
STFS_MAGICS = (b"LIVE", b"PIRS", b"CON ")
CONTENT_TYPES = {0x000B0000: "title_update", 0x00000002: "dlc"}
CHUNK = 1024 * 1024


class TransferError(netiso_console.ConsoleError):
    pass


# ---- drives

def console_drives(ftp):
    """Storage the user cares about: the hard disk and any USB drive plugged in."""
    return [name for name, is_dir in netiso_console.list_dir(ftp, "/")
            if is_dir and name not in SYSTEM_DRIVES]


# ---- checked transfers

def remote_crc32(ftp, path):
    """CRC32 that Aurora's FTP server computes on the console (XCRC command)."""
    reply = ftp.sendcmd("XCRC " + path)
    values = re.findall(r"\b[0-9A-Fa-f]{8}\b", reply)
    if not values:
        raise TransferError(tr("verify_failed", path=path))
    value = values[-1]
    return int(value, 16)


def _ensure_dirs(ftp, folder):
    path = ""
    for part in folder.strip("/").split("/"):
        path += "/" + part
        try:
            ftp.mkd(path)
        except ftplib.error_perm:
            pass  # already there


def upload_verified(ftp, local_path, remote_path, progress=None):
    """Streams a file to the console, then compares its CRC32 on both sides."""
    _ensure_dirs(ftp, remote_path.rsplit("/", 1)[0])
    total = os.path.getsize(local_path)
    state = {"crc": 0, "done": 0}

    def sent(block):
        state["crc"] = zlib.crc32(block, state["crc"])
        state["done"] += len(block)
        if progress:
            progress(state["done"], total)

    with open(local_path, "rb") as f:
        ftp.storbinary("STOR " + remote_path, f, CHUNK, callback=sent)
    if remote_crc32(ftp, remote_path) != state["crc"]:
        raise TransferError(tr("verify_failed", path=remote_path))
    return state["crc"]


def download_verified(ftp, remote_path, local_path, progress=None, total=None):
    """Copies a console file to the PC, then compares its CRC32 on both sides."""
    os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
    if total is None:
        try:
            total = ftp.size(remote_path)
        except ftplib.Error:
            total = 0
    state = {"crc": 0, "done": 0}
    partial = local_path + ".part"
    with open(partial, "wb") as out:
        def received(block):
            out.write(block)
            state["crc"] = zlib.crc32(block, state["crc"])
            state["done"] += len(block)
            if progress:
                progress(state["done"], total)
        ftp.retrbinary("RETR " + remote_path, received, CHUNK)
    if remote_crc32(ftp, remote_path) != state["crc"]:
        os.remove(partial)
        raise TransferError(tr("verify_failed", path=remote_path))
    os.replace(partial, local_path)
    return state["crc"]


# ---- title updates and DLC

def stfs_info(path):
    """(kind, title_id, content_type, display name) of a title update or DLC file, or None."""
    try:
        with open(path, "rb") as f:
            header = f.read(0x500)
    except OSError:
        return None
    if len(header) < 0x500 or header[:4] not in STFS_MAGICS:
        return None
    content_type, = struct.unpack_from(">I", header, 0x344)
    title_id, = struct.unpack_from(">I", header, 0x360)
    name = header[0x411:0x411 + 256].decode("utf-16-be", "replace").split("\0")[0].strip()
    return CONTENT_TYPES.get(content_type, "other"), title_id, content_type, name


def package_destination(path, info):
    """Where the console expects a package: Content\\0000000000000000\\<TitleID>\\<type>\\<file>."""
    _kind, title_id, content_type, _name = info
    return "%s/%08X/%08X/%s" % (CONTENT_ROOT, title_id, content_type, os.path.basename(path))


def install_package(ftp, path, progress=None):
    """Copies a title update or DLC file to its place on the console, checked."""
    info = stfs_info(path)
    if info is None or info[0] == "other":
        raise TransferError(tr("not_a_package", path=os.path.basename(path)))
    destination = package_destination(path, info)
    upload_verified(ftp, path, destination, progress)
    return destination


# ---- game usage, from Aurora's databases

def filetime_to_datetime(value):
    """Windows FILETIME (100 ns since 1601), as Aurora stores dates, to a local datetime."""
    if not value:
        return None
    try:
        return datetime.datetime.fromtimestamp(value / 1e7 - 11644473600)
    except (OverflowError, OSError, ValueError):
        return None


def _open_db(data):
    handle, path = tempfile.mkstemp(suffix=".db")
    with os.fdopen(handle, "wb") as f:
        f.write(data)
    return sqlite3.connect(path), path


def game_usage(content_db, settings_db, skip_folder="\\NetISO"):
    """Games Aurora knows, with the last time any profile launched them.

    Returns [{"id", "title", "title_id", "folder", "drive", "last_played",
    "added"}], never played first, then oldest launch first. Tiles under
    skip_folder (NetISO's own) are left out: they take no space.
    """
    content, content_path = _open_db(content_db)
    settings, settings_path = _open_db(settings_db)
    try:
        drives = {row[0]: row[1] for row in content.execute(
            "SELECT DeviceId, DeviceName FROM MountedDevices")}
        scan_drive = {row[0]: drives.get(row[1], "?") for row in settings.execute(
            "SELECT Id, DeviceId FROM ScanPaths")}
        last = {}
        for content_id, when in settings.execute(
                "SELECT ContentId, MAX(DateTime) FROM UserRecentGames GROUP BY ContentId"):
            last[content_id] = when
        games = []
        skip = skip_folder.lower().rstrip("\\") + "\\"
        for row in content.execute("SELECT Id, TitleName, TitleId, Directory, ScanPathId, DateAdded "
                                   "FROM ContentItems"):
            content_id, title, title_id, folder, scan_id, added = row
            if (folder or "").lower().startswith(skip):
                continue
            games.append({"id": content_id, "title": title, "title_id": title_id, "folder": folder,
                          "drive": scan_drive.get(scan_id, "?"),
                          "last_played": filetime_to_datetime(last.get(content_id)),
                          "added": filetime_to_datetime(added)})
    finally:
        content.close()
        settings.close()
        os.remove(content_path)
        os.remove(settings_path)
    never = datetime.datetime.min
    games.sort(key=lambda g: (g["last_played"] is not None, g["last_played"] or never))
    return games


def read_usage(ftp):
    """game_usage() on the databases read from the running Aurora."""
    content = netiso_console.read_file(ftp, netiso_console.AURORA_CONTENT_DB)
    settings = netiso_console.read_file(ftp, netiso_console.AURORA_SETTINGS_DB)
    if content is None or settings is None:
        raise TransferError(tr("aurora_db_missing"))
    return game_usage(content, settings)


# ---- covers

def cover_urls(cover_info):
    """Cover addresses from a GameCoverInfo.bin, official covers first.

    Returns [(front, thumbnail)]: front is a PNG, thumbnail a small JPEG.
    """
    try:
        entries = json.loads(cover_info.decode("utf-8", "replace"))
    except ValueError:
        return []
    entries = [e for e in entries if isinstance(e, dict) and e.get("front")]
    entries.sort(key=lambda e: not e.get("official"))
    return [(e["front"], e.get("thumbnail") or e["front"]) for e in entries]


def read_cover_urls(ftp, title_id):
    """cover_urls() for a game, read from Aurora's game data on the console."""
    prefix = "%08X_" % title_id
    for name, is_dir in netiso_console.list_dir(ftp, GAMEDATA_ROOT):
        if is_dir and name.upper().startswith(prefix):
            data = netiso_console.read_file(ftp, "%s/%s/GameCoverInfo.bin" % (GAMEDATA_ROOT, name))
            if data:
                urls = cover_urls(data)
                if urls:
                    return urls
    return []


# ---- launching a title on the console from the PC

def device_folder(ftp_folder):
    """FTP folder (/Hdd1/NetISO/Halo Wars) to the device path Aurora's launcher wants."""
    parts = ftp_folder.strip("/").split("/")
    device = FTP_TO_DEVICE.get(parts[0])
    if device is None:
        raise TransferError(tr("launch_drive_unsupported", drive=parts[0]))
    return device + "".join("\\" + p for p in parts[1:])


def restart_aurora_if_idle(host, user, password):
    """Starts Aurora again when it is what the console shows (never during a game).

    Aurora runs its list filters only while building the list: the NetISO games
    appear or vanish at its next start. Called when the server starts or stops.
    Returns True when Aurora was restarted.
    """
    client = netiso_nova.NovaClient(host, user or "xboxhttp", password or "xboxhttp")
    try:
        path = json.loads(client._get("/title")).get("path", "")
    except (netiso_nova.NovaError, ValueError):
        return False
    if not path.lower().endswith("\\aurora.xex"):
        return False
    folder, executable = path.rsplit("\\", 1)
    body = urllib.parse.urlencode({"path": folder, "exec": executable, "type": "0"}).encode()
    try:
        client._request("/title/launch", data=body)
    except netiso_nova.NovaError:
        return False
    return True


def launch_on_console(host, user, password, ftp_folder, executable="default.xex"):
    """Asks Aurora to start a title. The console leaves whatever it is running."""
    client = netiso_nova.NovaClient(host, user or "xboxhttp", password or "xboxhttp")
    body = urllib.parse.urlencode({"path": device_folder(ftp_folder), "exec": executable,
                                   "type": "0"}).encode()
    client.login()
    client._request("/title/launch", data=body)
