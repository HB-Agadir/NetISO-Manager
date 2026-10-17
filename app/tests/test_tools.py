import io
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_console
import netiso_tools


class VersionTests(unittest.TestCase):
    def test_reads_tags(self):
        self.assertEqual(netiso_tools.version_tuple("v1.2.0"), (1, 2, 0))
        self.assertEqual(netiso_tools.version_tuple("1.10"), (1, 10))
        self.assertEqual(netiso_tools.version_tuple("beta"), ())

    def reply(self, tag):
        body = io.BytesIO(json.dumps({"tag_name": tag}).encode())
        body.__enter__ = lambda: body
        body.__exit__ = lambda *a: None
        return mock.patch("urllib.request.urlopen", return_value=body)

    def test_only_a_newer_release_is_offered(self):
        with self.reply("v1.4.0"):
            self.assertEqual(netiso_tools.newer_release("1.3.0"), "v1.4.0")
        with self.reply("v1.3.0"):
            self.assertIsNone(netiso_tools.newer_release("1.3.0"))
        with self.reply("v1.2.9"):
            self.assertIsNone(netiso_tools.newer_release("1.3.0"))

    def test_no_network_is_not_an_error(self):
        with mock.patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.assertIsNone(netiso_tools.newer_release("1.3.0"))


class FindTests(unittest.TestCase):
    def test_consoles_with_both_servers_come_first(self):
        open_ports = {("192.168.1.50", 21), ("192.168.1.9", 21), ("192.168.1.9", 9999),
                      ("192.168.1.77", 9999)}
        with mock.patch.object(netiso_tools, "_open",
                               side_effect=lambda h, p, t: (h, p) in open_ports):
            found = netiso_tools.find_consoles("192.168.1.101")
        self.assertEqual(found, ["192.168.1.9", "192.168.1.50"])

    def test_bad_address(self):
        self.assertEqual(netiso_tools.find_consoles("not an address"), [])


class Game:
    def __init__(self, path, is_folder):
        self.path, self.is_folder = path, is_folder


class XeniaTests(unittest.TestCase):
    def test_target_is_the_iso_or_the_folder_default_xex(self):
        self.assertEqual(netiso_tools.xenia_target(Game("D:\\g.iso", False)), "D:\\g.iso")
        self.assertEqual(netiso_tools.xenia_target(Game("D:\\Game", True)),
                         os.path.join("D:\\Game", "default.xex"))

    def test_launch_passes_the_target_as_first_argument(self):
        with tempfile.TemporaryDirectory() as folder:
            iso = os.path.join(folder, "game.iso")
            open(iso, "wb").close()
            exe = os.path.join(folder, "xenia_canary.exe")
            with mock.patch("subprocess.Popen") as popen:
                netiso_tools.launch_xenia(exe, Game(iso, False))
            popen.assert_called_once_with([exe, iso], cwd=folder)
            with self.assertRaises(OSError):
                netiso_tools.launch_xenia(exe, Game(os.path.join(folder, "missing.iso"), False))


class ReportTests(unittest.TestCase):
    def test_scrub_hides_addresses_user_and_home(self):
        home = os.path.expanduser("~")
        user = os.environ.get("USERNAME", "")
        text = netiso_tools.scrub("console 192.168.1.102, file %s\\games\\x.iso" % home)
        self.assertNotIn("192.168.1.102", text)
        self.assertIn("x.x.x.102", text)
        self.assertNotIn(home, text)
        if len(user) > 2:
            self.assertNotIn(user.lower(), text.lower())

    def test_report_has_no_password(self):
        settings = {"ftp_password": "s3cret-ftp", "http_password": "s3cret-web",
                    "folders": ["E:\\Xbox"], "fast_read": True, "group_discs": True}
        report = netiso_tools.diagnostic_report(
            settings, [("ok", "fine"), ("fail", "broken")], [], "line 1\nconsole 10.0.0.5\n", True)
        self.assertNotIn("s3cret", report)
        self.assertNotIn("10.0.0.5", report)
        self.assertIn("[FAIL] broken", report)
        self.assertIn(netiso_tools.APP_VERSION, report)


