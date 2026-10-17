"""Helpers of version 1.3: keeping the PC awake, update notice, finding the
console, Xenia, setup test and diagnostic report.

Nothing here touches the window: the app calls these from worker threads and
shows the results.
"""

import concurrent.futures
import ctypes
import ftplib
import ipaddress
import json
import os
import platform
import re
import socket
import subprocess
import urllib.request

import netiso_console
import netiso_network
import netiso_nova
from netiso_i18n import tr

APP_VERSION = "1.3.0"
RELEASES_API = "https://api.github.com/repos/HB-Agadir/NetISO-Manager/releases/latest"
RELEASES_PAGE = "https://github.com/HB-Agadir/NetISO-Manager/releases/latest"
FTP_PORT = 21
NOVA_PORT = netiso_nova.PORT

# ---- keeping the PC awake while a game plays

ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def keep_awake(on):
    """Asks Windows not to sleep (on) or gives the permission back (off).

    The request belongs to the calling thread: call it from the window's
    thread every time. The screen may still turn off; only sleep is held.
    Returns False where the call is not available.
    """
    try:
        flags = ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0)
        return ctypes.windll.kernel32.SetThreadExecutionState(flags) != 0
    except (AttributeError, OSError):
        return False


# ---- update notice

def version_tuple(text):
    """"v1.2.0" -> (1, 2, 0); () when it is not a version."""
    match = re.fullmatch(r"v?(\d+(?:\.\d+)*)", (text or "").strip())
    return tuple(int(part) for part in match.group(1).split(".")) if match else ()


