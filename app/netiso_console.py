"""Talks to the console over Aurora's FTP server: finds installed games, syncs tiles,
installs the plugin configuration."""

import ftplib
import hashlib
import io
import os
import re
import sqlite3
import struct
import sys
import tempfile
import time
import unicodedata

import netiso_iso
from netiso_i18n import tr

CONTENT_ROOT = "Content/0000000000000000"
GAME_CONTENT_TYPES = ("00007000", "00004000")  # Games on Demand, installed disc
TILE_FILES = ("default.xex", "netiso.cfg", "netiso_stub.log")
XEX_HEADER_READ = 0x8000
SCAN_DEPTH = 2
LAUNCH_INI_PATHS = ("/Hdd1/launch.ini", "/Usb0/launch.ini", "/Usb1/launch.ini")
DEFAULT_PLUGIN_PATH = "Hdd:\\Apps\\NetISO.xex"
# Aurora's own folder is the FTP drive "Game" while Aurora is running.
AURORA_CONTENT_DB = "/Game/Data/Databases/content.db"
AURORA_SETTINGS_DB = "/Game/Data/Databases/settings.db"
CLEANUP_SCRIPT_DIR = "/Game/User/Scripts/Utility/NetISO Cleanup"
BACKUP_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NetISOManager",
                          "aurora_backups")
BACKUPS_KEPT = 10
# Tables of Aurora's settings database that point at a content entry by its Id.
CONTENT_REFERENCES = ("UserRecentGames", "UserFavorites", "UserHidden", "TitleSettings")
# NetISO.xex 1.0 by cOz, shipped unmodified with the app. The launcher only
# knows this exact build: it checks the instructions it changes before touching them.
PLUGIN_SHA256 = "3672c88a7a3542746bd43db0f400a6eb4c0b2ca41aa382c4188e02526e8012ea"
# DashLaunch device names and the drive names of Aurora's FTP server.
DEVICES = (("Hdd:", "/Hdd1"), ("Usb:", "/Usb0"))


class ConsoleError(Exception):
    pass


class PluginMissing(ConsoleError):
    """The plugin file is not on the console and none was given to upload."""


def connect(host, user, password, port=21):
    try:
        ftp = ftplib.FTP()
        ftp.connect(host, port, timeout=15)
        ftp.login(user, password)
        return ftp
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_connect_failed", host=host, error=error))


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


def read_file(ftp, path):
    """Returns the content of a remote file, or None when it does not exist."""
    data = io.BytesIO()
    try:
        ftp.retrbinary("RETR " + path, data.write)
    except ftplib.Error:
        return None
    return data.getvalue()


def write_file(ftp, path, data):
    """Uploads a file and reads it back to check it."""
    ftp.storbinary("STOR " + path, io.BytesIO(data))
    if hashlib.sha256(read_file(ftp, path) or b"").digest() != hashlib.sha256(data).digest():
        raise ConsoleError(tr("verify_failed", path=path))


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
    return game.console_key in installed or (game.title_id, None) in installed


def plan_sync(tiles, installed, existing_tiles):
    """Decides what to do with each tile.

    A tile is needed as long as one disc of the game is missing from the
    console. Returns (to_send, to_remove): tiles that must be on the console,
    and names of tiles to delete because the whole game is installed there or
    its ISO is gone from the PC.
    """
    to_send = [tile for tile in tiles
               if not all(is_installed(game, installed) for game in tile.games)]
    wanted = {tile.name.lower() for tile in to_send}
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
        raise ConsoleError(tr("mkdir_refused", path=path, error=error))


def send_tile(ftp, remote_root, name, files):
    """Uploads one tile and reads every file back to check it."""
    tile_dir = "%s/%s" % (remote_root, name)
    _ensure_dir(ftp, remote_root)
    _ensure_dir(ftp, tile_dir)
    for filename, data in files.items():
        write_file(ftp, "%s/%s" % (tile_dir, filename), data)