class ChecksTests(unittest.TestCase):
    INI = ("[Plugins]\r\nplugin1 = Hdd:\\Apps\\NetISO.xex\r\n").encode("latin-1")

    def run_with(self, files, network="Private", reachable=True, aurora=True, pc_ip="192.168.1.101"):
        class Ftp:
            def quit(self):
                pass

        settings = {"console_ip": "192.168.1.100", "ftp_user": "u", "ftp_password": "p",
                    "http_user": "", "http_password": ""}
        with mock.patch.object(netiso_tools.netiso_network, "network_category", return_value=network), \
                mock.patch.object(netiso_tools, "_open", return_value=reachable), \
                mock.patch.object(netiso_tools, "is_aurora", return_value=aurora), \
                mock.patch.object(netiso_console, "connect", return_value=Ftp()), \
                mock.patch.object(netiso_console, "read_file", side_effect=lambda f, p: files.get(p)), \
                mock.patch.object(netiso_console, "is_known_plugin", return_value=True):
            return netiso_tools.run_checks(settings, pc_ip, True)

    def statuses(self, results):
        return [status for status, _text in results]

    def good_files(self):
        return {"/Hdd1/launch.ini": self.INI, "/Hdd1/Apps/NetISO.xex": b"x",
                "/Hdd1/Apps/NetISO.xex.txt": b"192.168.1.101"}

    def test_everything_fine(self):
        results = self.run_with(self.good_files())
        self.assertEqual(set(self.statuses(results)), {"ok"})

    def test_public_network_and_wrong_address_are_problems(self):
        files = self.good_files()
        files["/Hdd1/Apps/NetISO.xex.txt"] = b"192.168.1.100"
        results = self.run_with(files, network="Public")
        self.assertEqual(self.statuses(results).count("fail"), 2)
        self.assertTrue(any("192.168.1.100" in text for _s, text in results))

    def test_stops_when_the_console_does_not_answer(self):
        results = self.run_with(self.good_files(), reachable=False)
        self.assertEqual(self.statuses(results)[-1], "fail")
        self.assertEqual(len(results), 3)

    def test_plugin_not_registered(self):
        files = self.good_files()
        files["/Hdd1/launch.ini"] = b"[Plugins]\r\nplugin1 = \r\n"
        self.assertEqual(self.statuses(self.run_with(files))[-1], "fail")


if __name__ == "__main__":
    unittest.main()


class DiscRoleTests(unittest.TestCase):
    def test_roles_from_names_and_generic_title(self):
        import netiso_iso
        role = netiso_iso.disc_role
        self.assertEqual(role("Watch_Dogs (Disc 1) (Installation Disc).iso", 0x555308B7), "install")
        self.assertEqual(role("Watch_Dogs (Disc 2) (Game Disc).iso", 0x555308B7), "game")
        self.assertEqual(role("Resident Evil 6 (Disc 2) (Voice Over Pack).iso", 0xFFED2000), "extra")
        self.assertEqual(role("Resident Evil 6 (Disc 1) (Game).iso", 0x43430819), "game")
        self.assertEqual(role("Forza Horizon (Disc 2) (Content Disc).iso", 0x4D530910), "extra")
        self.assertEqual(role("Halo Wars.iso", 0x4D5307F4), "game")

    def test_scripts_hold_both_filters_and_the_combined_view(self):
        s, f = netiso_console.aurora_scripts("/Hdd1/NetISO")
        self.assertIn(netiso_console.FILTER_NAME.encode(), f)
        self.assertIn(netiso_console.DISC_FILTER_NAME.encode(), f)
        setup = netiso_console.setup_script()
        self.assertIn(("User.%s;AND;User.%s" % (netiso_console.FILTER_NAME,
                                                netiso_console.DISC_FILTER_NAME)).encode(), setup)


class VersionNumberTests(unittest.TestCase):
    def test_app_and_installer_carry_the_same_version(self):
        """The number shown in the window must be the one of the installer."""
        build = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "build_msi.bat")
        with open(build, encoding="ascii") as f:
            line = next(l for l in f if l.startswith("set VERSION="))
        self.assertEqual(line.strip().split("=", 1)[1], netiso_tools.APP_VERSION)