def newer_release(current=APP_VERSION, timeout=10):
    """The tag of the latest published release when it is newer than current, else None.

    Only reads GitHub's public release information; nothing is sent about the user.
    """
    request = urllib.request.Request(RELEASES_API, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "NetISO-Manager"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            tag = json.loads(response.read()).get("tag_name", "")
    except (OSError, ValueError):
        return None
    latest = version_tuple(tag)
    return tag if latest and latest > version_tuple(current) else None


# ---- finding the console

def _open(host, port, timeout):
    try:
        with socket.create_connection((host, port), timeout):
            return True
    except OSError:
        return False


def find_consoles(pc_ip, timeout=0.6, workers=64):
    """Addresses on the PC's network (/24) that answer like a console running Aurora.

    A console has Aurora's FTP server (21) and its web server (9999) open.
    Returns them sorted, best guess first: both ports open, then FTP only.
    """
    try:
        network = ipaddress.ip_network(pc_ip + "/24", strict=False)
    except ValueError:
        return []
    hosts = [str(h) for h in network.hosts() if str(h) != pc_ip]
    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        ftp = dict(zip(hosts, pool.map(lambda h: _open(h, FTP_PORT, timeout), hosts)))
        with_ftp = [h for h in hosts if ftp[h]]
        web = dict(zip(with_ftp, pool.map(lambda h: _open(h, NOVA_PORT, timeout), with_ftp)))
    order = lambda h: (not web[h], tuple(int(p) for p in h.split(".")))
    return sorted(with_ftp, key=order)


def is_aurora(host, user, password):
    """True when Aurora's web server at host accepts the login (it then is a console)."""
    try:
        netiso_nova.NovaClient(host, user, password).login()
        return True
    except netiso_nova.NovaError:
        return False


# ---- Xenia

def xenia_target(game):
    """What Xenia is given for a game: the ISO, or the default.xex of a game folder."""
    if game.is_folder:
        return os.path.join(game.path, "default.xex")
    return game.path


def launch_xenia(xenia_exe, game):
    """Starts Xenia on the game. Xenia takes the .iso or .xex as its first argument
    (its "target" option). Raises OSError when it cannot be started."""
    target = xenia_target(game)
    if not os.path.exists(target):
        raise OSError(tr("xenia_no_target", path=target))
    return subprocess.Popen([xenia_exe, target], cwd=os.path.dirname(xenia_exe))


# ---- setup test

OK, WARN, FAIL = "ok", "warn", "fail"


def run_checks(settings, pc_ip, server_running):
    """Checks the whole chain, console side and PC side.

    Returns [(status, text)] in order; each text says what is wrong and what
    to do. Stops checking the console after the first step it cannot pass.
    """
    results = []
    add = lambda status, key, **values: results.append((status, tr(key, **values)))

    add(OK if server_running else FAIL, "check_server_ok" if server_running else "check_server_off")
    category = netiso_network.network_category(pc_ip) if pc_ip else None
    if category == "Public":
        add(FAIL, "check_network_public")
    elif category:
        add(OK, "check_network_ok", category=category)
    else:
        add(WARN, "check_network_unknown")

    host = settings.get("console_ip", "")
    if not host:
        add(FAIL, "check_no_console_ip")
        return results
    if not _open(host, FTP_PORT, 3):
        add(FAIL, "check_console_unreachable", host=host)
        return results
    try:
        ftp = netiso_console.connect(host, settings["ftp_user"], settings["ftp_password"])
    except (OSError, ftplib.Error):
        add(FAIL, "check_ftp_login")
        return results
    add(OK, "check_console_ok", host=host)
    try:
        ini, ini_path = None, None
        for candidate in netiso_console.LAUNCH_INI_PATHS:
            ini = netiso_console.read_file(ftp, candidate)
            if ini is not None:
                ini_path = candidate
                break
        if ini is None:
            add(FAIL, "check_no_launch_ini")
            return results
        try:
            plugin_ini_path, new_text = netiso_console.plan_launch_ini(ini.decode("latin-1"))
        except netiso_console.ConsoleError:
            add(FAIL, "check_no_plugin_slot")
            return results
        if new_text is not None:
            add(FAIL, "check_plugin_not_loaded", path=ini_path)
            return results
        plugin_path = netiso_console.ini_to_ftp_path(plugin_ini_path)
        data = netiso_console.read_file(ftp, plugin_path)
        if data is None:
            add(FAIL, "check_plugin_missing", path=plugin_ini_path)
            return results
        if netiso_console.is_known_plugin(data):
            add(OK, "check_plugin_ok", path=plugin_ini_path)
        else:
            add(WARN, "check_plugin_other", path=plugin_ini_path)
        address = netiso_console.read_file(ftp, plugin_path + ".txt")
        address = address.decode("latin-1").strip() if address is not None else ""
        if not address:
            add(FAIL, "check_address_missing")
        elif pc_ip and address != pc_ip:
            add(FAIL, "check_address_wrong", found=address, ip=pc_ip)
        else:
            add(OK, "check_address_ok", ip=address)
    except (OSError, ftplib.Error) as error:
        add(FAIL, "check_ftp_error", error=error)
        return results
    finally:
        try:
            ftp.quit()
        except (OSError, ftplib.Error):
            pass

    if is_aurora(host, settings.get("http_user") or "xboxhttp",
                 settings.get("http_password") or "xboxhttp"):
        add(OK, "check_web_ok")
    else:
        add(WARN, "check_web_failed")
    return results


# ---- diagnostic report

_ADDRESS = re.compile(r"\b(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})\b")


def scrub(text):
    """Removes what could identify the user: addresses, Windows user name, home folder."""
    text = _ADDRESS.sub(lambda m: "x.x.x." + m.group(4), text)
    home = os.path.expanduser("~")
    if home and home != "~":
        text = text.replace(home, "%USERPROFILE%")
    user = os.environ.get("USERNAME", "")
    if len(user) > 2:
        text = re.sub(re.escape(user), "<user>", text, flags=re.IGNORECASE)
    return text


def diagnostic_report(settings, checks, tiles, log_text, server_running, max_log_lines=60):
    """Plain text to paste in a forum post or a GitHub issue. No passwords, no
    addresses, no user name; the game list is reduced to counts."""
    games = sum(len(t.games) for t in tiles)
    folders = sum(1 for t in tiles for g in t.games if g.is_folder)
    lines = [
        "NetISO Manager %s - diagnostic report" % APP_VERSION,
        "Windows %s (%s)" % (platform.version(), platform.machine()),
        "Server running: %s" % ("yes" if server_running else "no"),
        "Fast loading: %s   One tile per multi-disc game: %s" % (
            "yes" if settings.get("fast_read") else "no",
            "yes" if settings.get("group_discs") else "no"),
        "Games: %d tiles, %d discs (%d ISO, %d game folders), %d PC folder(s)" % (
            len(tiles), games, games - folders, folders, len(settings.get("folders", []))),
        "",
        "Setup test:",
    ]
    if checks:
        lines += ["  [%s] %s" % (status.upper(), text) for status, text in checks]
    else:
        lines.append("  (not run)")
    log_lines = [line for line in log_text.splitlines() if line.strip()][-max_log_lines:]
    lines += ["", "Log (last %d lines):" % len(log_lines)] + ["  " + line for line in log_lines]
    return scrub("\n".join(lines)) + "\n"