def sync(settings, tiles, stub, log, pc_ip=None, address_fixed=None):
    """Brings the console's tiles in line with the PC's ISOs.

    Returns {tile name: state} where state is "console" (installed there, no
    tile) or "netiso" (tile sent). With pc_ip, also corrects the address the
    plugin uses (check_pc_address) and calls address_fixed(old) when it did.
    """
    remote_root = "/" + settings["remote_root"].strip("/")
    tiles_scan_path(remote_root)  # refuses a drive root: tiles need a folder of their own
    drives = sorted({f.strip("/").split("/")[0] for f in settings["console_game_folders"]
                     if f.strip("/")} | {remote_root.strip("/").split("/")[0]})
    ftp = connect(settings["console_ip"], settings["ftp_user"], settings["ftp_password"])
    try:
        if pc_ip:
            old = check_pc_address(ftp, pc_ip, log)
            if old is not None and address_fixed:
                address_fixed(old)
        log(tr("looking_installed"))
        installed = installed_games(ftp, settings["console_game_folders"], drives, remote_root)
        log(tr("installed_count", count=len(installed)))
        to_send, to_remove = plan_sync(tiles, installed, existing_tiles(ftp, remote_root))
        for name in to_remove:
            remove_tile(ftp, remote_root, name)
            log(tr("tile_removed", name=name))
        message = tr("console_no_server")
        for number, tile in enumerate(to_send, 1):
            send_tile(ftp, remote_root, tile.name, netiso_iso.tile_files(
                stub, tile, message,
                netiso_iso.FAST_REQUEST_SIZE if settings.get("fast_read", True) else 0))
            log("  %d/%d  %s" % (number, len(to_send), tile.name))
        prepare_cleanup(ftp, remote_root, log)
        install_aurora_scripts(ftp, remote_root)
        sent = {tile.name for tile in to_send}
        return {tile.name: "netiso" if tile.name in sent else "console" for tile in tiles}
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass


# ---- entries Aurora keeps for tiles that are gone

def ghost_entries(content_db, settings_db, remote_root, existing):
    """Finds the entries of Aurora's game list left behind by removed tiles.

    Aurora never forgets a game whose folder disappeared, so a removed or
    renamed tile stays in its list as a dead duplicate. Only entries found by
    the scan path of our tiles folder are considered: the user's own games
    are never touched. Returns [(Id, Directory)].
    """
    path = tiles_scan_path(remote_root)
    existing = {name.lower() for name in existing}
    settings = sqlite3.connect(settings_db)
    try:
        scan_ids = [row[0] for row in settings.execute(
            "SELECT Id FROM ScanPaths WHERE Path = ? COLLATE NOCASE", (path,))]
    finally:
        settings.close()
    if not scan_ids:
        return []
    content = sqlite3.connect(content_db)
    try:
        rows = content.execute(
            "SELECT Id, Directory FROM ContentItems WHERE ScanPathId IN (%s) ORDER BY Id"
            % ",".join("?" * len(scan_ids)), scan_ids).fetchall()
    finally:
        content.close()
    ghosts = []
    for content_id, directory in rows:
        relative = directory[len(path):].strip("\\") if directory.lower().startswith(path.lower()) else ""
        tile = relative.split("\\")[0]
        if tile and tile.lower() not in existing:
            ghosts.append((content_id, directory))
    return ghosts


def _ascii(text):
    """Aurora scripts are plain ASCII: accents are dropped, other scripts fall back to '?'."""
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def tiles_scan_path(remote_root):
    """Path of the tiles folder as Aurora stores it: /Hdd1/NetISO -> \\NetISO."""
    parts = [part for part in remote_root.strip("/").split("/") if part]
    if len(parts) < 2:
        raise ConsoleError(tr("bad_tiles_folder", path=remote_root))
    return "\\" + "\\".join(parts[1:])


