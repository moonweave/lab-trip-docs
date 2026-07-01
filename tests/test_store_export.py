import unittest
from pathlib import Path
import tempfile

from tripdoc.exporters import excel_summary, zip_export
from tripdoc.store import add_document, add_traveler, connect, create_trip, list_documents, list_travelers


class StoreExportTests(unittest.TestCase):
    def test_store_and_export(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            conn = connect(root / "app.db")
            trip_id = create_trip(conn, "Test Trip")
            traveler_id = add_traveler(conn, trip_id, "김철수", "Chulsoo Kim")
            upload_dir = root / "uploads" / f"trip-{trip_id}"
            upload_dir.mkdir(parents=True)
            original = upload_dir / "receipt.txt"
            original.write_text("receipt")
            add_document(
                conn,
                trip_id=trip_id,
                traveler_id=traveler_id,
                uploaded_by="김철수",
                original_filename="receipt.txt",
                stored_path=str(original.relative_to(root)),
                category="meal",
                status="reviewed",
                amount_hint="KRW 10,000",
            )
            travelers = list_travelers(conn, trip_id)
            docs = list_documents(conn, trip_id)
            trip = {"id": trip_id, "name": "Test Trip", "description": ""}
            xlsx = excel_summary(root / "summary.xlsx", trip, travelers, docs)
            package = zip_export(root / "package.zip", trip, travelers, docs, root)
            self.assertTrue(xlsx.exists())
            self.assertTrue(package.exists())


if __name__ == "__main__":
    unittest.main()

