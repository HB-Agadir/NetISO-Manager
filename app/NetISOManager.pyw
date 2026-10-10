"""NetISO Manager: pick ISO folders, show the games in Aurora, serve them to the console."""

import json
import os
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import netiso_console
import netiso_iso
import netiso_server

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STUB_PATH = os.path.join(APP_DIR, "stub.xex")
SETTINGS_PATH = os.path.join(os.environ.get("APPDATA", APP_DIR), "NetISOManager", "settings.json")
DEFAULTS = {
    "folders": [],
    "recursive": True,
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
        return "inconnue"
    finally:
        probe.close()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NetISO Manager")
        self.geometry("980x680")
        self.minsize(820, 560)
        self.settings = load_settings()
        self.games = []
        self.states = {}
        self.events = queue.Queue()
        self.server = netiso_server.NetIsoServer(lambda kind, text: self.events.put(("log", text)))
        self.busy = False

        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(100, self._drain_events)
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

        folders = ttk.LabelFrame(self, text="1. Dossiers contenant vos ISOs")
        folders.pack(fill="x", **pad)
        self.folder_list = tk.Listbox(folders, height=4, activestyle="none")
        self.folder_list.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        for folder in self.settings["folders"]:
            self.folder_list.insert("end", folder)
        buttons = ttk.Frame(folders)
        buttons.pack(side="right", fill="y", padx=8, pady=8)
        ttk.Button(buttons, text="Ajouter un dossier...", command=self._add_folder).pack(fill="x")
        ttk.Button(buttons, text="Retirer", command=self._remove_folder).pack(fill="x", pady=4)
        self.recursive = tk.BooleanVar(value=self.settings["recursive"])
        ttk.Checkbutton(buttons, text="Inclure les sous-dossiers", variable=self.recursive,
                        command=self._scan).pack(fill="x")
        ttk.Button(buttons, text="Actualiser", command=self._scan).pack(fill="x", pady=4)

        games = ttk.LabelFrame(self, text="2. Jeux detectes")
        games.pack(fill="both", expand=True, **pad)
        columns = ("name", "state", "title", "disc", "size", "folder")
        self.tree = ttk.Treeview(games, columns=columns, show="headings", height=8)
        for column, label, width, anchor in (
                ("name", "Jeu", 260, "w"), ("state", "Etat", 170, "w"),
                ("title", "Title ID", 80, "center"),
                ("disc", "Disque", 60, "center"), ("size", "Taille", 80, "e"),
                ("folder", "Dossier", 260, "w")):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, anchor=anchor)
        scroll = ttk.Scrollbar(games, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scroll.pack(side="right", fill="y", padx=(0, 8), pady=8)

        row = ttk.Frame(self)
        row.pack(fill="x", **pad)

        console = ttk.LabelFrame(row, text="3. Console")
        console.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.console_ip = tk.StringVar(value=self.settings["console_ip"])
        self.ftp_user = tk.StringVar(value=self.settings["ftp_user"])
        self.ftp_password = tk.StringVar(value=self.settings["ftp_password"])
        self.remote_root = tk.StringVar(value=self.settings["remote_root"])
        self.console_folders = tk.StringVar(
            value="; ".join(self.settings["console_game_folders"]))
        for line, (label, variable, width) in enumerate((
                ("Adresse IP de la console", self.console_ip, 18),
                ("Utilisateur FTP", self.ftp_user, 18),
                ("Mot de passe FTP", self.ftp_password, 18),
                ("Dossier des tuiles", self.remote_root, 18),
                ("Jeux installes (dossiers)", self.console_folders, 18))):
            ttk.Label(console, text=label).grid(row=line, column=0, sticky="w", padx=8, pady=3)
            ttk.Entry(console, textvariable=variable, width=width).grid(
                row=line, column=1, sticky="we", padx=8, pady=3)
        console.columnconfigure(1, weight=1)
        self.push_button = ttk.Button(console, text="Synchroniser avec Aurora",
                                      command=self._push)
        self.push_button.grid(row=5, column=0, columnspan=2, sticky="we", padx=8, pady=8)

        server = ttk.LabelFrame(row, text="4. Serveur")
        server.pack(side="left", fill="both", expand=True, padx=(6, 0))
        self.server_state = tk.StringVar(value="Arrete")
        self.pc_ip = tk.StringVar()
        ttk.Label(server, text="Etat").grid(row=0, column=0, sticky="w", padx=8, pady=3)
        ttk.Label(server, textvariable=self.server_state).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(server, text="Adresse de ce PC").grid(row=1, column=0, sticky="w", padx=8, pady=3)
        ttk.Label(server, textvariable=self.pc_ip).grid(row=1, column=1, sticky="w", padx=8)
        ttk.Label(server, text="(a mettre dans NetISO.xex.txt sur la console)",
                  foreground="#666666").grid(row=2, column=0, columnspan=2, sticky="w", padx=8)
        self.autostart = tk.BooleanVar(value=self.settings["autostart_server"])
        ttk.Checkbutton(server, text="Demarrer le serveur a l'ouverture",
                        variable=self.autostart).grid(row=3, column=0, columnspan=2, sticky="w",
                                                      padx=8, pady=3)
        self.server_button = ttk.Button(server, text="Demarrer le serveur",
                                        command=self._toggle_server)
        self.server_button.grid(row=4, column=0, columnspan=2, sticky="we", padx=8, pady=8)
        server.columnconfigure(1, weight=1)

        log = ttk.LabelFrame(self, text="Journal")
        log.pack(fill="both", **pad)
        self.log = tk.Text(log, height=7, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=8, pady=8)
        self._refresh_pc_ip()

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
            "folders": list(self.folder_list.get(0, "end")),
            "recursive": self.recursive.get(),
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
        folder = filedialog.askdirectory(title="Choisir un dossier d'ISOs")
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

    def _scan(self):
        settings = self._collect_settings()
        save_settings(settings)
        folders, recursive = list(settings["folders"]), settings["recursive"]
        self._log("Recherche des ISOs dans %d dossier(s)..." % len(folders))

        def work():
            self.events.put(("scanned", netiso_iso.scan(folders, recursive)))

        threading.Thread(target=work, daemon=True).start()

    def _show_games(self, games, errors):
        self.games = games
        self.server.set_games(games)
        self._fill_tree()
        self._log("%d jeu(x) detecte(s)" % len(games))
        for path, message in errors:
            self._log("Ignore: %s (%s)" % (path, message))

    def _fill_tree(self):
        labels = {"netiso": "Dans Aurora (NetISO)", "console": "Deja sur la console"}
        self.tree.delete(*self.tree.get_children())
        for game in self.games:
            self.tree.insert("", "end", values=(
                game.name, labels.get(self.states.get(game.name), "A synchroniser"),
                "%08X" % game.title_id, "%d/%d" % (game.disc, game.discs),
                "%.1f Go" % (game.size / 1e9), os.path.dirname(game.path)))

    # ---- console

    def _push(self):
        if self.busy:
            return
        settings = self._collect_settings()
        save_settings(settings)
        self._refresh_pc_ip()
        if not settings["console_ip"]:
            messagebox.showwarning("NetISO Manager", "Indiquez l'adresse IP de la console.")
            return
        if not self.games:
            messagebox.showwarning("NetISO Manager", "Aucun jeu detecte. Ajoutez un dossier d'ISOs.")
            return
        try:
            with open(STUB_PATH, "rb") as f:
                stub = f.read()
        except OSError as error:
            messagebox.showerror("NetISO Manager", "Lanceur introuvable: %s" % error)
            return
        games = list(self.games)
        self.busy = True
        self.push_button.configure(state="disabled")
        self._log("Synchronisation de %d jeu(x) avec %s..." % (len(games), settings["console_ip"]))

        def work():
            try:
                states = netiso_console.sync(
                    dict(settings), games, stub, lambda text: self.events.put(("log", text)))
                sent = sum(1 for state in states.values() if state == "netiso")
                message = ("Termine: %d jeu(x) en NetISO, %d deja sur la console. "
                           "Lancez un scan dans Aurora." % (sent, len(states) - sent))
            except netiso_console.ConsoleError as error:
                states, message = None, "Echec de la synchronisation: %s" % error
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
                    self._log("Port %d occupe par un autre serveur NetISO, nouvel essai..."
                              % self.server.port)
                self.after(3000, self._autostart_server, attempts - 1)
            else:
                self._log("Le serveur n'a pas pu demarrer: fermez l'autre serveur NetISO, "
                          "puis cliquez sur Demarrer le serveur.")
        self._show_server_state()

    def _toggle_server(self):
        if self.server.running:
            self.server.stop()
        else:
            try:
                self.server.start()
            except OSError as error:
                self._log("Impossible de demarrer le serveur: %s" % error)
                messagebox.showerror(
                    "NetISO Manager",
                    "Le port %d est deja utilise. Fermez l'autre serveur NetISO puis reessayez."
                    % self.server.port)
        self._show_server_state()

    def _show_server_state(self):
        running = self.server.running
        self.server_state.set("En marche, port %d" % self.server.port if running else "Arrete")
        self.server_button.configure(text="Arreter le serveur" if running else "Demarrer le serveur")

    def _close(self):
        save_settings(self._collect_settings())
        self.server.stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()