def cleanup_script(ghost_ids, scan_path, title, question, done):
    """Lua utility script that removes the given entries from Aurora's list.

    Aurora keeps its database locked while it runs, so the removal has to be
    done by Aurora itself. The script edits Aurora's list only: it holds no
    file operation at all. Every deletion names its entries one by one and is
    further limited to entries located under the tiles folder.
    """
    ids = ",".join(str(int(i)) for i in ghost_ids)
    prefix = (scan_path + "\\").lower()
    if not re.fullmatch(r"[a-z0-9 _\-\\]+", prefix):
        raise ConsoleError(tr("bad_tiles_folder", path=scan_path))
    under_tiles = "lower(substr(Directory, 1, %d)) = '%s'" % (len(prefix), prefix.replace("\\", "\\\\"))
    lines = [
        'scriptTitle = "NetISO Cleanup"',
        'scriptAuthor = "NetISO Manager"',
        'scriptVersion = 1',
        'scriptDescription = "%s"' % _ascii(title),
        'scriptPermissions = { "sql" }',
        '',
        'function main()',
        '\tlocal answer = Script.ShowMessageBox("NetISO Cleanup", "%s", "OK", "Cancel");'
        % _ascii(question).replace('"', "'"),
        '\tif answer.Button ~= 1 then',
        '\t\treturn;',
        '\tend',
    ]
    # References first, while the entries they point at can still be checked.
    lines += ['\tSql.Execute("DELETE FROM Config.%s WHERE ContentId IN (SELECT Id FROM ContentItems '
              'WHERE Id IN (%s) AND %s)");' % (table, ids, under_tiles)
              for table in CONTENT_REFERENCES]
    lines += ['\tSql.Execute("DELETE FROM ContentItems WHERE Id IN (%s) AND %s");' % (ids, under_tiles)]
    lines += [
        '\tScript.RefreshListOnExit(true);',
        '\tScript.ShowMessageBox("NetISO Cleanup", "%s", "OK");' % _ascii(done).replace('"', "'"),
        'end',
        '',
    ]
    return "\r\n".join(lines).encode("ascii")


def save_backup(content, settings, backup_dir=None):
    """Keeps a dated copy of Aurora's two databases on the PC; returns its folder.

    Taken before every cleanup script is prepared, so the list and settings of
    Aurora can be put back as they were. Old copies beyond the last ten go.
    """
    backup_dir = backup_dir or BACKUP_DIR
    folder = os.path.join(backup_dir, time.strftime("%Y-%m-%d_%H-%M-%S"))
    os.makedirs(folder, exist_ok=True)
    for name, data in (("content.db", content), ("settings.db", settings)):
        with open(os.path.join(folder, name), "wb") as f:
            f.write(data)
    for old in sorted(os.listdir(backup_dir))[:-BACKUPS_KEPT]:
        old_path = os.path.join(backup_dir, old)
        for name in os.listdir(old_path):
            os.remove(os.path.join(old_path, name))
        os.rmdir(old_path)
    return folder


def prepare_cleanup(ftp, remote_root, log, backup_dir=None):
    """Uploads a cleanup script when Aurora's list holds entries of removed tiles.

    Returns the number of such entries.
    """
    content = read_file(ftp, AURORA_CONTENT_DB)
    settings = read_file(ftp, AURORA_SETTINGS_DB)
    if content is None or settings is None:
        return 0
    existing = [name for name, is_dir in list_dir(ftp, remote_root) if is_dir]
    folder = tempfile.mkdtemp()
    try:
        paths = []
        for name, data in (("content.db", content), ("settings.db", settings)):
            paths.append(os.path.join(folder, name))
            with open(paths[-1], "wb") as f:
                f.write(data)
        try:
            ghosts = ghost_entries(paths[0], paths[1], remote_root, existing)
        except sqlite3.Error:
            return 0
    finally:
        for name in os.listdir(folder):
            os.remove(os.path.join(folder, name))
        os.rmdir(folder)
    if ghosts:
        log(tr("backup_saved", path=save_backup(content, settings, backup_dir)))
        script = cleanup_script([g[0] for g in ghosts], tiles_scan_path(remote_root),
                                tr("cleanup_description"),
                                tr("cleanup_question", count=len(ghosts)), tr("cleanup_done"))
        _ensure_dir(ftp, CLEANUP_SCRIPT_DIR)
        write_file(ftp, CLEANUP_SCRIPT_DIR + "/Main.lua", script)
        log(tr("cleanup_ready", count=len(ghosts)))
    return len(ghosts)


# ---- plugin installation

def ini_to_ftp_path(ini_path):
    """Turns a DashLaunch path (Hdd:\\Apps\\x.xex) into an FTP path (/Hdd1/Apps/x.xex)."""
    for device, drive in DEVICES:
        if ini_path.lower().startswith(device.lower()):
            return drive + ini_path[len(device):].replace("\\", "/")
    raise ConsoleError(tr("unknown_device", path=ini_path))


