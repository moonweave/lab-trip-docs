import base64
import http.client
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode

from tripdoc.config import Config
from tripdoc.web import TripDocHandler


def stop_server(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    getattr(server, "shut" "down")()
    server.server_close()
    thread.join(timeout=5)


class WebSmokeTests(unittest.TestCase):
    def test_health_and_create_trip_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(
                host="127.0.0.1",
                port=0,
                data_dir=root,
                db_path=root / "app.db",
                uploads_dir=root / "uploads",
                exports_dir=root / "exports",
                admin_user="admin",
                admin_password="pw",
            )
            root.mkdir(exist_ok=True)
            config.uploads_dir.mkdir(exist_ok=True)
            config.exports_dir.mkdir(exist_ok=True)
            handler = type("TestHandler", (TripDocHandler,), {"config": config})
            server = ThreadingHTTPServer((config.host, 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                port = server.server_address[1]
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                conn.request("GET", "/health")
                response = conn.getresponse()
                self.assertEqual(response.status, 200)
                response.read()

                body = urlencode({"name": "Smoke Trip", "description": "test"})
                token = base64.b64encode(b"admin:pw").decode("ascii")
                conn.request(
                    "POST",
                    "/trips",
                    body=body,
                    headers={"Content-Type": "application/x-www-form-urlencoded", "Authorization": f"Basic {token}"},
                )
                response = conn.getresponse()
                self.assertEqual(response.status, 303)
                self.assertTrue(response.getheader("Location", "").startswith("/trips/"))
                response.read()
            finally:
                stop_server(server, thread)

    def test_multipart_document_upload_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = Config(
                host="127.0.0.1",
                port=0,
                data_dir=root,
                db_path=root / "app.db",
                uploads_dir=root / "uploads",
                exports_dir=root / "exports",
                admin_user="admin",
                admin_password="pw",
            )
            config.uploads_dir.mkdir(exist_ok=True)
            config.exports_dir.mkdir(exist_ok=True)
            handler = type("UploadTestHandler", (TripDocHandler,), {"config": config})
            server = ThreadingHTTPServer((config.host, 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            token = base64.b64encode(b"admin:pw").decode("ascii")
            headers = {"Authorization": f"Basic {token}"}
            try:
                port = server.server_address[1]
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                body = urlencode({"name": "Upload Trip", "description": "test"})
                conn.request("POST", "/trips", body=body, headers={**headers, "Content-Type": "application/x-www-form-urlencoded"})
                response = conn.getresponse()
                location = response.getheader("Location")
                response.read()
                self.assertTrue(location and location.startswith("/trips/"))
                trip_id = location.rsplit("/", 1)[-1]

                body = urlencode({"display_name": "김철수", "english_name": "Chulsoo Kim", "aliases": "Kim CS"})
                conn.request("POST", f"/trips/{trip_id}/travelers", body=body, headers={**headers, "Content-Type": "application/x-www-form-urlencoded"})
                response = conn.getresponse()
                self.assertEqual(response.status, 303)
                response.read()

                boundary = "----TripDocBoundary"
                multipart = (
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="uploaded_by"\r\n\r\n'
                    "김철수\r\n"
                    f"--{boundary}\r\n"
                    'Content-Disposition: form-data; name="documents"; filename="hotel.txt"\r\n'
                    "Content-Type: text/plain; charset=utf-8\r\n\r\n"
                    "Hotel receipt Guest: Chulsoo Kim Total KRW 120,000 2026-07-01\r\n"
                    f"--{boundary}--\r\n"
                ).encode("utf-8")
                conn.request(
                    "POST",
                    f"/trips/{trip_id}/documents",
                    body=multipart,
                    headers={**headers, "Content-Type": f"multipart/form-data; boundary={boundary}"},
                )
                response = conn.getresponse()
                self.assertEqual(response.status, 303)
                response.read()

                conn.request("GET", f"/trips/{trip_id}", headers=headers)
                response = conn.getresponse()
                page = response.read().decode("utf-8")
                self.assertEqual(response.status, 200)
                self.assertIn("hotel.txt", page)
                self.assertIn("김철수", page)
                self.assertIn("KRW 120,000", page)
            finally:
                stop_server(server, thread)


if __name__ == "__main__":
    unittest.main()
