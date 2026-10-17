import json
import os
import sqlite3
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_content as k

FILETIME_2026 = int((1_790_000_000 + 11644473600) * 1e7)


def stfs(magic=b"LIVE", content_type=0x000B0000, title_id=0x4156091D, name="Title Update 8"):
    header = bytearray(0x600)
    header[:4] = magic
    struct.pack_into(">I", header, 0x344, content_type)
    struct.pack_into(">I", header, 0x360, title_id)
    encoded = name.encode("utf-16-be")
    header[0x411:0x411 + len(encoded)] = encoded
    return bytes(header)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, name, data):
        path = os.path.join(self.dir.name, name)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def test_title_update_goes_to_its_content_folder(self):
        path = self.write("tu00000005_00000000", stfs())
        info = k.stfs_info(path)
        self.assertEqual(info, ("title_update", 0x4156091D, 0x000B0000, "Title Update 8"))
        self.assertEqual(k.package_destination(path, info),
                         "/Hdd1/Content/0000000000000000/4156091D/000B0000/tu00000005_00000000")

    def test_dlc(self):
        path = self.write("map_pack", stfs(b"PIRS", 0x00000002, 0x415607E6, "Map Pack"))
        self.assertEqual(k.stfs_info(path)[0], "dlc")
        self.assertTrue(k.package_destination(path, k.stfs_info(path)).endswith(
            "/415607E6/00000002/map_pack"))

    def test_other_files_are_refused(self):
        self.assertIsNone(k.stfs_info(self.write("readme.txt", b"hello" * 400)))
        with self.assertRaises(k.TransferError):
            k.install_package(None, self.write("game.iso", b"\0" * 0x600))


class CrcTests(unittest.TestCase):
    def test_reads_aurora_xcrc_reply(self):
        class Ftp:
            def sendcmd(self, command):
                return "211-Calculating CRC32 hash, please wait...\n 08EA12AE\n211 END"
        self.assertEqual(k.remote_crc32(Ftp(), "/x"), zlib.crc32(b"192.168.1.14"))


class UsageTests(unittest.TestCase):
    def build(self):
        content = sqlite3.connect(":memory:")
        content.executescript("""
            CREATE TABLE MountedDevices (DeviceId, DeviceName, VirtualRoot, MountPoint);
            CREATE TABLE ContentItems (Id, TitleName, TitleId, Directory, ScanPathId, DateAdded);
            INSERT INTO MountedDevices VALUES ('DEV1', 'Hdd1', '', 'Hdd1:');
            INSERT INTO ContentItems VALUES (1, 'Played Long Ago', 1, '\\Games\\Old', 1, 0);
            INSERT INTO ContentItems VALUES (2, 'Never Played', 2, '\\Games\\New', 1, 0);
            INSERT INTO ContentItems VALUES (3, 'Played Today', 3, '\\Games\\Fav', 1, 0);
            INSERT INTO ContentItems VALUES (4, 'NetISO Tile', 4, '\\NetISO\\Tile', 2, 0);
        """)
        settings = sqlite3.connect(":memory:")
        settings.executescript("""
            CREATE TABLE ScanPaths (Id, Path, DeviceId, Depth);
            CREATE TABLE UserRecentGames (Id, DateTime, ContentId, ProfileId);
            INSERT INTO ScanPaths VALUES (1, '\\Games', 'DEV1', 5);
            INSERT INTO ScanPaths VALUES (2, '\\NetISO', 'DEV1', 3);
        """)
        settings.execute("INSERT INTO UserRecentGames VALUES (1, ?, 1, 1)", (FILETIME_2026 - 10 ** 15,))
        settings.execute("INSERT INTO UserRecentGames VALUES (2, ?, 3, 1)", (FILETIME_2026,))
        settings.execute("INSERT INTO UserRecentGames VALUES (3, ?, 3, 2)", (FILETIME_2026 - 10 ** 12,))
        return self.dump(content), self.dump(settings)

    def dump(self, connection):
        handle, path = tempfile.mkstemp(suffix=".db")
        os.close(handle)
        self.addCleanup(os.remove, path)
        target = sqlite3.connect(path)
        connection.commit()              # a pending transaction makes backup() wait forever
        connection.backup(target)
        target.close()
        with open(path, "rb") as f:
            return f.read()

    def test_least_recently_played_first_without_netiso_tiles(self):
        games = k.game_usage(*self.build())
        self.assertEqual([g["title"] for g in games], ["Never Played", "Played Long Ago", "Played Today"])
        self.assertIsNone(games[0]["last_played"])
        self.assertEqual(games[2]["last_played"].year, 2026)
        self.assertEqual(games[0]["drive"], "Hdd1")


class CoverTests(unittest.TestCase):
    def test_official_covers_first(self):
        info = json.dumps([
            {"front": "http://x/front/1", "thumbnail": "http://x/sm/1", "official": False},
            {"front": "http://x/front/2", "thumbnail": "http://x/sm/2", "official": True},
            {"name": "no image"}]).encode()
        self.assertEqual(k.cover_urls(info), [("http://x/front/2", "http://x/sm/2"),
                                              ("http://x/front/1", "http://x/sm/1")])
        self.assertEqual(k.cover_urls(b"not json"), [])


class LaunchTests(unittest.TestCase):
    def test_ftp_folder_to_device_path(self):
        self.assertEqual(k.device_folder("/Hdd1/NetISO/Halo Wars"),
                         "\\Device\\Harddisk0\\Partition1\\NetISO\\Halo Wars")
        with self.assertRaises(k.TransferError):
            k.device_folder("/Usb0/Games/X")


if __name__ == "__main__":
    unittest.main()