def plan_launch_ini(text, plugin_path=DEFAULT_PLUGIN_PATH):
    """Finds where launch.ini loads NetISO.xex, or adds it to a free plugin slot.

    Returns (plugin path as written in the file, new text or None when the
    file already loads the plugin).
    """
    in_plugins = False
    free = None
    lines = text.splitlines(keepends=True)
    for number, line in enumerate(lines):
        section = re.match(r"\s*\[(.+?)\]", line)
        if section:
            in_plugins = section.group(1).strip().lower() == "plugins"
            continue
        slot = re.match(r"(\s*plugin\d\s*=)[ \t]*([^\r\n]*?)[ \t]*(\r?\n?)$", line, re.I)
        if not in_plugins or not slot:
            continue
        value = slot.group(2)
        if value.replace("/", "\\").lower().endswith("\\netiso.xex"):
            return value, None
        if not value and free is None:
            free = (number, slot)
    if free is None:
        raise ConsoleError(tr("no_plugin_slot"))
    number, slot = free
    lines[number] = "%s %s%s" % (slot.group(1), plugin_path, slot.group(3) or "\r\n")
    return plugin_path, "".join(lines)


def bundled_plugin():
    """Path of the NetISO.xex shipped with the app, or None."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "plugin", "NetISO.xex")
    return path if os.path.isfile(path) else None


def is_known_plugin(data):
    return hashlib.sha256(data).hexdigest() == PLUGIN_SHA256


# ---- telling Aurora whether the PC is there

MARKER_NAME = "pc_online.txt"
FILTER_SCRIPT = "/Game/User/Scripts/Content/Filters/NetISO.lua"
SUBTITLE_SCRIPT = "/Game/User/Scripts/Content/Subtitles/NetISO.lua"


def _aurora_paths(remote_root):
    """("Hdd1:\\\\NetISO\\\\pc_online.txt", "\\\\netiso\\\\") as Lua string literals for a tiles folder."""
    drive, _, folder = remote_root.strip("/").partition("/")
    marker = "%s:\\%s\\%s" % (drive, folder.replace("/", "\\"), MARKER_NAME)
    prefix = "\\%s\\" % folder.replace("/", "\\").lower()
    lua = lambda text: text.replace("\\", "\\\\").replace('"', '\\"')
    return lua(marker), lua(prefix), len(prefix)


def aurora_scripts(remote_root):
    """Lua for Aurora's game list: a subtitle showing where a game plays from, and a
    filter hiding the PC's games while NetISO Manager is closed.

    The PC is taken as "there" while the marker file exists: the app writes it
    while it runs and deletes it when it closes. After a crash or a power cut
    the marker stays, the games stay visible, and the launcher's "PC not
    reachable" message remains the last safety net. If Aurora does not give
    these scripts file access, they fall back to showing every game.
    """
    marker, prefix, length = _aurora_paths(remote_root)
    common = (
        '-- Written by NetISO Manager. Safe to delete: NetISO Manager writes it again.\n'
        'local function NetIsoGame(Content)\n'
        '\treturn string.sub(string.lower(Content.Directory or ""), 1, %d) == "%s"\n'
        'end\n'
        'local function PcOnline()\n'
        '\tlocal ok, online = pcall(FileSystem.FileExists, "%s")\n'
        '\treturn (not ok) or online\n'
        'end\n' % (length, prefix, marker))
    subtitle = common + (
        'GameListSubtitles["NetISO"] = function(Content)\n'
        '\tif not NetIsoGame(Content) then return "On the console" end\n'
        '\tif PcOnline() then return "Played from the PC" end\n'
        '\treturn "PC off: start NetISO Manager"\n'
        'end\n')
    filter_ = common + (
        'GameListFilterCategories.User["%s"] = function(Content)\n'
        '\treturn (not NetIsoGame(Content)) or PcOnline()\n'
        'end\n'
        '-- Hides the discs that are not a game: installation discs and voice or texture\n'
        '-- packs (often the generic Title ID FFED2000: the Resident Evil 6 voice pack shows\n'
        '-- as "RESIDENT EVIL 6" while the game is "BIOHAZARD 6"). Game discs all stay:\n'
        '-- Battlefield 4 runs its campaign from disc 2, launched on its own.\n'
        'GameListFilterCategories.User["%s"] = function(Content)\n'
        '\tlocal id = Content.TitleId or 0\n'
        '\tif id < 0 then id = id + 4294967296 end\n'
        '\tif id == 4293730304 then return false end\n'
        '\tlocal folder = string.lower(Content.Directory or "")\n'
        '\tif string.find(folder, "game disc", 1, true) then return true end\n'
        '\tfor _, word in ipairs({ "install", "voice", "language", "texture", "hd content" }) do\n'
        '\t\tif string.find(folder, word, 1, true) then return false end\n'
        '\tend\n'
        '\treturn true\n'
        'end\n' % (FILTER_NAME, DISC_FILTER_NAME))
    return subtitle.encode("ascii"), filter_.encode("ascii")


FILTER_NAME = "NetISO: hide PC games when the PC is off"
DISC_FILTER_NAME = "NetISO: hide install and voice discs"
# Names this filter had during development: views saved with them are updated by the setup script.
OLD_DISC_FILTER_NAMES = ("NetISO: one entry per game",)
QUICK_VIEW_NAME = "Available games"
SETUP_SCRIPT = "/Game/User/Scripts/Utility/NetISO Setup/Main.lua"


def setup_script():
    """Optional one-run Aurora script: makes the "Available games" quick view (the
    NetISO filter, kept across restarts, unlike a filter ticked by hand) the one
    Aurora opens on. Quick views live in settings.db; Aurora saves a user filter
    as "User.<name>" with flags 262144 (seen on a real console, 2026-10-17)."""
    method = "User.%s;AND;User.%s" % (FILTER_NAME, DISC_FILTER_NAME)
    # Views saved earlier: made by hand with the first filter only, or with older names.
    older = "', '".join(["User." + FILTER_NAME] + ["User.%s;AND;User.%s" % (FILTER_NAME, name)
                                                   for name in OLD_DISC_FILTER_NAMES])
    return (
        'scriptTitle = "NetISO Setup"\n'
        'scriptAuthor = "NetISO Manager"\n'
        'scriptVersion = 1\n'
        'scriptDescription = "Opens Aurora on the games you can play now: PC games are hidden '
        'while NetISO Manager is closed. Run it once."\n'
        'scriptPermissions = { "sql", "settings" }\n'
        '\n'
        'local function ViewId()\n'
        '\tfor _, row in pairs(Sql.ExecuteFetchRows("SELECT Id FROM Config.QuickViews WHERE '
        'FilterMethod IN (\'%(method)s\', \'%(older)s\')")) do\n'
        '\t\treturn row.Id\n'
        '\tend\n'
        '\treturn nil\n'
        'end\n'
        '\n'
        'function main()\n'
        '\tlocal id = ViewId()\n'
        '\tif id == nil then\n'
        '\t\tSql.Execute("INSERT INTO Config.QuickViews (DisplayName, SortMethod, FilterMethod, '
        'Flags, CreatorXUID, OrderIndex, IconHash) SELECT \'%(name)s\', \'Title Name\', '
        '\'%(method)s\', 262144, \'\', IFNULL(MAX(OrderIndex), 0) + 1, \'\' FROM Config.QuickViews")\n'
        '\t\tid = ViewId()\n'
        '\telse\n'
        '\t\tSql.Execute("UPDATE Config.QuickViews SET DisplayName = \'%(name)s\', FilterMethod = '
        '\'%(method)s\' WHERE Id = " .. id)\n'
        '\tend\n'
        '\tif id == nil then\n'
        '\t\tScript.ShowMessageBox("NetISO Setup", "The quick view could not be created.", "OK")\n'
        '\t\treturn\n'
        '\tend\n'
        '\tSettings.SetSystem("DefaultQuickView", tostring(id))\n'
        '\tlocal answer = Script.ShowMessageBox("NetISO Setup", "Aurora will now open on '
        '\\"%(name)s\\". Restart Aurora?", "Yes", "No")\n'
        '\tif answer.Button == 1 then\n'
        '\t\tAurora.Restart()\n'
        '\tend\n'
        'end\n' % {"method": method, "older": older, "name": QUICK_VIEW_NAME}).encode("ascii")


def install_aurora_scripts(ftp, remote_root):
    """Puts the subtitle, filter and setup scripts in Aurora's script folders (rewritten each sync)."""
    subtitle, filter_ = aurora_scripts(remote_root)
    for path, data in ((SUBTITLE_SCRIPT, subtitle), (FILTER_SCRIPT, filter_),
                       (SETUP_SCRIPT, setup_script())):
        _ensure_dir(ftp, path.rsplit("/", 1)[0])
        write_file(ftp, path, data)


