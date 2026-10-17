"""What Windows thinks of the network the console is on.

The installer opens port 4323 for private networks only. When Windows files
the network as Public (it can, after the router hands out new addresses),
its firewall silently blocks the console and every game ends with "PC not
reachable". This module only reads the setting; changing it is the user's call.
"""

import re
import subprocess

CREATE_NO_WINDOW = 0x08000000


def network_category(local_address, timeout=15):
    """"Public", "Private" or "DomainAuthenticated" for the network carrying
    local_address, or None when it cannot be told."""
    if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", local_address or ""):
        return None
    script = ("$i = (Get-NetIPAddress -IPAddress '%s' -ErrorAction Stop).InterfaceIndex; "
              "(Get-NetConnectionProfile -InterfaceIndex $i -ErrorAction Stop).NetworkCategory"
              % local_address)
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                                capture_output=True, text=True, timeout=timeout,
                                creationflags=CREATE_NO_WINDOW)
    except (OSError, subprocess.SubprocessError):
        return None
    category = result.stdout.strip()
    return category if category in ("Public", "Private", "DomainAuthenticated") else None


def make_private(local_address):
    """Asks Windows, through its administrator prompt (UAC), to file the network carrying
    local_address as Private. Only ever called after the user said yes.

    Returns True when the prompt was shown and the command started; the change
    itself is checked afterwards with network_category().
    """
    if not re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", local_address or ""):
        return False
    script = ("$i = (Get-NetIPAddress -IPAddress '%s' -ErrorAction Stop).InterfaceIndex; "
              "Set-NetConnectionProfile -InterfaceIndex $i -NetworkCategory Private" % local_address)
    try:
        import ctypes
        result = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", "powershell.exe",
            '-NoProfile -NonInteractive -WindowStyle Hidden -Command "%s"' % script, None, 0)
    except (AttributeError, OSError):
        return False
    return result > 32           # ShellExecute returns a value above 32 on success
