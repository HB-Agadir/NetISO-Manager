import http.server
import json
import os
import struct
import sys
import threading
import unittest
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import netiso_nova


def make_bmp(width, height, bits, pixel, top_down=False):
    """BMP whose pixel (x, y from the top) has the colour pixel(x, y) -> (r, g, b)."""
    step = bits // 8
    row_size = (width * step + 3) & ~3
    rows = []
    for y in range(height):
        row = bytearray(row_size)
        for x in range(width):
            r, g, b = pixel(x, y)
            row[x * step:x * step + 3] = bytes((b, g, r))
        rows.append(bytes(row))
    if not top_down:
        rows.reverse()
    header = b"BM" + struct.pack("<IHHI", 54 + row_size * height, 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, width, -height if top_down else height, 1, bits, 0,
                       row_size * height, 0, 0, 0, 0)
    return header + info + b"".join(rows)


def colour(x, y):
    return (x * 10) % 256, (y * 20) % 256, (x + y) % 256


def ppm_pixel(ppm, width, x, y):
    start = ppm.index(b"\n") + 1 + (y * width + x) * 3
    return tuple(ppm[start:start + 3])


class BmpTests(unittest.TestCase):
    def test_converts_the_formats_the_console_can_send(self):
        for bits in (24, 32):
            for top_down in (False, True):
                width, height, ppm = netiso_nova.bmp_to_ppm(make_bmp(7, 5, bits, colour, top_down))
                self.assertEqual((width, height), (7, 5))
                self.assertTrue(ppm.startswith(b"P6 7 5 255\n"))
                for x, y in ((0, 0), (6, 0), (3, 2), (0, 4), (6, 4)):
                    self.assertEqual(ppm_pixel(ppm, 7, x, y), colour(x, y), (bits, top_down, x, y))

    def test_shrinking_keeps_one_pixel_in_n_from_the_top_left(self):
        width, height, ppm = netiso_nova.bmp_to_ppm(make_bmp(9, 6, 32, colour), shrink=2)
        self.assertEqual((width, height), (5, 3))
        self.assertEqual(ppm_pixel(ppm, 5, 0, 0), colour(0, 0))
        self.assertEqual(ppm_pixel(ppm, 5, 4, 2), colour(8, 4))

    def test_rejects_what_is_not_a_usable_bmp(self):
        for bad in (b"", b"PNG" * 30, make_bmp(4, 4, 32, colour)[:80]):
            with self.assertRaises(netiso_nova.NovaError):
                netiso_nova.bmp_to_ppm(bad)


class FakeNova(http.server.BaseHTTPRequestHandler):
    """Stands in for Aurora's web server: same routes, same replies."""
    state = None

    def log_message(self, *args):
        pass

    def _reply(self, code, body=b"", kind="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("Authorization") == "Bearer " + self.state["token"]

    def do_POST(self):
        form = urllib.parse.parse_qs(self.rfile.read(int(self.headers["Content-Length"])).decode())
        self.state["logins"] += 1
        if self.path == "/authenticate" and form == {"username": ["user"], "password": ["secret"]}:
            return self._reply(200, json.dumps({"token": self.state["token"]}).encode())
        self._reply(401)

    def do_GET(self):
        if not self._authorized():
            return self._reply(401)
        if self.path == "/title":
            return self._reply(200, b'{"path": "Aurora.xex", "titleid": "0x00000000"}')
        if self.path == "/screencapture/meta":
            return self._reply(200, b'{"filename": "shot 1", "info": {"width": 4, "height": 4}}')
        if self.path == "/image/screencapture?uuid=shot%201":
            return self._reply(200, self.state["bmp"], "image/bmp")
        self._reply(404)

    def do_DELETE(self):
        self.state["deleted"].append(self.path)
        self._reply(204 if self._authorized() else 401)


class ClientTests(unittest.TestCase):
    def setUp(self):
        FakeNova.state = {"token": "t1", "logins": 0, "deleted": [], "bmp": make_bmp(4, 4, 32, colour)}
        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeNova)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.port = self.server.server_address[1]

    def client(self, password="secret"):
        return netiso_nova.NovaClient("127.0.0.1", "user", password, self.port)

    def test_signs_in_once_then_reads_the_running_title(self):
        client = self.client()
        self.assertEqual(client.title()["path"], "Aurora.xex")
        client.title()
        self.assertEqual(FakeNova.state["logins"], 1)

    def test_capture_returns_the_image_and_removes_it_from_the_console(self):
        self.assertEqual(self.client().capture(), FakeNova.state["bmp"])
        self.assertEqual(FakeNova.state["deleted"], ["/screencapture?uuid=shot%201"])

    def test_signs_in_again_when_the_session_has_expired(self):
        client = self.client()
        client.title()
        FakeNova.state["token"] = "t2"
        self.assertEqual(client.title()["path"], "Aurora.xex")
        self.assertEqual(FakeNova.state["logins"], 2)

    def test_a_wrong_password_is_reported_as_such(self):
        with self.assertRaises(netiso_nova.Unauthorized):
            self.client("wrong").title()

    def test_an_unreachable_console_is_an_error_not_a_crash(self):
        self.server.shutdown()
        self.server.server_close()
        with self.assertRaises(netiso_nova.NovaError):
            netiso_nova.NovaClient("127.0.0.1", "user", "secret", self.port).title()


if __name__ == "__main__":
    unittest.main()