def set_pc_online(settings, online):
    """Writes or removes the marker the Aurora scripts look for. Raises ConsoleError when
    the console cannot be reached."""
    remote_root = "/" + settings["remote_root"].strip("/")
    tiles_scan_path(remote_root)
    try:
        ftp = connect(settings["console_ip"], settings["ftp_user"], settings["ftp_password"])
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    try:
        path = remote_root + "/" + MARKER_NAME
        if online:
            write_file(ftp, path, b"NetISO Manager is running on the PC.\r\n")
        else:
            try:
                ftp.delete(path)
            except ftplib.error_perm:
                pass  # already gone
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass


def check_pc_address(ftp, pc_ip, log):
    """Rewrites NetISO.xex.txt when it no longer holds this PC's address.

    A router that hands out addresses again (after a restart) can give the PC
    a new one: the plugin then keeps asking the old address and every NetISO
    game goes back to Aurora with "PC server not reachable". Only acts when
    launch.ini already loads NetISO.xex and the plugin file is there. Returns
    the address that was replaced ("" when the file was missing), or None
    when nothing had to change.
    """
    ini = None
    for candidate in LAUNCH_INI_PATHS:
        ini = read_file(ftp, candidate)
        if ini is not None:
            break
    if ini is None:
        return None
    try:
        plugin_ini_path, new_text = plan_launch_ini(ini.decode("latin-1"))
    except ConsoleError:
        return None
    if new_text is not None:
        return None                      # not installed: the setup button handles that
    plugin_path = ini_to_ftp_path(plugin_ini_path)
    folder, filename = plugin_path.rsplit("/", 1)
    if filename.lower() not in {n.lower() for n, d in list_dir(ftp, folder) if not d}:
        return None
    current = read_file(ftp, plugin_path + ".txt")
    old = current.decode("latin-1").strip() if current is not None else ""
    if old == pc_ip:
        return None
    write_file(ftp, plugin_path + ".txt", pc_ip.encode("ascii"))
    log(tr("address_fixed_log", old=old or "-", ip=pc_ip, path=plugin_ini_path + ".txt"))
    return old


