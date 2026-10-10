"""Starts NetISO Manager with the user's Windows session (per-user Run key)."""

import os
import sys
import winreg

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "NetISOManager"
MINIMIZED_FLAG = "--minimized"


def command(script_path):
    """Command line that reopens the app minimized."""
    if getattr(sys, "frozen", False):
        return '"%s" %s' % (sys.executable, MINIMIZED_FLAG)
    runner = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    if not os.path.exists(runner):
        runner = sys.executable
    return '"%s" "%s" %s' % (runner, script_path, MINIMIZED_FLAG)


def is_enabled():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, VALUE_NAME)
            return True
    except OSError:
        return False


def set_enabled(enabled, script_path):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, command(script_path))
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass
