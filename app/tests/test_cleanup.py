import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_console

BS = chr(92)


class GhostEntryTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.content = os.path.join(self.dir.name, "content.db")
        self.settings = os.path.join(self.dir.name, "settings.db")
        db = sqlite3.connect(self.settings)
        db.execute("CREATE TABLE ScanPaths (Id INTEGER PRIMARY KEY, Path TEXT COLLATE NOCASE)")
        db.executemany("INSERT INTO ScanPaths VALUES (?, ?)",
                       [(1, BS + "Games"), (7, BS + "NetISO")])
        db.commit()
        db.close()
        db = sqlite3.connect(self.content)
        db.execute("CREATE TABLE ContentItems (Id INTEGER PRIMARY KEY, Directory TEXT, ScanPathId INTEGER)")
        db.executemany("INSERT INTO ContentItems VALUES (?, ?, ?)", [
            (11, BS + "Games" + BS + "Deleted Game", 1),
            (40, BS + "NetISO" + BS + "Binary Domain", 7),
            (99, BS + "NetISO" + BS + "Binary Domain (USA)", 7),
            (113, BS + "NetISO" + BS + "Wolfenstein (World) (En_Fr", 7),
            (120, BS + "netiso" + BS + "WRC 5", 7),
        ])
        db.commit()
        db.close()

    def ghosts(self, existing, root="/Hdd1/NetISO"):
        return netiso_console.ghost_entries(self.content, self.settings, root, existing)

    def test_finds_entries_of_removed_tiles_only(self):
        ids = [g[0] for g in self.ghosts(["Binary Domain", "wrc 5"])]
        self.assertEqual(ids, [99, 113])

    def test_never_reports_games_outside_the_tiles_folder(self):
        self.assertNotIn(11, [g[0] for g in self.ghosts([])])

    def test_nothing_to_do_when_every_tile_exists_or_the_folder_is_not_scanned(self):
        self.assertEqual(self.ghosts(["Binary Domain", "Binary Domain (USA)",
                                      "Wolfenstein (World) (En_Fr", "WRC 5"]), [])
        self.assertEqual(self.ghosts([], root="/Hdd1/Elsewhere"), [])


class CleanupScriptTests(unittest.TestCase):
    def test_script_deletes_exactly_the_listed_entries_and_refreshes_the_list(self):
        text = netiso_console.cleanup_script(
            [99, 113], "Retire les tuiles", 'Retirer 2 entrée(s) "NetISO" ?', "Terminé").decode("ascii")
        self.assertIn('scriptPermissions = { "sql" }', text)
        self.assertIn('Sql.Execute("DELETE FROM ContentItems WHERE Id IN (99,113)");', text)
        self.assertIn('Sql.Execute("DELETE FROM Config.UserRecentGames WHERE ContentId IN (99,113)");', text)
        self.assertIn("Script.RefreshListOnExit(true);", text)
        self.assertIn("Retirer 2 entree(s) 'NetISO' ?", text)
        self.assertEqual(text.count("DELETE FROM"), 5)
        self.assertNotIn("DROP", text.upper())


if __name__ == "__main__":
    unittest.main()
