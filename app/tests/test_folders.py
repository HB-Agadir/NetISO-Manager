import os
import random
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_iso
import netiso_xdvdfs
from test_core import make_xex

SECTOR = netiso_xdvdfs.SECTOR


class DiscReader:
    """Reads a disc image the way the console does: only through block reads."""

    def __init__(self, disc):
        self.disc = disc
        self.base = disc.partition
        head = disc.read(self.base + 32 * SECTOR, SECTOR)
        assert head[:20] == netiso_xdvdfs.MAGIC and head[-20:] == netiso_xdvdfs.MAGIC
        self.root = struct.unpack_from("<II", head, 20)

    def entry(self, table, offset):
        left, right, sector, size, attributes, length = struct.unpack_from("<HHIIBB", table, offset)
        return left * 4, right * 4, sector, size, attributes, table[offset + 14:offset + 14 + length].decode()

    def table(self, sector, size):
        return self.disc.read(self.base + sector * SECTOR, size)

    def lookup(self, sector, size, name):
        """Follows the search tree as the console's file system driver does."""
        table, offset, steps = self.table(sector, size), 0, 0
        while True:
            left, right, child_sector, child_size, attributes, found = self.entry(table, offset)
            steps += 1
            wanted, here = name.upper(), found.upper()
            if wanted == here:
                return child_sector, child_size, attributes, steps
            offset = left if wanted < here else right
            if offset == 0:
                return None

    def walk(self, sector, size, prefix=""):
        """Yields (path, sector, size, attributes) for every entry under a directory."""
        if size == 0:
            return
        table, pending = self.table(sector, size), [0]
        while pending:
            offset = pending.pop()
            left, right, child_sector, child_size, attributes, name = self.entry(table, offset)
            assert offset // SECTOR == (offset + 13 + len(name)) // SECTOR, "entry crosses a sector"
            yield prefix + name, child_sector, child_size, attributes
            if attributes & netiso_xdvdfs.ATTRIBUTE_DIRECTORY:
                yield from self.walk(child_sector, child_size, prefix + name + "/")
            pending += [o for o in (left, right) if o]

    def content(self, sector, size):
        return self.disc.read(self.base + sector * SECTOR, size)


class VirtualDiscTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.folder = os.path.join(self.dir.name, "My Game")
        self.files = {}
        rng = random.Random(7)
        names = ["default.xex", "Empty.bin", "media/intro.bik", "media/Sub/deep.dat", "z_last.pak"]
        names += ["data/file_%03d_with_a_rather_long_name.bin" % i for i in range(150)]
        for name in names:
            path = os.path.join(self.folder, *name.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            data = b"" if name == "Empty.bin" else bytes(rng.getrandbits(8) for _ in range(rng.randint(1, 9000)))
            if name == "default.xex":
                data = make_xex(0x12345678, 0x9ABCDEF0, 1, 1) + data
            with open(path, "wb") as f:
                f.write(data)
            self.files[name] = data
        os.makedirs(os.path.join(self.folder, "EmptyDir"))
        self.disc = netiso_xdvdfs.VirtualDisc(self.folder)
        self.addCleanup(self.disc.close)
        self.reader = DiscReader(self.disc)

    def write_iso(self, cut=0):
        """The virtual disc saved as a real ISO file, optionally missing its last bytes."""
        path = os.path.join(self.dir.name, "game.iso")
        with open(path, "wb") as f:
            offset, step = 0, 64 * 1024 * 1024
            while offset < self.disc.size:
                f.write(self.disc.read(offset, min(step, self.disc.size - offset)))
                offset += step
            f.truncate(self.disc.size - cut)
        return path

    def test_an_iso_extracts_back_to_the_same_files(self):
        iso = self.write_iso()
        netiso_iso.CHECKED_PATH = None
        netiso_iso.check_iso(iso)
        out = os.path.join(self.dir.name, "extracted")
        self.assertEqual(netiso_iso.extract_iso(iso, out), len(self.files))
        for name, data in self.files.items():
            with open(os.path.join(out, *name.split("/")), "rb") as f:
                self.assertEqual(f.read(), data, name)
        self.assertTrue(os.path.isdir(os.path.join(out, "EmptyDir")))

    def test_a_truncated_iso_is_reported(self):
        iso = self.write_iso(cut=SECTOR * 4)
        with self.assertRaises(netiso_iso.IsoError):
            netiso_iso.check_iso(iso)

    def test_every_file_is_listed_with_its_exact_content(self):
        seen = {}
        for path, sector, size, attributes in self.reader.walk(*self.reader.root):
            if not attributes & netiso_xdvdfs.ATTRIBUTE_DIRECTORY:
                seen[path] = self.reader.content(sector, size)
        self.assertEqual(seen, self.files)

    def test_every_name_is_found_through_the_search_tree_whatever_its_case(self):
        data_sector, data_size, attributes, _ = self.reader.lookup(*self.reader.root, "DATA")
        self.assertTrue(attributes & netiso_xdvdfs.ATTRIBUTE_DIRECTORY)
        deepest = 0
        for i in range(150):
            found = self.reader.lookup(data_sector, data_size, "FILE_%03d_WITH_A_RATHER_LONG_NAME.BIN" % i)
            self.assertIsNotNone(found, i)
            deepest = max(deepest, found[3])
        self.assertLessEqual(deepest, 9, "the tree should stay shallow")
        self.assertIsNone(self.reader.lookup(data_sector, data_size, "missing.bin"))
        self.assertIsNotNone(self.reader.lookup(*self.reader.root, "Default.XEX"))

    def test_directory_tables_span_sectors_without_splitting_an_entry(self):
        _sector, size, _attributes, _ = self.reader.lookup(*self.reader.root, "data")
        self.assertGreater(size, SECTOR)
        self.assertEqual(size % SECTOR, 0)
        list(self.reader.walk(*self.reader.root))  # asserts on a split entry

    def test_empty_file_and_empty_folder_take_no_space(self):
        self.assertEqual(self.reader.lookup(*self.reader.root, "Empty.bin")[:2], (0, 0))
        self.assertEqual(self.reader.lookup(*self.reader.root, "EmptyDir")[:2], (0, 0))

    def test_layout_is_the_one_the_plugin_looks_for(self):
        self.assertEqual(self.disc.partition, netiso_xdvdfs.XGD2_OFFSET)
        self.assertEqual(self.disc.size % SECTOR, 0)
        self.assertEqual(self.disc.read(0, 4096), bytes(4096))
        self.assertEqual(self.disc.descriptor_offset, netiso_xdvdfs.XGD2_OFFSET + 32 * SECTOR)

    def test_reads_across_file_boundaries_and_past_the_end_are_consistent(self):
        whole = self.disc.read(self.disc.partition, self.disc.size - self.disc.partition)
        rng = random.Random(3)
        for _ in range(200):
            start = rng.randrange(len(whole))
            length = rng.randint(1, 20000)
            expected = whole[start:start + length].ljust(length, b"\0")
            self.assertEqual(self.disc.read(self.disc.partition + start, length), expected)

    def test_a_very_large_game_uses_the_bigger_disc_layout(self):
        with open(os.path.join(self.folder, "huge.pak"), "wb") as f:
            f.write(b"x" * 5000 + b"end")
        limit = netiso_xdvdfs.XGD2_MAX_SECTORS
        self.addCleanup(setattr, netiso_xdvdfs, "XGD2_MAX_SECTORS", limit)
        netiso_xdvdfs.XGD2_MAX_SECTORS = 50  # stand-in for a game too big for the small layout
        disc = netiso_xdvdfs.VirtualDisc(self.folder)
        self.addCleanup(disc.close)
        self.assertEqual(disc.partition, netiso_xdvdfs.XGD3_OFFSET)
        sector, size, _a, _s = DiscReader(disc).lookup(*DiscReader(disc).root, "huge.pak")
        self.assertEqual(disc.read(disc.partition + sector * SECTOR + size - 3, 3), b"end")

    def test_names_the_disc_format_cannot_hold_are_refused(self):
        open(os.path.join(self.folder, "café.bin"), "wb").close()
        with self.assertRaises(netiso_xdvdfs.DiscError):
            netiso_xdvdfs.VirtualDisc(self.folder)


class FolderGameTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = os.path.join(self.dir.name, "games")
        game = os.path.join(self.root, "sub", "Cool Game (USA) (Disc 1)")
        os.makedirs(os.path.join(game, "media"))
        with open(os.path.join(game, "Default.xex"), "wb") as f:
            f.write(make_xex(0x4D530001, 0x77, 1, 2))
        with open(os.path.join(game, "media", "default.xex"), "wb") as f:
            f.write(b"not a game of its own")
        with open(os.path.join(game, "media", "a.iso"), "wb") as f:
            f.write(b"inner file that must not be listed")
        self.game = game

    def test_a_folder_with_a_default_xex_is_one_game_and_is_not_searched_further(self):
        self.assertEqual(netiso_iso.find_isos([self.root], True), [self.game])
        self.assertEqual(netiso_iso.find_isos([self.root], False), [])

    def test_scan_reads_its_ids_and_serves_it_as_a_disc(self):
        tiles, errors = netiso_iso.scan([self.root], True)
        self.assertEqual(errors, [])
        self.assertEqual([t.name for t in tiles], ["Cool Game (Disc 1)"])
        game = tiles[0].game()
        self.assertTrue(game.is_folder)
        self.assertEqual((game.title_id, game.media_id, game.disc, game.discs), (0x4D530001, 0x77, 1, 2))
        self.assertEqual(game.size, 0x40 + 21 + 34)
        disc = game.open()
        self.addCleanup(disc.close)
        found = DiscReader(disc).lookup(*DiscReader(disc).root, "default.xex")
        self.assertEqual(DiscReader(disc).content(found[0], found[1])[:4], b"XEX2")

    def test_snapshot_changes_while_a_folder_is_still_being_copied(self):
        before = netiso_iso.snapshot([self.root], True)
        with open(os.path.join(self.game, "media", "more.pak"), "wb") as f:
            f.write(b"x" * 100)
        after = netiso_iso.snapshot([self.root], True)
        self.assertNotEqual(before, after)
        self.assertFalse(netiso_iso.is_being_written(self.game))

    def test_multi_disc_folders_named_without_brackets_share_a_tile(self):
        games = []
        for disc in (1, 2):
            folder = os.path.join(self.root, "Batman - Arkham City Disc %d" % disc)
            os.makedirs(folder)
            with open(os.path.join(folder, "default.xex"), "wb") as f:
                f.write(make_xex(0x57520802, 5, disc, 2))
            games.append(folder)
        tiles, _ = netiso_iso.scan([self.root], False)
        self.assertEqual([t.name for t in tiles], ["Batman - Arkham City"])
        self.assertEqual([g.disc for g in tiles[0].games], [1, 2])


if __name__ == "__main__":
    unittest.main()
