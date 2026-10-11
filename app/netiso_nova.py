"""Client for the web server built into Aurora (its Nova module, port 9999 by default).

Used to show what is on the console's screen while it is being set up from
the PC. The server takes a screenshot on request and serves it as a BMP file.
"""

import json
import struct
import urllib.error
import urllib.parse
import urllib.request

PORT = 9999
TIMEOUT = 30


class NovaError(Exception):
    pass


class Unauthorized(NovaError):
    pass


def bmp_to_ppm(data, shrink=1):
    """Converts an uncompressed 24 or 32-bit BMP to a binary PPM, keeping one pixel in `shrink`.

    Returns (width, height, ppm bytes). Tk reads PPM natively, which avoids
    depending on an imaging library.
    """
    if data[:2] != b"BM" or len(data) < 54:
        raise NovaError("not a BMP image")
    pixels_at = struct.unpack_from("<I", data, 10)[0]
    width, height, _planes, bits, compression = struct.unpack_from("<iiHHI", data, 18)
    if bits not in (24, 32) or compression not in (0, 3) or width <= 0 or height == 0:
        raise NovaError("unsupported BMP format")
    step = bits // 8
    row_size = (width * step + 3) & ~3
    rows = abs(height)
    if pixels_at + row_size * rows > len(data):
        raise NovaError("truncated BMP image")
    out_width = (width + shrink - 1) // shrink
    order = range(rows - 1, -1, -shrink) if height > 0 else range(0, rows, shrink)  # stored bottom-up
    out = bytearray()
    for row in order:
        start = pixels_at + row * row_size
        line = data[start:start + width * step]
        rgb = bytearray(out_width * 3)
        rgb[0::3] = line[2::step * shrink]  # stored blue, green, red
        rgb[1::3] = line[1::step * shrink]
        rgb[2::3] = line[0::step * shrink]
        out += rgb
    out_height = len(out) // (out_width * 3)
    return out_width, out_height, b"P6 %d %d 255\n" % (out_width, out_height) + bytes(out)


class NovaClient:
    def __init__(self, host, user, password, port=PORT):
        self._base = "http://%s:%d" % (host, port)
        self._user = user
        self._password = password
        self._token = None

    def _request(self, path, data=None, method=None):
        request = urllib.request.Request(self._base + path, data=data, method=method)
        if self._token:
            request.add_header("Authorization", "Bearer " + self._token)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            error.close()
            if error.code == 401:
                raise Unauthorized("401")
            raise NovaError("HTTP %d" % error.code)
        except (OSError, ValueError) as error:
            raise NovaError(str(error))

    def login(self):
        self._token = None
        body = self._request("/authenticate", urllib.parse.urlencode(
            {"username": self._user, "password": self._password}).encode())
        try:
            self._token = json.loads(body)["token"]
        except (ValueError, KeyError, TypeError):
            raise NovaError("unexpected login reply")

    def _get(self, path, method=None):
        """Runs a request, signing in first or again when the session is missing or expired."""
        if self._token is None:
            self.login()
        try:
            return self._request(path, method=method)
        except Unauthorized:
            self.login()
            return self._request(path, method=method)

    def title(self):
        """Returns what the console is running: {"path", "titleid", "resolution", ...}."""
        return json.loads(self._get("/title"))

    def temperature(self):
        return json.loads(self._get("/temperature"))

    def capture(self):
        """Takes a screenshot and returns it as BMP bytes.

        Aurora keeps every screenshot on the console's disk, so the capture is
        deleted there once downloaded.
        """
        meta = json.loads(self._get("/screencapture/meta"))
        uuid = urllib.parse.quote(str(meta["filename"]))
        try:
            return self._get("/image/screencapture?uuid=" + uuid)
        finally:
            try:
                self._get("/screencapture?uuid=" + uuid, method="DELETE")
            except NovaError:
                pass
