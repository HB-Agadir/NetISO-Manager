import gc
import importlib.machinery
import importlib.util
import os
import re
import sys
import tempfile
import threading
import time
import unittest

APP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, APP_DIR)

import netiso_i18n
import netiso_iso
from test_core import make_iso, make_xex


class TranslationTests(unittest.TestCase):
    def test_every_text_exists_in_each_language_with_the_same_placeholders(self):
        for key, texts in netiso_i18n._TEXTS.items():
            self.assertEqual(len(texts), len(netiso_i18n.LANGUAGES), key)
            fields = [sorted(re.findall(r"\{(\w+)", text)) for text in texts]
            self.assertTrue(all(text.strip() for text in texts), key)
            self.assertEqual(fields[0], fields[1], key)
            self.assertEqual(fields[0], fields[2], key)

    def test_unknown_language_falls_back_to_english(self):
        self.addCleanup(netiso_i18n.set_language, "en")
        netiso_i18n.set_language("xx")
        self.assertEqual(netiso_i18n.tr("refresh"), "Refresh")
        netiso_i18n.set_language("fr")
        self.assertEqual(netiso_i18n.tr("games_found", count=3), "3 jeu(x) détecté(s)")


class WatchHelperTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_snapshot_lists_isos_with_their_size(self):
        path = os.path.join(self.dir.name, "a.iso")
        with open(path, "wb") as f:
            f.write(b"x" * 10)
        open(os.path.join(self.dir.name, "notes.txt"), "wb").close()
        self.assertEqual(netiso_iso.snapshot([self.dir.name], False), {path: 10})

    def test_a_file_another_program_is_writing_is_reported_as_busy(self):
        import ctypes
        path = os.path.join(self.dir.name, "copying.iso")
        open(path, "wb").close()
        self.assertFalse(netiso_iso.is_being_written(path))
        kernel32 = ctypes.windll.kernel32
        kernel32.CreateFileW.restype = ctypes.c_void_p
        generic_write, open_existing = 0x40000000, 3
        handle = kernel32.CreateFileW(path, generic_write, 0, None, open_existing, 0, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value)
        try:
            self.assertTrue(netiso_iso.is_being_written(path))
        finally:
            kernel32.CloseHandle(ctypes.c_void_p(handle))
        self.assertFalse(netiso_iso.is_being_written(path))


class WindowsStartTests(unittest.TestCase):
    def test_command_reopens_the_app_minimized(self):
        import netiso_winstart
        script = os.path.join("C:", os.sep, "apps", "NetISOManager.pyw")
        command = netiso_winstart.command(script)
        self.assertTrue(command.endswith('"%s" --minimized' % script))
        self.assertIn("python", command.lower())


class WindowTests(unittest.TestCase):
    """Drives the real window with settings kept in a temporary folder."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.isos = os.path.join(self.dir.name, "isos")
        os.mkdir(self.isos)
        make_iso(os.path.join(self.isos, "First Game.iso"), 0, make_xex(0x11111111, 1))
        loader = importlib.machinery.SourceFileLoader(
            "manager", os.path.join(APP_DIR, "NetISOManager.pyw"))
        spec = importlib.util.spec_from_loader("manager", loader)
        self.manager = importlib.util.module_from_spec(spec)
        loader.exec_module(self.manager)
        self.manager.SETTINGS_PATH = os.path.join(self.dir.name, "settings.json")
        self.manager.netiso_iso.CHECKED_PATH = os.path.join(self.dir.name, "checked.json")
        self.manager.save_settings(dict(self.manager.DEFAULTS, folders=[self.isos],
                                        autostart_server=False, welcome_shown=True,
                                        language="fr"))
        self.opened = []
        self.manager.webbrowser.open = self.opened.append
        self.addCleanup(netiso_i18n.set_language, "en")
        self.app = self.manager.App()
        self.addCleanup(self.close_app)
        self.pump(lambda: self.app.scanned is not None)

    def close_app(self):
        """Destroys the window and frees its Tk variables here, in the main thread.

        Left to the garbage collector, they could be freed from a worker thread
        of the next test, where every Tk call stalls for a second.
        """
        self.app.destroy()
        self.app = None
        gc.collect()

    def pump(self, done, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            self.app.update()
            if done():
                return
            time.sleep(0.02)
        self.fail("timed out waiting for the window")

    def rows(self):
        return [self.app.tree.item(i, "values") for i in self.app.tree.get_children()]

    def test_support_link_opens_the_donation_page(self):
        self.app._open_donation_page()
        self.assertEqual(self.opened, ["https://ko-fi.com/x360remap"])

    def test_guide_opens_in_the_app_language_and_falls_back_to_english(self):
        self.app._open_guide()
        self.assertTrue(self.opened[-1].endswith("docs/Guide_fr.html"))
        netiso_i18n.set_language("ar")
        self.app._open_guide()
        self.assertTrue(self.opened[-1].endswith("docs/Guide_en.html"))

    def test_welcome_is_shown_once_and_opens_the_page_only_on_yes(self):
        answers = [False, True]
        asked = []
        self.manager.messagebox.askyesno = lambda title, text: (asked.append(text), answers.pop(0))[1]
        self.app.settings["welcome_shown"] = False
        self.app._welcome()
        self.assertEqual(self.opened, [])
        self.assertTrue(self.manager.load_settings()["welcome_shown"])
        self.app._welcome()
        self.assertEqual(len(self.opened), 1)
        self.assertEqual(len(asked), 2)

    def test_a_fresh_install_starts_in_english(self):
        self.assertEqual(self.manager.DEFAULTS["language"], "en")

    def test_console_view_shows_captures_and_reports_a_refused_login(self):
        from test_nova import colour, make_bmp
        import netiso_nova

        refuse = threading.Event()

        class FakeClient:
            def __init__(self, *args):
                pass

            def capture(self):
                time.sleep(0.05)  # the real console takes seconds per capture
                if refuse.is_set():
                    raise netiso_nova.Unauthorized("401")
                return make_bmp(8, 6, 32, colour)

            def title(self):
                return {"titleid": "0x4D5307D5"}

        self.addCleanup(setattr, self.manager.netiso_nova, "NovaClient", netiso_nova.NovaClient)
        self.manager.netiso_nova.NovaClient = FakeClient
        self.manager.ConsoleView.RETRY_SECONDS = 0.05
        self.app.console_ip.set("192.0.2.1")
        self.app._open_view()
        view = self.app.view
        self.pump(lambda: view.photo is not None)
        self.assertEqual((view.photo.width(), view.photo.height()), (8, 6))
        self.assertIn("4D5307D5", view.status.get())
        refuse.set()
        self.pump(lambda: "mot de passe" in view.status.get())
        self.app._open_view()
        self.assertIs(self.app.view, view, "a second click must reuse the open window")
        view.close()
        self.assertIsNone(self.app.view)

    def test_lists_the_games_of_the_folder(self):
        self.assertEqual([r[0] for r in self.rows()], ["First Game"])
        self.assertEqual(self.rows()[0][1], "À synchroniser")
        self.assertEqual(self.rows()[0][2], "11111111")

    def test_switching_language_translates_the_window_and_is_remembered(self):
        self.app.language.set("English")
        self.app._change_language()
        self.assertEqual(self.rows()[0][1], "Not synced yet")
        self.assertEqual(self.app.push_button.cget("text"), "Sync with Aurora")
        self.assertEqual(self.manager.load_settings()["language"], "en")
        self.app.language.set("العربية")
        self.app._change_language()
        self.assertEqual(self.app.push_button.cget("text"), "المزامنة مع Aurora")

    def test_a_new_iso_is_offered_for_transfer_once_it_has_stopped_changing(self):
        offers = []
        self.app._offer_transfer = lambda added, removed: offers.append((added, removed))
        make_iso(os.path.join(self.isos, "Second Game.iso"), 0, make_xex(0x22222222, 2))
        self.app._watch()
        self.pump(lambda: self.app.last_seen is not None)
        self.assertEqual(offers, [])
        self.app._watch()
        self.pump(lambda: offers)
        self.assertEqual(offers, [(["Second Game"], [])])
        self.assertEqual([r[0] for r in self.rows()], ["First Game", "Second Game"])

    def test_a_removed_iso_is_reported(self):
        offers = []
        self.app._offer_transfer = lambda added, removed: offers.append((added, removed))
        os.remove(os.path.join(self.isos, "First Game.iso"))
        self.app._watch()
        self.pump(lambda: self.app.last_seen is not None)
        self.app._watch()
        self.pump(lambda: offers)
        self.assertEqual(offers, [([], ["First Game"])])

    def test_a_multi_disc_game_shows_one_row_and_switches_disc(self):
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 1).iso"), 0, make_xex(0x33333333, 1, 1, 2))
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 2).iso"), 0, make_xex(0x33333333, 2, 2, 2))
        self.app.scanned = None
        self.app._scan()
        self.pump(lambda: self.app.scanned is not None)
        rows = {r[0]: r for r in self.rows()}
        self.assertEqual(sorted(rows), ["First Game", "Saga"])
        self.assertEqual(rows["Saga"][3], "1 sur 2")
        self.app.tree.selection_set("Saga")
        self.app._next_disc()
        rows = {r[0]: r for r in self.rows()}
        self.assertEqual(rows["Saga"][3], "2 sur 2")
        self.assertTrue(rows["Saga"][5].endswith("Saga (USA) (Disc 2).iso"))
        self.assertEqual(self.manager.load_settings()["active_discs"], {"33333333": 2})

    def test_counts_show_games_isos_and_game_folders(self):
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 1).iso"), 0, make_xex(0x33333333, 1, 1, 2))
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 2).iso"), 0, make_xex(0x33333333, 2, 2, 2))
        folder = os.path.join(self.isos, "Folder Game")
        os.mkdir(folder)
        with open(os.path.join(folder, "default.xex"), "wb") as f:
            f.write(make_xex(0x44444444, 3))
        self.app.scanned = None
        self.app._scan()
        self.pump(lambda: self.app.scanned is not None)
        self.assertEqual(self.app.counts.get(), "3 jeu(x)   ·   3 ISO   ·   1 dossier(s) de jeu")
        self.app.states = {"Saga": "netiso", "First Game": "console", "Folder Game": "netiso"}
        self.app._fill_tree()
        self.assertTrue(self.app.counts.get().endswith("2 en NetISO, 1 sur la console"))

    def test_ungrouping_shows_one_row_per_disc(self):
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 1).iso"), 0, make_xex(0x33333333, 1, 1, 2))
        make_iso(os.path.join(self.isos, "Saga (USA) (Disc 2).iso"), 0, make_xex(0x33333333, 2, 2, 2))
        self.app.group_discs.set(False)
        self.app.scanned = None
        self.app._scan()
        self.pump(lambda: self.app.scanned is not None)
        self.assertEqual([r[0] for r in self.rows()],
                         ["First Game", "Saga (Disc 1)", "Saga (Disc 2)"])
        self.assertFalse(self.manager.load_settings()["group_discs"])

    def test_nothing_is_offered_when_detection_is_switched_off(self):
        offers = []
        self.app._offer_transfer = lambda added, removed: offers.append((added, removed))
        self.app.auto_detect.set(False)
        make_iso(os.path.join(self.isos, "Second Game.iso"), 0, make_xex(0x22222222, 2))
        for _ in range(2):
            self.app._watch()
            end = time.time() + 0.5
            while time.time() < end:
                self.app.update()
        self.assertEqual(offers, [])
        self.assertIsNone(self.app.last_seen)


if __name__ == "__main__":
    unittest.main()