def fix_pc_address(settings, pc_ip, log):
    """check_pc_address on its own connection. Raises ConsoleError when the console is not reachable."""
    try:
        ftp = connect(settings["console_ip"], settings["ftp_user"], settings["ftp_password"])
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    try:
        return check_pc_address(ftp, pc_ip, log)
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass


def setup_console(settings, pc_ip, plugin_file, log):
    """Makes the console load NetISO.xex and point it at this PC.

    Uploads the plugin when it is missing (the copy shipped with the app, or
    plugin_file when given), writes the PC address next to it, and registers
    the plugin in launch.ini after saving a backup. A plugin already on the
    console is left in place. Returns True when launch.ini was changed.
    """
    ftp = connect(settings["console_ip"], settings["ftp_user"], settings["ftp_password"])
    try:
        ini_path, ini = None, None
        for candidate in LAUNCH_INI_PATHS:
            ini = read_file(ftp, candidate)
            if ini is not None:
                ini_path = candidate
                break
        if ini is None:
            raise ConsoleError(tr("no_launch_ini"))
        plugin_ini_path, new_text = plan_launch_ini(ini.decode("latin-1"))
        plugin_path = ini_to_ftp_path(plugin_ini_path)
        folder, filename = plugin_path.rsplit("/", 1)
        present = {n.lower() for n, d in list_dir(ftp, folder) if not d}
        if filename.lower() not in present:
            plugin_file = plugin_file or bundled_plugin()
            if not plugin_file:
                raise PluginMissing(tr("plugin_missing", path=plugin_ini_path))
            with open(plugin_file, "rb") as f:
                data = f.read()
            _ensure_dir(ftp, folder)
            write_file(ftp, plugin_path, data)
            log(tr("plugin_uploaded", path=plugin_ini_path))
        else:
            data = read_file(ftp, plugin_path) or b""
        if not is_known_plugin(data):
            log(tr("plugin_other_version", path=plugin_ini_path))
        write_file(ftp, plugin_path + ".txt", pc_ip.encode("ascii"))
        log(tr("address_written", path=plugin_ini_path + ".txt", ip=pc_ip))
        if new_text is not None:
            write_file(ftp, ini_path + ".netiso.bak", ini)
            write_file(ftp, ini_path, new_text.encode("latin-1"))
            log(tr("ini_updated", path=ini_path))
        return new_text is not None
    except (OSError, ftplib.Error) as error:
        raise ConsoleError(tr("ftp_error", error=error))
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass
