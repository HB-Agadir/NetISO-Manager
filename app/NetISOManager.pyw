"""NetISO Manager: pick ISO folders, show the games in Aurora, serve them to the console."""

import json
import os
import queue
import socket
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import netiso_console
import netiso_i18n
import netiso_iso
import netiso_server
from netiso_i18n import tr

# When frozen into an executable, bundled files live in the unpacking folder.
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
STUB_PATH = os.path.join(APP_DIR, "stub.xex")
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA", APP_DIR), "NetISOManager", "settings.json")
WATCH_INTERVAL_MS = 15000
PROMPT_NAMES_MAX = 8
DEFAULTS = {
    "language": "fr",
    "folders": [],
    "recursive": True,
    "auto_detect": True,
    "console_ip": "",
    "ftp_user": "xboxftp",
    "ftp_password": "xboxftp",
    "remote_root": "/Hdd1/NetISO",
    "console_game_folders": ["/Hdd1/Games"],
    "autostart_server": True,
}


def load_settings():
    settings = dict(DEFAULTS)
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as f:
            settings.update(json.load(f))
    except (OSError, ValueError):
        pass
    return settings


def save_settings(settings):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)


def local_ip(toward):
    """Address of this PC on the network that reaches the console."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((toward or "192.168.1.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return tr("pc_ip_unknown")
    finally:
        probe.close()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NetISO Manager")
        self.geometry("1000x720")
        self.minsize(860, 600)
        self.settings = load_settings()
        netiso_i18n.set_language(self.settings["language"])
        self.games = []
        self.states = {}
        self.events = queue.Queue()
        self.server = netiso_server.NetIsoServer(lambda kind, text: self.events.put(("log", text)))
        self.busy = False
        self.scanned = None      # {path: size} at the last full scan
        self.last_seen = None    # {path: size} at the previous watch poll
        self.prompt_next_scan = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._drain_events)
        self.after(WATCH_INTERVAL_MS, self._watch)
        if self.settings["folders"]:
            self._scan()
        if self.settings["autostart_server"]:
            self._autostart_server()

    # ---- layout

    def _build(self):
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")
        pad = {"padx": 10, "pady": 6}
        self.body = ttk.Frame(self)
        self.body.pack(fill="both", expand=True)
        body = self.body

        top = ttk.Frame(body)
        top.pack(fill="x", padx=10, pady=(8, 0))
        self.language = tk.StringVar(value=netiso_i18n.LANGUAGES[netiso_i18n.language()])
        picker = ttk.Combobox(top, textvariable=self.language, state="readonly", width=12,
                              values=list(netiso_i18n.LANGUAGES.values()))
        picker.pack(side="right")
        picker.bind("<<ComboboxSelected>>", self._change_language)
        ttk.Label(top, text=tr("language")).pack(side="right", padx=6)

        folders = ttk.LabelFrame(body, text=tr("folders_frame"))
        folders.pack(fill="x", **pad)
        self.folder_list = tk.Listbox(folders, height=5, activestyle="none")
        self.folder_list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        for folder in self.settings["folders"]:
            self.folder_list.insert("end", folder)
        buttons = ttk.Frame(folders)
        buttons.pack(side="right", fill="y", padx=8, pady=8)
        ttk.Button(buttons, text=tr("add_folder"), command=self._add_folder).pack(fill="x")
        ttk.Button(buttons, text=tr("remove"), command=self._remove_folder).pack(fill="x", pady=4)
        ttk.Button(buttons, text=tr("refresh"), command=self._scan).pack(fill="x")
        self.recursive = tk.BooleanVar(value=self.settings["recursive"])
        ttk.Checkbutton(buttons, text=tr("recursive"), variable=self.recursive,
                        command=self._scan).pack(fill="x", pady=(4, 0))
        self.auto_detect = tk.BooleanVar(value=self.settings["auto_detect"])
        ttk.Checkbutton(buttons, text=tr("auto_detect"), variable=self.auto_detect).pack(fill="x")

        games = ttk.LabelFrame(body, text=tr("games_frame"))
        games.pack(fill="both", expand=True, **pad)
        columns = ("name", "state", "title", "disc", "size", "folder")
        self.tree = ttk.Treeview(games, columns=columns, show="headings", height=8)
        for column, key, width, anchor in (
                ("name", "col_game", 260, "w"), ("state", "col_state", 170, "w"),
                ("title", "col_title", 80, "center"), ("disc", "col_disc", 60, "center"),
                ("size", "col_size", 80, "e"), ("folder", "col_folder", 260, "w")):
            self.tree.heading(column, text=tr(key))
            self.tree.column(column, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(games, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", padx=(0, 8), pady=8)

        row = ttk.Frame(body)
        row.pack(fill="x", **pad)

        console = ttk.LabelFrame(row, text=tr("console_frame"))
        console.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.console_ip = tk.StringVar(value=self.settings["console_ip"])
        self.ftp_user = tk.StringVar(value=self.settings["ftp_user"])
        self.ftp_password = tk.StringVar(value=self.settings["ftp_password"])
        self.remote_root = tk.StringVar(value=self.settings["remote_root"])
        self.console_folders = tk.StringVar(
            value="; ".join(self.settings["console_game_folders"]))
        for line, (key, variable) in enumerate((
                ("console_ip", self.console_ip), ("ftp_user", self.ftp_user),
                ("ftp_password", self.ftp_password), ("remote_root", self.remote_root),
                ("console_folders", self.console_folders))):
            ttk.Label(console, text=tr(key)).grid(row=line, column=0, sticky="w", padx=8, pady=3)
            ttk.Entry(console, textvariable=variable, width=18).grid(
                row=line, column=1, sticky="we", padx=8, pady=3)
        console.columnconfigure(1, weight=1)
        self.push_button = ttk.Button(console, text=tr("sync_button"), command=self._push)
        self.push_button.grid(row=5, column=0, columnspan=2, sticky="we", padx=8, pady=8)
        if self.busy:
            self.push_button.configure(state="disabled")

        server = ttk.LabelFrame(row, text=tr("server_frame"))
        server.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.server_state = tk.StringVar()
        self.pc_ip = tk.StringVar()
        ttk.Label(server, text=tr("server_state")).grid(row=0, column=0, sticky="w", padx=8, pady=3)
        ttk.Label(server, textvariable=self.server_state).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(server, text=tr("pc_ip")).grid(row=1, column=0, sticky="w", padx=8, pady=3)
        ttk.Label(server, textvariable=self.pc_ip).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(server, text=tr("pc_ip_hint"), foreground="#666666").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8)
        self.autostart = tk.BooleanVar(value=self.settings["autostart_server"])
        ttk.Checkbutton(server, text=tr("autostart"), variable=self.autostart).grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8, pady=3)
        self.server_button = ttk.Button(server, command=self._toggle_server)
        self.server_button.grid(row=4, column=0, columnspan=2, sticky="we", padx=8, pady=8)
        server.columnconfigure(1, weight=1)

        log = ttk.LabelFrame(body, text=tr("log_frame"))
        log.pack(fill="both", **pad)
        self.log = tk.Text(log, height=7, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_pc_ip()
        self._show_server_state()

    def _change_language(self, _event=None):
        chosen = self.language.get()
        code = next(c for c, label in netiso_i18n.LANGUAGES.items() if label == chosen)
        if code == netiso_i18n.language():
            return
        self._collect_settings()
        self.settings["language"] = code
        save_settings(self.settings)
        netiso_i18n.set_language(code)
        history = self.log.get("1.0", "end-1c")
        self.body.destroy()
        self._build()
        self.log.configure(state="normal")
        self.log.insert("end", history)
        self.log.see("end")
        self.log.configure(state="disabled")
        self._fill_tree()

    # ---- helpers

    def _log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", "%s  %s\n" % (time.strftime("%H:%M:%S"), text))
        self.log.see("end")
        self.log.configure(state="disabled")

    def _drain_events(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "log":
                    self._log(payload)
                elif kind == "scanned":
                    self._show_games(*payload)
                elif kind == "watched":
                    self._compare_snapshot(payload)
                elif kind == "pushed":
                    self.busy = False
                    self.push_button.configure(state="normal")
                    message, states = payload
                    if states is not None:
                        self.states = states
                        self._fill_tree()
                    self._log(message)
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _refresh_pc_ip(self):
        self.pc_ip.set(local_ip(self.console_ip.get().strip()))

    def _collect_settings(self):
        self.settings.update({
            "language": netiso_i18n.language(),
            "folders": list(self.folder_list.get(0, "end")),
            "recursive": self.recursive.get(),
            "auto_detect": self.auto_detect.get(),
            "console_ip": self.console_ip.get().strip(),
            "ftp_user": self.ftp_user.get(),
            "ftp_password": self.ftp_password.get(),
            "remote_root": self.remote_root.get().strip(),
            "console_game_folders": [f.strip() for f in self.console_folders.get().split(";")
                                     if f.strip()],
            "autostart_server": self.autostart.get(),
        })
        return self.settings

    # ---- folders and games

    def _add_folder(self):
        folder = filedialog.askdirectory(title=tr("choose_folder"))
        if not folder:
            return
        folder = os.path.normpath(folder)
        if folder.lower() not in (f.lower() for f in self.folder_list.get(0, "end")):
            self.folder_list.insert("end", folder)
            self._scan()

    def _remove_folder(self):
        for index in reversed(self.folder_list.curselection()):
            self.folder_list.delete(index)
        self._scan()

    def _scan(self, prompt=False):
        settings = self._collect_settings()
        save_settings(settings)
        folders, recursive = list(settings["folders"]), settings["recursive"]
        self.prompt_next_scan = prompt
        self._log(tr("scanning", count=len(folders)))

        def work():
            snapshot = netiso_iso.snapshot(folders, recursive)
            self.events.put(("scanned", netiso_iso.scan(folders, recursive) + (snapshot,)))

        threading.Thread(target=work, daemon=True).start()

    def _show_games(self, games, errors, snapshot):
        before = {game.name for game in self.games}
        self.games = games
        self.scanned = snapshot
        self.server.set_games(games)
        self._fill_tree()
        self._log(tr("games_found", count=len(games)))
        for path, message in errors:
            self._log(tr("ignored", path=path, reason=message))
        if self.prompt_next_scan:
            self.prompt_next_scan = False
            after = {game.name for game in games}
            self._offer_transfer(sorted(after - before), sorted(before - after))

    def _fill_tree(self):
        labels = {"netiso": tr("state_netiso"), "console": tr("state_console")}
        self.tree.delete(*self.tree.get_children())
        for game in self.games:
            self.tree.insert("", "end", values=(
                game.name, labels.get(self.states.get(game.name), tr("state_pending")),
                "%08X" % game.title_id, "%d/%d" % (game.disc, game.discs),
                tr("size_gb", size=game.size / 1e9), os.path.dirname(game.path)))

    # ---- automatic detection

    def _watch(self):
        self.after(WATCH_INTERVAL_MS, self._watch)
        if not self.auto_detect.get() or self.scanned is None or self.busy:
            return
        folders = list(self.folder_list.get(0, "end"))
        recursive = self.recursive.get()

        def work():
            snapshot = netiso_iso.snapshot(folders, recursive)
            changed = [p for p in snapshot if snapshot[p] != (self.scanned or {}).get(p)]
            writing = any(netiso_iso.is_being_written(p) for p in changed)
            self.events.put(("watched", (snapshot, writing)))

        threading.Thread(target=work, daemon=True).start()

    def _compare_snapshot(self, payload):
        snapshot, writing = payload
        previous, self.last_seen = self.last_seen, snapshot
        if snapshot == self.scanned or self.prompt_next_scan:
            return
        # Act only once the files have stopped changing: a copy or a download
        # in progress would be read as a broken ISO.
        if writing or snapshot != previous:
            return
        self._scan(prompt=True)

    def _offer_transfer(self, added, removed):
        if not added and not removed:
            return
        lines = []
        for key, names in (("changes_added", added), ("changes_removed", removed)):
            if names:
                lines.append(tr(key))
                lines += ["   " + name for name in names[:PROMPT_NAMES_MAX]]
                if len(names) > PROMPT_NAMES_MAX:
                    lines.append("   " + tr("changes_more", count=len(names) - PROMPT_NAMES_MAX))
                lines.append("")
        lines.append(tr("changes_question"))
        self.bell()
        self.deiconify()
        self.lift()
        if messagebox.askyesno("NetISO Manager", "\n".join(lines)):
            self._push()

    # ---- console

    def _push(self):
        if self.busy:
            return
        settings = self._collect_settings()
        save_settings(settings)
        self._refresh_pc_ip()
        if not settings["console_ip"]:
            messagebox.showwarning("NetISO Manager", tr("need_ip"))
            return
        if not self.games:
            messagebox.showwarning("NetISO Manager", tr("no_games"))
            return
        try:
            with open(STUB_PATH, "rb") as f:
                stub = f.read()
        except OSError as error:
            messagebox.showerror("NetISO Manager", tr("stub_missing", error=error))
            return
        games = list(self.games)
        self.busy = True
        self.push_button.configure(state="disabled")
        self._log(tr("sync_start", count=len(games), host=settings["console_ip"]))

        def work():
            try:
                states = netiso_console.sync(
                    dict(settings), games, stub, lambda text: self.events.put(("log", text)))
                sent = sum(1 for state in states.values() if state == "netiso")
                message = tr("sync_done", netiso=sent, console=len(states) - sent)
            except (netiso_console.ConsoleError, netiso_iso.IsoError) as error:
                states, message = None, tr("sync_failed", error=error)
            self.events.put(("pushed", (message, states)))

        threading.Thread(target=work, daemon=True).start()

    # ---- server

    def _autostart_server(self, attempts=10):
        """Starts the server at launch, waiting for a previous instance to release the port."""
        if self.server.running:
            return
        try:
            self.server.start()
        except OSError:
            if attempts > 1:
                if attempts == 10:
                    self._log(tr("port_busy_retry", port=self.server.port))
                self.after(3000, self._autostart_server, attempts - 1)
            else:
                self._log(tr("server_failed", port=self.server.port))
        self._show_server_state()

    def _toggle_server(self):
        if self.server.running:
            self.server.stop()
        else:
            try:
                self.server.start()
            except OSError:
                self._log(tr("server_failed", port=self.server.port))
                messagebox.showerror("NetISO Manager",
                                     tr("port_busy_dialog", port=self.server.port))
        self._show_server_state()

    def _show_server_state(self):
        running = self.server.running
        self.server_state.set(tr("server_running", port=self.server.port) if running
                              else tr("server_stopped"))
        self.server_button.configure(text=tr("server_stop") if running else tr("server_start"))

    def _close(self):
        save_settings(self._collect_settings())
        self.server.stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
