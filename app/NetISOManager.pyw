"""NetISO Manager: pick ISO folders, show the games in Aurora, serve them to the console."""

import json
import os
import queue
import socket
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk

import netiso_console
import netiso_i18n
import netiso_iso
import netiso_server
import netiso_winstart
from netiso_i18n import tr

# When frozen into an executable, bundled files live in the unpacking folder.
APP_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
SCRIPT_PATH = os.path.abspath(__file__)
STUB_PATH = os.path.join(APP_DIR, "stub.xex")
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA", APP_DIR), "NetISOManager", "settings.json")
TRACE_PATH = os.path.join(os.path.dirname(SETTINGS_PATH), "server_trace.log")
DONATION_URL = "https://ko-fi.com/x360remap"
WATCH_INTERVAL_MS = 15000
STATUS_INTERVAL_MS = 1000
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
    "welcome_shown": False,
    "active_discs": {},  # Title ID (hex) -> disc number launched by the game's tile
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
    """Address of this PC on the network that reaches the console, or None."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((toward or "192.168.1.1", 9))
        return probe.getsockname()[0]
    except OSError:
        return None
    finally:
        probe.close()


class App(tk.Tk):
    def __init__(self, minimized=False):
        super().__init__()
        self.title("NetISO Manager")
        self.geometry("1040x760")
        self.minsize(900, 640)
        self.settings = load_settings()
        netiso_i18n.set_language(self.settings["language"])
        self.tiles = []
        self.states = {}
        self.events = queue.Queue()
        self.server = netiso_server.NetIsoServer(self._server_event)
        self.busy = False
        self.scanned = None      # {path: size} at the last full scan
        self.last_seen = None    # {path: size} at the previous watch poll
        self.prompt_next_scan = False
        self.last_bytes = 0

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._drain_events)
        self.after(WATCH_INTERVAL_MS, self._watch)
        self.after(STATUS_INTERVAL_MS, self._show_playing)
        if self.settings["folders"]:
            self._scan()
        if self.settings["autostart_server"]:
            self._autostart_server()
        if minimized:
            self.iconify()
        elif not self.settings["welcome_shown"]:
            self.after(800, self._welcome)

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
        support = ttk.Label(top, text=tr("support_link"), foreground="#b03060", cursor="hand2")
        support.pack(side="left")
        support.bind("<Button-1>", lambda _event: self._open_donation_page())

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
        bar = ttk.Frame(games)
        bar.pack(side="bottom", fill="x", padx=8, pady=(0, 8))
        ttk.Button(bar, text=tr("next_disc"), command=self._next_disc).pack(side="left")
        columns = ("name", "state", "title", "disc", "size", "file")
        self.tree = ttk.Treeview(games, columns=columns, show="headings", height=8,
                                 selectmode="browse")
        for column, key, width, anchor in (
                ("name", "col_game", 250, "w"), ("state", "col_state", 160, "w"),
                ("title", "col_title", 80, "center"), ("disc", "col_disc", 80, "center"),
                ("size", "col_size", 80, "e"), ("file", "col_folder", 300, "w")):
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
        self.push_button.grid(row=5, column=0, columnspan=2, sticky="we", padx=8, pady=(8, 2))
        self.setup_button = ttk.Button(console, text=tr("setup_button"), command=self._setup)
        self.setup_button.grid(row=6, column=0, columnspan=2, sticky="we", padx=8, pady=(2, 8))
        if self.busy:
            self.push_button.configure(state="disabled")
            self.setup_button.configure(state="disabled")

        server = ttk.LabelFrame(row, text=tr("server_frame"))
        server.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.server_state = tk.StringVar()
        self.playing = tk.StringVar(value=tr("nothing_playing"))
        self.pc_ip = tk.StringVar()
        for line, (key, variable) in enumerate((
                ("server_state", self.server_state), ("now_playing", self.playing),
                ("pc_ip", self.pc_ip))):
            ttk.Label(server, text=tr(key)).grid(row=line, column=0, sticky="w", padx=8, pady=3)
            ttk.Label(server, textvariable=variable).grid(row=line, column=1, sticky="w", padx=8)
        ttk.Label(server, text=tr("pc_ip_hint"), foreground="#666666").grid(
            row=3, column=0, columnspan=2, sticky="w", padx=8)
        self.autostart = tk.BooleanVar(value=self.settings["autostart_server"])
        ttk.Checkbutton(server, text=tr("autostart"), variable=self.autostart).grid(
            row=4, column=0, columnspan=2, sticky="w", padx=8, pady=(3, 0))
        self.with_windows = tk.BooleanVar(value=netiso_winstart.is_enabled())
        ttk.Checkbutton(server, text=tr("start_with_windows"), variable=self.with_windows,
                        command=self._toggle_windows_start).grid(
            row=5, column=0, columnspan=2, sticky="w", padx=8)
        self.server_button = ttk.Button(server, command=self._toggle_server)
        self.server_button.grid(row=6, column=0, columnspan=2, sticky="we", padx=8, pady=8)
        server.columnconfigure(1, weight=1)

        log = ttk.LabelFrame(body, text=tr("log_frame"))
        log.pack(fill="both", **pad)
        self.log = tk.Text(log, height=6, state="disabled", wrap="word")
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

    # ---- support

    def _open_donation_page(self):
        webbrowser.open(DONATION_URL)

    def _welcome(self):
        """Shown once, at the first start: says the app is free and how to support it."""
        self.settings["welcome_shown"] = True
        save_settings(self._collect_settings())
        if messagebox.askyesno("NetISO Manager", tr("welcome")):
            self._open_donation_page()

    # ---- helpers

    def _server_event(self, kind, text):
        """Called from server threads: journal lines go to the window, traces to a file."""
        if kind == "disc":
            self.events.put(("disc", text))
            text = "%s -> disc %d" % (text[0], text[2])
        elif kind != "trace":
            self.events.put(("log", text))
        try:
            with open(TRACE_PATH, "a", encoding="utf-8") as f:
                f.write("%s  %s  %s\n" % (time.strftime("%H:%M:%S"), kind, text))
        except OSError:
            pass

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
                    self._show_tiles(*payload)
                elif kind == "disc":
                    name, title_id, disc = payload
                    self.settings["active_discs"]["%08X" % title_id] = disc
                    save_settings(self._collect_settings())
                    self._fill_tree()
                    self._log(tr("disc_selected", name=name, disc=disc))
                elif kind == "watched":
                    self._compare_snapshot(payload)
                elif kind == "pushed":
                    self._set_busy(False)
                    message, states = payload
                    if states is not None:
                        self.states = states
                        self._fill_tree()
                    self._log(message)
                elif kind == "setup":
                    self._set_busy(False)
                    self._setup_finished(payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_events)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.push_button.configure(state=state)
        self.setup_button.configure(state=state)

    def _refresh_pc_ip(self):
        self.pc_ip.set(local_ip(self.console_ip.get().strip()) or tr("pc_ip_unknown"))

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

    def _show_tiles(self, tiles, errors, snapshot):
        before = {tile.name for tile in self.tiles}
        for tile in tiles:
            chosen = self.settings["active_discs"].get("%08X" % tile.title_id)
            if chosen in [game.disc for game in tile.games]:
                tile.active = chosen
        self.tiles = tiles
        self.scanned = snapshot
        self.server.set_tiles(tiles)
        self._fill_tree()
        self._log(tr("games_found", count=len(tiles)))
        for path, message in errors:
            self._log(tr("ignored", path=path, reason=message))
        if self.prompt_next_scan:
            self.prompt_next_scan = False
            after = {tile.name for tile in tiles}
            self._offer_transfer(sorted(after - before), sorted(before - after))

    def _fill_tree(self):
        labels = {"netiso": tr("state_netiso"), "console": tr("state_console")}
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for tile in self.tiles:
            game = tile.game()
            disc = (tr("disc_of", disc=game.disc, count=len(tile.games)) if tile.multi_disc
                    else "%d/%d" % (game.disc, game.discs))
            self.tree.insert("", "end", iid=tile.name, values=(
                tile.name, labels.get(self.states.get(tile.name), tr("state_pending")),
                "%08X" % tile.title_id, disc, tr("size_gb", size=game.size / 1e9), game.path))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])

    def _next_disc(self):
        selected = self.tree.selection()
        tile = next((t for t in self.tiles if selected and t.name == selected[0]), None)
        if tile is None or not tile.multi_disc:
            messagebox.showinfo("NetISO Manager", tr("select_multi_disc"))
            return
        disc = tile.next_disc()
        self.settings["active_discs"]["%08X" % tile.title_id] = disc
        save_settings(self._collect_settings())
        self._fill_tree()
        self._log(tr("disc_selected", name=tile.name, disc=disc))
        playing, _total = self.server.status()
        if playing and playing[0] == tile.name:
            self._log(tr("disc_in_use", name=tile.name))

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

    def _console_settings(self):
        """Saves and returns the settings, or None after telling what is missing."""
        settings = self._collect_settings()
        save_settings(settings)
        self._refresh_pc_ip()
        if not settings["console_ip"]:
            messagebox.showwarning("NetISO Manager", tr("need_ip"))
            return None
        return dict(settings)

    def _push(self):
        if self.busy:
            return
        settings = self._console_settings()
        if settings is None:
            return
        if not self.tiles:
            messagebox.showwarning("NetISO Manager", tr("no_games"))
            return
        try:
            with open(STUB_PATH, "rb") as f:
                stub = f.read()
        except OSError as error:
            messagebox.showerror("NetISO Manager", tr("stub_missing", error=error))
            return
        tiles = list(self.tiles)
        self._set_busy(True)
        self._log(tr("sync_start", count=len(tiles), host=settings["console_ip"]))

        def work():
            try:
                states = netiso_console.sync(
                    settings, tiles, stub, lambda text: self.events.put(("log", text)))
                sent = sum(1 for state in states.values() if state == "netiso")
                message = tr("sync_done", netiso=sent, console=len(states) - sent)
            except (netiso_console.ConsoleError, netiso_iso.IsoError) as error:
                states, message = None, tr("sync_failed", error=error)
            self.events.put(("pushed", (message, states)))

        threading.Thread(target=work, daemon=True).start()

    def _setup(self, plugin_file=None):
        if self.busy:
            return
        settings = self._console_settings()
        if settings is None:
            return
        pc_ip = local_ip(settings["console_ip"])
        if pc_ip is None:
            messagebox.showwarning("NetISO Manager", tr("need_ip"))
            return
        if plugin_file is None and not messagebox.askyesno(
                "NetISO Manager", tr("setup_confirm", ip=pc_ip)):
            return
        self._set_busy(True)

        def work():
            try:
                changed = netiso_console.setup_console(
                    settings, pc_ip, plugin_file, lambda text: self.events.put(("log", text)))
                result = ("done", changed)
            except netiso_console.PluginMissing as error:
                result = ("plugin", str(error))
            except (netiso_console.ConsoleError, OSError) as error:
                result = ("failed", str(error))
            self.events.put(("setup", result))

        threading.Thread(target=work, daemon=True).start()

    def _setup_finished(self, result):
        kind, detail = result
        if kind == "done":
            self._log(tr("setup_done_reboot") if detail else tr("setup_done"))
        elif kind == "plugin":
            self._log(detail)
            plugin_file = filedialog.askopenfilename(
                title=tr("choose_plugin"), filetypes=[("NetISO.xex", "*.xex")])
            if plugin_file:
                self._setup(plugin_file)
        else:
            self._log(tr("setup_failed", error=detail))

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

    def _show_playing(self):
        self.after(STATUS_INTERVAL_MS, self._show_playing)
        playing, total = self.server.status()
        rate = (total - self.last_bytes) / 1e6 / (STATUS_INTERVAL_MS / 1000)
        self.last_bytes = total
        self.playing.set(tr("playing_value", name=playing[0], disc=playing[1], rate=rate)
                         if playing else tr("nothing_playing"))

    def _toggle_windows_start(self):
        try:
            netiso_winstart.set_enabled(self.with_windows.get(), SCRIPT_PATH)
        except OSError as error:
            self._log(str(error))
        self.with_windows.set(netiso_winstart.is_enabled())

    def _close(self):
        save_settings(self._collect_settings())
        self.server.stop()
        self.destroy()


if __name__ == "__main__":
    App(minimized=netiso_winstart.MINIMIZED_FLAG in sys.argv[1:]).mainloop()
