from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import base64
import cgi
import html
import mimetypes
import re
import uuid
from urllib.parse import parse_qs, urlparse

from .analyze import TravelerCandidate, analyze_document
from .config import Config
from .exporters import excel_summary, zip_export
from .roster import load_roster
from .store import (
    add_document,
    add_traveler,
    clear_travelers,
    connect,
    create_trip,
    get_document,
    get_trip,
    list_documents,
    list_travelers,
    list_trips,
    update_document_review,
)

CATEGORIES = [
    "airfare",
    "boarding_pass",
    "lodging",
    "conference_registration",
    "badge",
    "meal",
    "transport",
    "misc",
]
STATUSES = ["auto_matched", "needs_review", "reviewed", "excluded"]


@dataclass
class UploadedFile:
    filename: str
    content: bytes
    mime_type: str


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def slug_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\-가-힣 ]+", "_", name, flags=re.UNICODE).strip()
    return name or "upload.bin"


def layout(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <style>
    body {{ margin: 0; font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f6f7f9; color: #17202a; }}
    header {{ background: #111827; color: white; padding: 14px 24px; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 24px; }}
    a {{ color: #1f6feb; text-decoration: none; }}
    .panel {{ background: white; border: 1px solid #d8dee8; border-radius: 8px; padding: 18px; margin-bottom: 18px; }}
    .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; }}
    label {{ display: block; font-weight: 700; margin: 10px 0 5px; }}
    input, textarea, select {{ width: 100%; padding: 9px 10px; border: 1px solid #d8dee8; border-radius: 6px; background: white; box-sizing: border-box; }}
    button, .button {{ display: inline-block; border: 0; border-radius: 6px; background: #1f6feb; color: white; padding: 9px 12px; font-weight: 700; cursor: pointer; margin-top: 10px; }}
    .button.secondary {{ background: #374151; }}
    table {{ width: 100%; border-collapse: collapse; background: white; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #d8dee8; text-align: left; padding: 9px; vertical-align: top; }}
    th {{ background: #f1f4f8; }}
    .muted {{ color: #687385; }}
    .pill {{ display: inline-block; padding: 2px 7px; border-radius: 999px; background: #e8f0fe; color: #174ea6; font-size: 12px; font-weight: 700; }}
    .needs_review {{ background: #fff4ce; color: #9a6700; }}
    .rowform {{ display: grid; grid-template-columns: 1fr 1fr 1fr 1.5fr auto; gap: 8px; align-items: end; }}
    @media (max-width: 800px) {{ main {{ padding: 14px; }} .rowform {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <header><strong>Lab Trip Docs</strong></header>
  <main>{body}</main>
</body>
</html>"""


class TripDocHandler(BaseHTTPRequestHandler):
    config: Config

    def log_message(self, format: str, *args: object) -> None:
        return

    @property
    def conn(self):
        return connect(self.config.db_path)

    def authenticated(self) -> bool:
        if self.path == "/health":
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
        except Exception:
            return False
        username, _, password = decoded.partition(":")
        return username == self.config.admin_user and password == self.config.admin_password

    def require_auth(self) -> bool:
        if self.authenticated():
            return True
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Lab Trip Docs"')
        self.end_headers()
        return False

    def do_GET(self) -> None:
        if not self.require_auth():
            return
        path = urlparse(self.path).path
        if path == "/health":
            self.send_text("ok")
        elif path == "/":
            self.index()
        elif match := re.fullmatch(r"/trips/(\d+)", path):
            self.trip_detail(int(match.group(1)))
        elif match := re.fullmatch(r"/documents/(\d+)/file", path):
            self.document_file(int(match.group(1)))
        elif match := re.fullmatch(r"/trips/(\d+)/export.xlsx", path):
            self.export_xlsx(int(match.group(1)))
        elif match := re.fullmatch(r"/trips/(\d+)/export.zip", path):
            self.export_zip(int(match.group(1)))
        else:
            self.not_found()

    def do_POST(self) -> None:
        if not self.require_auth():
            return
        path = urlparse(self.path).path
        if path == "/trips":
            self.create_trip_route()
        elif match := re.fullmatch(r"/trips/(\d+)/roster", path):
            self.upload_roster(int(match.group(1)))
        elif match := re.fullmatch(r"/trips/(\d+)/documents", path):
            self.upload_documents(int(match.group(1)))
        elif match := re.fullmatch(r"/documents/(\d+)/review", path):
            self.review_document(int(match.group(1)))
        else:
            self.not_found()

    def parse_form(self) -> tuple[dict[str, str], dict[str, list[UploadedFile]]]:
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", "0"))
        fields: dict[str, str] = {}
        files: dict[str, list[UploadedFile]] = {}
        if content_type.startswith("multipart/form-data"):
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type, "CONTENT_LENGTH": str(content_length)},
            )
            for key in form.keys():
                items = form[key]
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    if item.filename:
                        files.setdefault(key, []).append(UploadedFile(item.filename, item.file.read(), item.type or ""))
                    else:
                        fields[key] = item.value
        else:
            raw = self.rfile.read(content_length).decode("utf-8")
            fields = {key: values[-1] for key, values in parse_qs(raw).items()}
        return fields, files

    def index(self) -> None:
        with self.conn as conn:
            trips = list_trips(conn)
        rows = "".join(
            f"<tr><td><a href='/trips/{t['id']}'>{esc(t['name'])}</a></td><td>{t['traveler_count']}</td><td>{t['document_count']}</td><td class='muted'>{esc(t['created_at'])}</td></tr>"
            for t in trips
        ) or "<tr><td colspan='4' class='muted'>아직 출장 건이 없습니다.</td></tr>"
        body = f"""
        <h1>출장 서류 자동취합</h1>
        <section class="panel">
          <h2>새 출장 건 만들기</h2>
          <form method="post" action="/trips">
            <label>출장 건 이름</label><input name="name" placeholder="예: 2026 E-MRS 출장" required>
            <label>설명</label><textarea name="description" rows="2"></textarea>
            <button type="submit">출장 건 생성</button>
          </form>
        </section>
        <section class="panel"><h2>출장 건 목록</h2><table><thead><tr><th>이름</th><th>출장자</th><th>문서</th><th>생성일</th></tr></thead><tbody>{rows}</tbody></table></section>
        """
        self.send_html(layout("Lab Trip Docs", body))

    def trip_detail(self, trip_id: int) -> None:
        with self.conn as conn:
            trip = get_trip(conn, trip_id)
            if not trip:
                self.not_found(); return
            travelers = list_travelers(conn, trip_id)
            documents = list_documents(conn, trip_id)
        traveler_options_base = '<option value="">확인 필요/미지정</option>' + "".join(
            f'<option value="{t["id"]}">{esc(t["display_name"])}</option>' for t in travelers
        )
        traveler_rows = "".join(
            f"<tr><td>{esc(t['display_name'])}</td><td>{esc(t['english_name'])}</td><td>{esc(t['aliases'])}</td><td>{esc(t['affiliation'])}</td></tr>" for t in travelers
        ) or "<tr><td colspan='4' class='muted'>명단을 업로드하세요.</td></tr>"
        doc_rows = ""
        for doc in documents:
            traveler_options = traveler_options_base
            if doc["traveler_id"]:
                traveler_options = traveler_options.replace(f'value="{doc["traveler_id"]}"', f'value="{doc["traveler_id"]}" selected', 1)
            category_options = "".join(f'<option value="{c}" {"selected" if c == doc["category"] else ""}>{c}</option>' for c in CATEGORIES)
            status_options = "".join(f'<option value="{s}" {"selected" if s == doc["status"] else ""}>{s}</option>' for s in STATUSES)
            status_class = "needs_review" if doc["status"] == "needs_review" else ""
            doc_rows += f"""<tr>
              <td><a href="/documents/{doc['id']}/file">{esc(doc['original_filename'])}</a><br><span class="muted">by {esc(doc['uploaded_by'])}</span></td>
              <td><span class="pill {status_class}">{esc(doc['status'])}</span><br><span class="muted">{doc['match_confidence']:.2f}</span></td>
              <td>{esc(doc['date_hint'])}<br>{esc(doc['amount_hint'])}</td>
              <td><form class="rowform" method="post" action="/documents/{doc['id']}/review"><select name="traveler_id">{traveler_options}</select><select name="category">{category_options}</select><select name="status">{status_options}</select><input name="notes" value="{esc(doc['notes'])}"><button type="submit">저장</button></form></td>
            </tr>"""
        doc_rows = doc_rows or "<tr><td colspan='4' class='muted'>아직 업로드된 문서가 없습니다.</td></tr>"
        body = f"""
        <p><a href="/">← 출장 건 목록</a></p><h1>{esc(trip['name'])}</h1><p class="muted">{esc(trip['description'])}</p>
        <section class="grid">
          <div class="panel"><h2>출장자 명단 업로드</h2><form method="post" action="/trips/{trip_id}/roster" enctype="multipart/form-data"><label>CSV 또는 XLSX</label><input type="file" name="roster" accept=".csv,.xlsx" required><button type="submit">명단 반영</button></form></div>
          <div class="panel"><h2>문서 업로드</h2><form method="post" action="/trips/{trip_id}/documents" enctype="multipart/form-data"><label>업로드한 사람</label><input name="uploaded_by" placeholder="예: 김철수"><label>PDF/JPG/PNG/TXT</label><input type="file" name="documents" multiple required><button type="submit">업로드 및 분석</button></form></div>
        </section>
        <section class="panel"><h2>출력</h2><a class="button" href="/trips/{trip_id}/export.xlsx">Excel 요약 다운로드</a> <a class="button secondary" href="/trips/{trip_id}/export.zip">ZIP 패키지 다운로드</a></section>
        <section class="panel"><h2>출장자 명단</h2><table><thead><tr><th>이름</th><th>영문명</th><th>별칭</th><th>소속</th></tr></thead><tbody>{traveler_rows}</tbody></table></section>
        <section class="panel"><h2>문서 검토</h2><table><thead><tr><th>파일</th><th>상태</th><th>힌트</th><th>검토</th></tr></thead><tbody>{doc_rows}</tbody></table></section>
        """
        self.send_html(layout(trip["name"], body))

    def create_trip_route(self) -> None:
        fields, _ = self.parse_form()
        name = fields.get("name", "").strip()
        if not name:
            self.redirect("/"); return
        with self.conn as conn:
            trip_id = create_trip(conn, name, fields.get("description", ""))
        self.redirect(f"/trips/{trip_id}")

    def upload_roster(self, trip_id: int) -> None:
        _, files = self.parse_form()
        uploads = files.get("roster", [])
        if not uploads:
            self.redirect(f"/trips/{trip_id}"); return
        temp_dir = self.config.data_dir / "tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_path = temp_dir / f"{uuid.uuid4().hex}_{slug_filename(uploads[0].filename)}"
        temp_path.write_bytes(uploads[0].content)
        records = load_roster(temp_path)
        with self.conn as conn:
            clear_travelers(conn, trip_id)
            for record in records:
                add_traveler(conn, trip_id, **record)
        temp_path.unlink(missing_ok=True)
        self.redirect(f"/trips/{trip_id}")

    def upload_documents(self, trip_id: int) -> None:
        fields, files = self.parse_form()
        uploaded_by = fields.get("uploaded_by", "").strip()
        upload_dir = self.config.uploads_dir / f"trip-{trip_id}"
        upload_dir.mkdir(parents=True, exist_ok=True)
        with self.conn as conn:
            travelers = [TravelerCandidate(int(row["id"]), row["display_name"], row["english_name"], row["aliases"]) for row in list_travelers(conn, trip_id)]
            for upload in files.get("documents", []):
                clean_name = slug_filename(upload.filename)
                stored_path = upload_dir / f"{uuid.uuid4().hex}_{clean_name}"
                stored_path.write_bytes(upload.content)
                result = analyze_document(stored_path, travelers, uploaded_by)
                add_document(
                    conn,
                    trip_id=trip_id,
                    traveler_id=result.matched_traveler_id,
                    uploaded_by=uploaded_by,
                    original_filename=clean_name,
                    stored_path=str(stored_path.relative_to(self.config.data_dir)),
                    mime_type=upload.mime_type,
                    category=result.category,
                    status=result.status,
                    extracted_text=result.extracted_text,
                    date_hint=result.date_hint,
                    amount_hint=result.amount_hint,
                    match_confidence=result.match_confidence,
                    notes=result.notes,
                )
        self.redirect(f"/trips/{trip_id}")

    def review_document(self, document_id: int) -> None:
        fields, _ = self.parse_form()
        traveler_raw = fields.get("traveler_id", "").strip()
        traveler_id = int(traveler_raw) if traveler_raw else None
        with self.conn as conn:
            doc = get_document(conn, document_id)
            if not doc:
                self.not_found(); return
            update_document_review(conn, document_id, traveler_id, fields.get("category", "misc"), fields.get("status", "needs_review"), fields.get("notes", ""))
        self.redirect(f"/trips/{doc['trip_id']}")

    def document_file(self, document_id: int) -> None:
        with self.conn as conn:
            doc = get_document(conn, document_id)
        if not doc:
            self.not_found(); return
        path = self.config.data_dir / doc["stored_path"]
        if not path.exists():
            self.not_found(); return
        mime = doc["mime_type"] or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_bytes(path.read_bytes(), mime, doc["original_filename"])

    def export_xlsx(self, trip_id: int) -> None:
        with self.conn as conn:
            trip = get_trip(conn, trip_id)
            if not trip:
                self.not_found(); return
            travelers = list_travelers(conn, trip_id)
            docs = list_documents(conn, trip_id)
        path = self.config.exports_dir / f"trip-{trip_id}" / "summary.xlsx"
        excel_summary(path, trip, travelers, docs)
        self.send_bytes(path.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", path.name)

    def export_zip(self, trip_id: int) -> None:
        with self.conn as conn:
            trip = get_trip(conn, trip_id)
            if not trip:
                self.not_found(); return
            travelers = list_travelers(conn, trip_id)
            docs = list_documents(conn, trip_id)
        path = self.config.exports_dir / f"trip-{trip_id}" / "trip-package.zip"
        zip_export(path, trip, travelers, docs, self.config.data_dir)
        self.send_bytes(path.read_bytes(), "application/zip", path.name)

    def send_html(self, content: str) -> None:
        self.send_bytes(content.encode("utf-8"), "text/html; charset=utf-8")

    def send_text(self, content: str) -> None:
        self.send_bytes(content.encode("utf-8"), "text/plain; charset=utf-8")

    def send_bytes(self, content: bytes, content_type: str, filename: str | None = None) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{slug_filename(filename)}"')
        self.end_headers()
        self.wfile.write(content)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", location)
        self.end_headers()

    def not_found(self) -> None:
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()
        self.wfile.write(b"not found")


def run(config: Config) -> None:
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.uploads_dir.mkdir(parents=True, exist_ok=True)
    config.exports_dir.mkdir(parents=True, exist_ok=True)
    with connect(config.db_path):
        pass
    handler = type("ConfiguredTripDocHandler", (TripDocHandler,), {"config": config})
    server = ThreadingHTTPServer((config.host, config.port), handler)
    print(f"Lab Trip Docs running at http://{config.host}:{config.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

