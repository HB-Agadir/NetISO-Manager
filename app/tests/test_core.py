import os
import socket
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_console
import netiso_iso
import netiso_server

HEADER = struct.Struct(">4sHHQI")


def make_xex(title_id, media_id):
    """Minimal XEX2 header holding only an execution info entry."""
    header = bytearray(0x40)
    header[0:4] = b"XEX2"
    struct.pack_into(">I", header, 0x14, 1)
    struct.pack_into(">II", header, 0x18, netiso_iso.XEX_EXECUTION_INFO, 0x20)
    struct.pack_into(">IIIIBBBB", header, 0x20, media_id, 0, 0, title_id, 0, 0, 1, 2)
    return bytes(header)


def make_iso(path, partition, xex):
    """Raw image with an XDVDFS root directory holding other.bin and default.xex."""
    sector = netiso_iso.SECTOR
    entries = bytearray(sector)
    # Root entry "other.bin" with "default.xex" as its right child at offset 28.
    struct.pack_into("<HHIIBB", entries, 0, 0, 7, 40, 4, 0, 9)
    entries[14:23] = b"other.bin"
    struct.pack_into("<HHIIBB", entries, 28, 0, 0, 34, len(xex), 0, 11)
    entries[42:53] = b"DEFAULT.XEX"
    with open(path, "wb") as f:
        f.seek(partition + 32 * sector)
        f.write(netiso_iso.XDVDFS_MAGIC + struct.pack("<II", 33, sector))
        f.seek(partition + 33 * sector)
        f.write(entries)
        f.seek(partition + 34 * sector)
        f.write(xex.ljust(sector, b"\0"))
        f.seek(partition + 41 * sector - 1)
        f.write(b"\0")


class IsoTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_reads_ids_from_each_disc_layout(self):
        xex = make_xex(0x4D530A26, 0x3528321A)
        for partition in (0, 0x2080000):
            path = os.path.join(self.dir.name, "game%X.iso" % partition)
            make_iso(path, partition, xex)
            self.assertEqual(netiso_iso.read_iso_ids(path), (0x4D530A26, 0x3528321A, 1, 2))

    def test_rejects_a_file_that_is_not_a_disc_image(self):
        path = os.path.join(self.dir.name, "junk.iso")
        with open(path, "wb") as f:
            f.write(b"\0" * 0x20000)
        with self.assertRaises(netiso_iso.IsoError):
            netiso_iso.read_iso_ids(path)

    def test_scan_gives_unique_fatx_safe_names_and_reports_bad_files(self):
        xex = make_xex(1, 2)
        for folder in ("a", "b"):
            os.mkdir(os.path.join(self.dir.name, folder))
            make_iso(os.path.join(self.dir.name, folder, "Jeu: édition.iso".replace(":", "")), 0, xex)
        with open(os.path.join(self.dir.name, "a", "bad.iso"), "wb") as f:
            f.write(b"x")
        games, errors = netiso_iso.scan(
            [os.path.join(self.dir.name, "a"), os.path.join(self.dir.name, "b")], False)
        self.assertEqual([g.name for g in games], ["Jeu _dition", "Jeu _dition 2"])
        self.assertEqual(len(errors), 1)
        for game in games:
            self.assertLessEqual(len(game.name), netiso_iso.FATX_NAME_MAX)

    def real_stub(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stub.xex"), "rb") as f:
            return f.read()

    def test_stamp_stub_writes_the_game_ids_and_keeps_the_header_hash_valid(self):
        path = os.path.join(self.dir.name, "g.iso")
        make_iso(path, 0, make_xex(0xAABBCCDD, 0x11223344))
        games, _ = netiso_iso.scan([self.dir.name], False)
        stub = self.real_stub()
        files = netiso_iso.tile_files(stub, games[0])
        stamped = files["default.xex"]
        offset = netiso_iso.xex_execution_info_offset(stamped)
        self.assertEqual(struct.unpack_from(">I", stamped, offset)[0], 0x11223344)
        self.assertEqual(struct.unpack_from(">I", stamped, offset + 12)[0], 0xAABBCCDD)
        hash_at = struct.unpack_from(">I", stamped, 0x10)[0] + netiso_iso.XEX_HEADER_HASH
        self.assertEqual(stamped[hash_at:hash_at + 20], netiso_iso.xex_header_hash(stamped))
        self.assertNotEqual(stamped[hash_at:hash_at + 20], stub[hash_at:hash_at + 20])
        self.assertEqual(len(stamped), len(stub))
        self.assertEqual(files["netiso.cfg"], b"g\r\n")

    def test_stamp_stub_refuses_a_stub_whose_header_hash_it_cannot_reproduce(self):
        path = os.path.join(self.dir.name, "g.iso")
        make_iso(path, 0, make_xex(1, 2))
        games, _ = netiso_iso.scan([self.dir.name], False)
        broken = bytearray(self.real_stub())
        broken[0x20] ^= 0xFF
        with self.assertRaises(netiso_iso.IsoError):
            netiso_iso.stamp_stub(bytes(broken), games[0])


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.games = []
        for folder, name in (("x", "Alpha"), ("y", "Beta")):
            os.mkdir(os.path.join(self.dir.name, folder))
            path = os.path.join(self.dir.name, folder, name + " file.iso")
            with open(path, "wb") as f:
                f.write((name.encode() * 4096)[:3 * netiso_server.SECTOR])
            self.games.append(netiso_iso.Game(path, name, 1, 2, 1, 1))
        self.events = []
        self.server = netiso_server.NetIsoServer(lambda kind, text: self.events.append((kind, text)), port=0)
        self.server.set_games(self.games)
        self.server.start()
        self.addCleanup(self.server.stop)
        port = self.server._listener.getsockname()[1]
        self.conn = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.addCleanup(self.conn.close)

    def request(self, cmd, reply_size, index=0, offset=0, length=0, payload=b""):
        self.conn.sendall(HEADER.pack(b"ISVR", cmd, index, offset, length) + payload)
        data = b""
        while len(data) < reply_size:
            data += self.conn.recv(reply_size - len(data))
        return data

    def mount(self, name):
        payload = ("\\%s\\Mount\\" % name).encode()
        return struct.unpack(">I", self.request(5, 4, length=len(payload), payload=payload))[0]

    def test_ping(self):
        self.assertEqual(self.request(0, 8), b"ISVRokOK")

    def test_lists_games_from_every_folder_then_an_empty_name(self):
        names = [self.request(4, 64, index=i, length=64).rstrip(b"\0") for i in range(3)]
        self.assertEqual(names, [b"Alpha", b"Beta", b""])

    def test_size_is_zero_until_a_game_is_mounted(self):
        self.assertEqual(struct.unpack(">II", self.request(1, 8)), (0, netiso_server.SECTOR))
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(struct.unpack(">II", self.request(1, 8)), (3, netiso_server.SECTOR))

    def test_reads_the_mounted_game_and_switches_games(self):
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.request(3, 10, offset=5, length=10), (b"Alpha" * 3)[:10])
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(self.request(3, 8, offset=4, length=8), b"BetaBeta")

    def test_mount_by_original_iso_file_name(self):
        self.assertEqual(self.mount("Alpha file.iso"), 1)

    def test_unknown_game_and_disable_unmount(self):
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.mount("Missing"), 0)
        self.assertEqual(struct.unpack(">II", self.request(1, 8))[0], 0)
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.mount(netiso_server.DISABLE_NAME), 0)
        self.assertEqual(struct.unpack(">II", self.request(1, 8))[0], 0)


class SyncPlanTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def game(self, name, title_id, disc=1):
        path = os.path.join(self.dir.name, name + ".iso")
        open(path, "wb").close()
        return netiso_iso.Game(path, name, title_id, 0, disc, 2)

    def test_console_copy_wins_over_the_iso(self):
        a, b = self.game("A", 0x111), self.game("B", 0x222)
        to_send, to_remove = netiso_console.plan_sync([a, b], {(0x111, 1)}, ["A", "B"])
        self.assertEqual([g.name for g in to_send], ["B"])
        self.assertEqual(to_remove, ["A"])

    def test_tile_comes_back_when_the_console_copy_is_deleted(self):
        a = self.game("A", 0x111)
        to_send, to_remove = netiso_console.plan_sync([a], set(), [])
        self.assertEqual([g.name for g in to_send], ["A"])
        self.assertEqual(to_remove, [])

    def test_only_the_installed_disc_of_a_multi_disc_game_is_skipped(self):
        d1, d2 = self.game("G1", 0x333, 1), self.game("G2", 0x333, 2)
        to_send, _ = netiso_console.plan_sync([d1, d2], {(0x333, 1)}, [])
        self.assertEqual([g.name for g in to_send], ["G2"])

    def test_container_install_skips_every_disc(self):
        d1, d2 = self.game("G1", 0x333, 1), self.game("G2", 0x333, 2)
        to_send, _ = netiso_console.plan_sync([d1, d2], {(0x333, None)}, [])
        self.assertEqual(to_send, [])

    def test_tile_of_an_iso_removed_from_the_pc_is_removed(self):
        a = self.game("A", 0x111)
        _, to_remove = netiso_console.plan_sync([a], set(), ["a", "Gone"])
        self.assertEqual(to_remove, ["Gone"])

    def test_list_line_parsing(self):
        self.assertEqual(netiso_console.parse_list_line(
            "drwxr-xr-x 1 root root 0 Jan 01 2020 Call of Duty - Black Ops III"),
            ("Call of Duty - Black Ops III", True))
        self.assertEqual(netiso_console.parse_list_line(
            "-rw-r--r-- 1 root root 3481600 Jan 01 2020 default.xex"), ("default.xex", False))
        self.assertIsNone(netiso_console.parse_list_line("total 3"))

    def test_xex_game_key(self):
        self.assertEqual(netiso_console.xex_game_key(make_xex(0x4D530A26, 5)), (0x4D530A26, 1))
        self.assertIsNone(netiso_console.xex_game_key(b"not a xex"))


if __name__ == "__main__":
    unittest.main()
