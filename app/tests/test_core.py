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
STUB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stub.xex")


def make_xex(title_id, media_id, disc=1, discs=1):
    """Minimal XEX2 header holding only an execution info entry."""
    header = bytearray(0x40)
    header[0:4] = b"XEX2"
    struct.pack_into(">I", header, 0x14, 1)
    struct.pack_into(">II", header, 0x18, netiso_iso.XEX_EXECUTION_INFO, 0x20)
    struct.pack_into(">IIIIBBBB", header, 0x20, media_id, 0, 0, title_id, 0, 0, disc, discs)
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


class TempDirCase(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def game(self, filename, title_id, disc=1, discs=1, media_id=None):
        path = os.path.join(self.dir.name, filename)
        if filename.endswith(".iso"):
            open(path, "wb").close()
        else:
            os.makedirs(path, exist_ok=True)
        self.media = getattr(self, "media", 0x1000) + 1
        # Every disc gets its own Media ID unless a test asks for the very same disc twice.
        return netiso_iso.Game(path, netiso_iso.clean_title(path), title_id,
                               self.media if media_id is None else media_id, disc, discs, size=0)


class IsoTests(TempDirCase):
    def test_reads_ids_from_each_disc_layout(self):
        xex = make_xex(0x4D530A26, 0x3528321A, 1, 2)
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

    def test_title_drops_region_and_language_tags_but_keeps_disc_tags(self):
        for filename, title in (
                ("Batman - Arkham Origins (USA, Europe) (En,Fr,De) (Disc 1).iso",
                 "Batman - Arkham Origins (Disc 1)"),
                ("Mafia II (USA, Europe) (Add-On Content Disc).iso",
                 "Mafia II (Add-On Content Disc)"),
                ("Metro 2033 (Europe) (En,De).iso", "Metro 2033"),
                ("Outfit, The (USA) [b].iso", "Outfit, The"),
                ("Gears of War - Judgment.iso", "Gears of War - Judgment"),
                ("(only tags).iso", "(only tags)")):
            self.assertEqual(netiso_iso.clean_title(filename), title)

    def test_scan_reports_bad_files_and_names_tiles_for_fatx(self):
        os.mkdir(os.path.join(self.dir.name, "a"))
        make_iso(os.path.join(self.dir.name, "a", "Jeu édition très longue " + "x" * 40 + ".iso"),
                 0, make_xex(1, 2))
        with open(os.path.join(self.dir.name, "a", "bad.iso"), "wb") as f:
            f.write(b"x")
        tiles, errors = netiso_iso.scan([os.path.join(self.dir.name, "a")], False)
        self.assertEqual(len(tiles), 1)
        self.assertEqual(len(errors), 1)
        self.assertLessEqual(len(tiles[0].name), netiso_iso.FATX_NAME_MAX)
        self.assertTrue(tiles[0].name.isascii())


class TileTests(TempDirCase):
    def test_discs_of_one_game_share_a_single_tile(self):
        games = [self.game("Big Game (USA) (Disc 2).iso", 0x500, 2, 3),
                 self.game("Big Game (USA) (Disc 1).iso", 0x500, 1, 3),
                 self.game("Big Game (USA) (Disc 3).iso", 0x500, 3, 3),
                 self.game("Other (Europe).iso", 0x600)]
        tiles = netiso_iso.build_tiles(games)
        self.assertEqual([t.name for t in tiles], ["Big Game", "Other"])
        self.assertEqual([g.disc for g in tiles[0].games], [1, 2, 3])
        self.assertTrue(tiles[0].multi_disc)
        self.assertFalse(tiles[1].multi_disc)

    def test_discs_that_all_claim_to_be_disc_1_are_grouped_by_their_file_names(self):
        games = [self.game("Snake V (USA) (Disc 2).iso", 0x4B4E085E),
                 self.game("Snake V (USA) (Disc 1).iso", 0x4B4E085E),
                 self.game("Metro 2033 (Europe).iso", 0x700),
                 self.game("Metro 2033 (USA).iso", 0x700)]
        tiles = netiso_iso.build_tiles(games)
        self.assertEqual([t.name for t in tiles], ["Metro 2033", "Metro 2033 (2)", "Snake V"])
        self.assertEqual([(g.disc, g.discs) for g in tiles[2].games], [(1, 2), (2, 2)])
        self.assertTrue(tiles[2].games[1].path.endswith("(Disc 2).iso"))

    def test_a_numbered_install_disc_joins_the_game_it_belongs_to(self):
        games = [self.game("Resident Evil 6 (USA, Europe) (Disc 2).iso", netiso_iso.GENERIC_DISC_TITLE),
                 self.game("Resident Evil 6 ~ Biohazard 6 (World) (Disc 1).iso", 0x43430819),
                 self.game("Mafia II (USA) (Add-On Content Disc).iso", netiso_iso.GENERIC_DISC_TITLE),
                 self.game("Mafia II (USA).iso", 0x545407E6)]
        tiles = netiso_iso.build_tiles(games)
        self.assertEqual([t.name for t in tiles],
                         ["Mafia II", "Mafia II (Add-On Content Disc)", "Resident Evil 6 ~ Biohazard 6"])
        saga = tiles[2]
        self.assertEqual([g.disc for g in saga.games], [1, 2])
        self.assertEqual(saga.title_id, 0x43430819)
        self.assertEqual(saga.game().disc, 1)
        self.assertEqual(saga.games[1].console_key, (netiso_iso.GENERIC_DISC_TITLE, 1))

    def test_an_install_disc_matching_several_games_stays_on_its_own(self):
        games = [self.game("Saga (Disc 3).iso", netiso_iso.GENERIC_DISC_TITLE),
                 self.game("Saga (Disc 1).iso", 0x111),
                 self.game("Saga II (Disc 1).iso", 0x222)]
        self.assertEqual(len(netiso_iso.build_tiles(games)), 3)

    def test_the_same_disc_as_iso_and_as_folder_gives_a_single_tile_using_the_iso(self):
        games = [self.game("Gears (USA) extracted", 0x4D5307D5, media_id=0x77),
                 self.game("Gears (USA).iso", 0x4D5307D5, media_id=0x77),
                 self.game("Gears (Japan).iso", 0x4D5307D5, media_id=0x78)]
        tiles = netiso_iso.build_tiles(games)
        self.assertEqual([t.name for t in tiles], ["Gears", "Gears (2)"])
        self.assertTrue(all(not g.is_folder for t in tiles for g in t.games))

    def test_a_set_present_as_isos_and_as_folders_does_not_get_mixed(self):
        games = [self.game("Saga (Disc 1).iso", 0x600, 1, 2), self.game("Saga (Disc 2).iso", 0x600, 2, 2),
                 self.game("Saga Disc 1", 0x600, 1, 2), self.game("Saga Disc 2", 0x600, 2, 2)]
        tiles = netiso_iso.build_tiles(games)
        self.assertEqual([t.name for t in tiles], ["Saga", "Saga (2)"])
        self.assertEqual([[g.is_folder for g in t.games] for t in tiles],
                         [[False, False], [True, True]])
        self.assertEqual([[g.disc for g in t.games] for t in tiles], [[1, 2], [1, 2]])

    def test_without_grouping_every_disc_keeps_its_own_tile(self):
        games = [self.game("Big Game (USA) (Disc 1).iso", 0x500, 1, 2),
                 self.game("Big Game (USA) (Disc 2).iso", 0x500, 2, 2),
                 self.game("Other (Europe).iso", 0x600)]
        tiles = netiso_iso.build_tiles(games, group_discs=False)
        self.assertEqual([t.name for t in tiles],
                         ["Big Game (Disc 1)", "Big Game (Disc 2)", "Other"])
        self.assertFalse(any(t.multi_disc for t in tiles))
        self.assertEqual([t.game().disc for t in tiles], [1, 2, 1])

    def test_a_tile_launches_disc_1_until_another_disc_is_chosen(self):
        tile = netiso_iso.build_tiles([self.game("G (Disc 1).iso", 7, 1, 2),
                                       self.game("G (Disc 2).iso", 7, 2, 2)])[0]
        self.assertEqual(tile.game().disc, 1)
        self.assertEqual(tile.next_disc(), 2)
        self.assertEqual(tile.game().disc, 2)
        self.assertEqual(tile.next_disc(), 1)

    def test_two_copies_of_the_same_game_get_two_tiles(self):
        games = [self.game("Metro 2033 (Europe).iso", 0x700),
                 self.game("Metro 2033 (USA).iso", 0x700),
                 self.game("Dup (Disc 1).iso", 0x800, 1, 2),
                 self.game("Dup (Disc 1) (Alt).iso", 0x800, 1, 2)]
        names = [t.name for t in netiso_iso.build_tiles(games)]
        self.assertEqual(names, ["Dup (Disc 1)", "Dup (Disc 1) (2)", "Metro 2033", "Metro 2033 (2)"])

    def test_discs_that_are_separate_games_keep_their_disc_tag(self):
        games = [self.game("Collection (USA) (Disc 1).iso", 0x900),
                 self.game("Collection (USA) (Disc 2).iso", 0x901),
                 self.game("Mafia II (USA) (Add-On Content Disc).iso", 0xFFED2000),
                 self.game("Mafia II (USA) (En,Fr).iso", 0x902)]
        names = [t.name for t in netiso_iso.build_tiles(games)]
        self.assertEqual(names, ["Collection (Disc 1)", "Collection (Disc 2)", "Mafia II",
                                 "Mafia II (Add-On Content Disc)"])

    def test_tile_files_carry_the_ids_a_valid_header_hash_and_the_message(self):
        with open(STUB_PATH, "rb") as f:
            stub = f.read()
        tile = netiso_iso.build_tiles([self.game("g (USA).iso", 0xAABBCCDD)])[0]
        files = netiso_iso.tile_files(stub, tile, "PC injoignable é")
        stamped = files["default.xex"]
        offset = netiso_iso.xex_execution_info_offset(stamped)
        self.assertEqual(struct.unpack_from(">I", stamped, offset)[0], tile.media_id)
        self.assertEqual(struct.unpack_from(">I", stamped, offset + 12)[0], 0xAABBCCDD)
        hash_at = struct.unpack_from(">I", stamped, 0x10)[0] + netiso_iso.XEX_HEADER_HASH
        self.assertEqual(stamped[hash_at:hash_at + 20], netiso_iso.xex_header_hash(stamped))
        self.assertNotEqual(stamped[hash_at:hash_at + 20], stub[hash_at:hash_at + 20])
        self.assertEqual(len(stamped), len(stub))
        self.assertEqual(files["netiso.cfg"], "g\r\nPC injoignable é\r\n1\r\n0\r\n".encode("utf-8"))
        fast = netiso_iso.tile_files(stub, tile, "m", netiso_iso.FAST_REQUEST_SIZE)
        self.assertEqual(fast["netiso.cfg"], b"g\r\nm\r\n1\r\n30720\r\n")
        self.assertEqual(netiso_iso.FAST_REQUEST_SIZE % netiso_iso.SECTOR, 0)

    def test_stamp_stub_refuses_a_stub_whose_header_hash_it_cannot_reproduce(self):
        with open(STUB_PATH, "rb") as f:
            broken = bytearray(f.read())
        broken[0x20] ^= 0xFF
        tile = netiso_iso.build_tiles([self.game("g.iso", 1)])[0]
        with self.assertRaises(netiso_iso.IsoError):
            netiso_iso.stamp_stub(bytes(broken), tile)


class ServerTests(TempDirCase):
    def setUp(self):
        super().setUp()
        games = []
        for filename, title_id, disc, discs in (("Alpha (USA).iso", 1, 1, 1),
                                                ("Beta (Disc 1).iso", 2, 1, 2),
                                                ("Beta (Disc 2).iso", 2, 2, 2)):
            path = os.path.join(self.dir.name, filename)
            with open(path, "wb") as f:
                f.write((filename.encode() * 4096)[:3 * netiso_server.SECTOR])
            games.append(netiso_iso.Game(path, netiso_iso.clean_title(path), title_id, 0, disc, discs))
        self.tiles = netiso_iso.build_tiles(games)
        self.server = netiso_server.NetIsoServer(port=0)
        self.server.set_tiles(self.tiles)
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

    def test_lists_one_entry_per_game_then_an_empty_name(self):
        names = [self.request(4, 64, index=i, length=64).rstrip(b"\0") for i in range(3)]
        self.assertEqual(names, [b"Alpha", b"Beta", b""])

    def test_size_is_zero_until_a_game_is_mounted(self):
        self.assertEqual(struct.unpack(">II", self.request(1, 8)), (0, netiso_server.SECTOR))
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(struct.unpack(">II", self.request(1, 8)), (3, netiso_server.SECTOR))

    def test_reads_the_mounted_game_and_reports_what_is_playing(self):
        self.assertEqual(self.server.status(), (None, 0))
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.request(3, 10, offset=0, length=10), b"Alpha (USA")
        self.assertEqual(self.server.status(), (("Alpha", 1), 10))

    def test_a_multi_disc_tile_serves_the_selected_disc(self):
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 1)")
        self.tiles[1].next_disc()
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 2)")
        self.assertEqual(self.server.status()[0], ("Beta", 2))

    def test_the_console_can_ask_for_the_next_or_previous_disc(self):
        events = []
        self.server._on_event = lambda kind, text: events.append((kind, text))
        self.assertEqual(self.mount("Beta#+"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 2)")
        self.assertIn(("disc", ("Beta", 2, 2)), events)
        self.assertEqual(self.mount("Beta"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 2)")
        self.assertEqual(self.mount("Beta#-"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 1)")

    def test_asking_for_another_disc_of_a_single_disc_game_changes_nothing(self):
        self.assertEqual(self.mount("Alpha#+"), 1)
        self.assertEqual(self.request(3, 10, length=10), b"Alpha (USA")

    def test_mount_by_original_iso_file_name(self):
        self.assertEqual(self.mount("Beta (Disc 2).iso"), 1)
        self.assertEqual(self.request(3, 13, length=13), b"Beta (Disc 2)")

    def test_unknown_game_and_disable_unmount(self):
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.mount("Missing"), 0)
        self.assertEqual(struct.unpack(">II", self.request(1, 8))[0], 0)
        self.assertEqual(self.mount("Alpha"), 1)
        self.assertEqual(self.mount(netiso_server.DISABLE_NAME), 0)
        self.assertEqual(struct.unpack(">II", self.request(1, 8))[0], 0)
        self.assertIsNone(self.server.status()[0])


class SyncPlanTests(TempDirCase):
    def tiles(self, *specs):
        return netiso_iso.build_tiles([self.game(*spec) for spec in specs])

    def test_console_copy_wins_over_the_iso(self):
        tiles = self.tiles(("A.iso", 0x111), ("B.iso", 0x222))
        to_send, to_remove = netiso_console.plan_sync(tiles, {(0x111, 1)}, ["A", "B"])
        self.assertEqual([t.name for t in to_send], ["B"])
        self.assertEqual(to_remove, ["A"])

    def test_tile_comes_back_when_the_console_copy_is_deleted(self):
        tiles = self.tiles(("A.iso", 0x111))
        to_send, to_remove = netiso_console.plan_sync(tiles, set(), [])
        self.assertEqual([t.name for t in to_send], ["A"])
        self.assertEqual(to_remove, [])

    def test_multi_disc_tile_stays_while_one_disc_is_missing_from_the_console(self):
        tiles = self.tiles(("G (Disc 1).iso", 0x333, 1, 2), ("G (Disc 2).iso", 0x333, 2, 2))
        to_send, _ = netiso_console.plan_sync(tiles, {(0x333, 1)}, [])
        self.assertEqual([t.name for t in to_send], ["G"])
        to_send, _ = netiso_console.plan_sync(tiles, {(0x333, 1), (0x333, 2)}, [])
        self.assertEqual(to_send, [])

    def test_install_check_uses_what_the_disc_itself_reports(self):
        tiles = self.tiles(("RE (Disc 2).iso", netiso_iso.GENERIC_DISC_TITLE), ("RE (Disc 1).iso", 0x900))
        self.assertEqual(len(tiles), 1)
        installed = {(netiso_iso.GENERIC_DISC_TITLE, 1), (0x900, 1)}
        to_send, _ = netiso_console.plan_sync(tiles, installed, [])
        self.assertEqual(to_send, [])
        to_send, _ = netiso_console.plan_sync(tiles, {(0x900, 1)}, [])
        self.assertEqual([t.name for t in to_send], ["RE"])

    def test_container_install_covers_every_disc(self):
        tiles = self.tiles(("G (Disc 1).iso", 0x333, 1, 2), ("G (Disc 2).iso", 0x333, 2, 2))
        to_send, _ = netiso_console.plan_sync(tiles, {(0x333, None)}, [])
        self.assertEqual(to_send, [])

    def test_tile_of_an_iso_removed_from_the_pc_is_removed(self):
        tiles = self.tiles(("A.iso", 0x111))
        _, to_remove = netiso_console.plan_sync(tiles, set(), ["a", "Gone"])
        self.assertEqual(to_remove, ["Gone"])

    def test_list_line_parsing(self):
        self.assertEqual(netiso_console.parse_list_line(
            "drwxr-xr-x 1 root root 0 Jan 01 2020 Call of Duty - Black Ops III"),
            ("Call of Duty - Black Ops III", True))
        self.assertEqual(netiso_console.parse_list_line(
            "-rw-r--r-- 1 root root 3481600 Jan 01 2020 default.xex"), ("default.xex", False))
        self.assertIsNone(netiso_console.parse_list_line("total 3"))

    def test_xex_game_key(self):
        self.assertEqual(netiso_console.xex_game_key(make_xex(0x4D530A26, 5, 2, 4)), (0x4D530A26, 2))
        self.assertIsNone(netiso_console.xex_game_key(b"not a xex"))


class LaunchIniTests(unittest.TestCase):
    INI = ("; comment\r\n[Paths]\r\nDefault = Hdd:\\Aurora\\Aurora.xex\r\nplugin1 = ignored\r\n"
           "[Plugins]\r\nplugin1 = Hdd:\\X360Remap.xex\r\nplugin2 = \r\nplugin3 =\r\n"
           "[Settings]\r\nnxemini = true\r\n")

    def test_adds_the_plugin_to_the_first_free_slot_and_touches_nothing_else(self):
        path, text = netiso_console.plan_launch_ini(self.INI)
        self.assertEqual(path, "Hdd:\\Apps\\NetISO.xex")
        self.assertEqual(text, self.INI.replace("plugin2 = \r\n", "plugin2 = Hdd:\\Apps\\NetISO.xex\r\n"))

    def test_leaves_a_file_that_already_loads_the_plugin(self):
        ini = self.INI.replace("plugin3 =", "plugin3 = Usb:\\plug\\netiso.XEX")
        self.assertEqual(netiso_console.plan_launch_ini(ini), ("Usb:\\plug\\netiso.XEX", None))

    def test_fails_when_every_slot_is_taken(self):
        ini = self.INI.replace("plugin2 = ", "plugin2 = Hdd:\\a.xex").replace(
            "plugin3 =", "plugin3 = Hdd:\\b.xex")
        with self.assertRaises(netiso_console.ConsoleError):
            netiso_console.plan_launch_ini(ini)

    def test_device_names_map_to_ftp_drives(self):
        self.assertEqual(netiso_console.ini_to_ftp_path("Hdd:\\Apps\\NetISO.xex"),
                         "/Hdd1/Apps/NetISO.xex")
        self.assertEqual(netiso_console.ini_to_ftp_path("usb:\\p\\NetISO.xex"), "/Usb0/p/NetISO.xex")
        with self.assertRaises(netiso_console.ConsoleError):
            netiso_console.ini_to_ftp_path("Mu:\\NetISO.xex")


if __name__ == "__main__":
    unittest.main()
