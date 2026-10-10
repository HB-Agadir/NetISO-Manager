"""NetISO server: serves ISO images to the console's NetISO.xex plugin.

Speaks the protocol of the original server (20-byte big-endian request header
with the magic "ISVR"), but serves a list of games that can live in any number
of folders.
"""

import socket
import struct
import threading

from netiso_i18n import tr

PORT = 4323
HEADER = struct.Struct(">4sHHQI")
MAGIC = b"ISVR"
SECTOR = 2048
DISABLE_NAME = "[Disable Current ISO]"

CMD_PING = 0
CMD_GET_SIZE = 1
CMD_HAS_TYPE1 = 2
CMD_READ = 3
CMD_GET_NAME = 4
CMD_MOUNT = 5


def _recv_exact(conn, size):
    chunks = []
    while size > 0:
        chunk = conn.recv(size)
        if not chunk:
            raise ConnectionError("closed")
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


class NetIsoServer:
    """Listens for consoles and serves the current list of games."""

    def __init__(self, on_event=None, port=PORT):
        self.port = port
        self._on_event = on_event or (lambda kind, text: None)
        self._games = []
        self._lock = threading.Lock()
        self._listener = None
        self._clients = set()

    @property
    def running(self):
        return self._listener is not None

    def set_games(self, games):
        with self._lock:
            self._games = list(games)

    def start(self):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            listener.bind(("0.0.0.0", self.port))
            listener.listen(4)
        except OSError:
            listener.close()
            raise
        self._listener = listener
        threading.Thread(target=self._accept_loop, args=(listener,), daemon=True).start()
        self._on_event("server", tr("server_started", port=self.port))

    def stop(self):
        listener, self._listener = self._listener, None
        if listener is None:
            return
        listener.close()
        with self._lock:
            clients = list(self._clients)
        for conn in clients:
            try:
                conn.close()
            except OSError:
                pass
        self._on_event("server", tr("server_stopped_msg"))

    def _accept_loop(self, listener):
        while True:
            try:
                conn, address = listener.accept()
            except OSError:
                return
            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            with self._lock:
                self._clients.add(conn)
            threading.Thread(target=self._serve, args=(conn, address[0]), daemon=True).start()

    def _find(self, name):
        wanted = name.lower()
        with self._lock:
            for game in self._games:
                if game.name.lower() == wanted:
                    return game
            # Tiles made for the original server name the ISO file itself.
            for game in self._games:
                if game.path.lower().endswith("\\" + wanted) or game.path.lower().endswith("/" + wanted):
                    return game
        return None

    def _serve(self, conn, address):
        self._on_event("client", tr("client_connected", address=address))
        mounted = None
        try:
            while True:
                magic, cmd, index, offset, length = HEADER.unpack(_recv_exact(conn, HEADER.size))
                if magic != MAGIC:
                    raise ConnectionError("bad request")
                if cmd == CMD_PING:
                    conn.sendall(b"ISVRokOK")
                elif cmd == CMD_GET_SIZE:
                    sectors = 0
                    if mounted is not None:
                        mounted.seek(0, 2)
                        sectors = mounted.tell() // SECTOR
                    conn.sendall(struct.pack(">II", sectors, SECTOR))
                elif cmd == CMD_HAS_TYPE1:
                    conn.sendall(struct.pack(">I", 0))
                elif cmd == CMD_READ:
                    if mounted is None:
                        raise ConnectionError("read without a mounted ISO")
                    mounted.seek(offset)
                    conn.sendall(mounted.read(length).ljust(length, b"\0"))
                elif cmd == CMD_GET_NAME:
                    with self._lock:
                        name = self._games[index].name if index < len(self._games) else ""
                    conn.sendall(name.encode("ascii", "replace")[:length].ljust(length, b"\0"))
                elif cmd == CMD_MOUNT:
                    raw = _recv_exact(conn, length).decode("ascii", "replace")
                    name = raw.replace("\\Mount", "").replace("\\", "").replace("\0", "")
                    if mounted is not None:
                        mounted.close()
                        mounted = None
                    game = None if name == DISABLE_NAME else self._find(name)
                    if game is not None:
                        try:
                            mounted = open(game.path, "rb", buffering=0)
                        except OSError as error:
                            self._on_event("mount", tr("open_failed", path=game.path, error=error))
                    if mounted is not None:
                        self._on_event("mount", tr("game_mounted", name=game.name))
                    elif name == DISABLE_NAME:
                        self._on_event("mount", tr("no_game_mounted"))
                    elif game is None:
                        self._on_event("mount", tr("unknown_game", name=name))
                    conn.sendall(struct.pack(">I", 1 if mounted is not None else 0))
                else:
                    raise ConnectionError("unknown command %d" % cmd)
        except (ConnectionError, OSError, struct.error) as error:
            if self.running:
                self._on_event("client", tr("client_disconnected", address=address))
        finally:
            if mounted is not None:
                mounted.close()
            with self._lock:
                self._clients.discard(conn)
            try:
                conn.close()
            except OSError:
                pass
