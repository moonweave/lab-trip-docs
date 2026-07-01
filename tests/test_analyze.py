import tempfile
import unittest
from pathlib import Path

from tripdoc.analyze import (
    TravelerCandidate,
    analyze_document,
    classify_document,
    classify_document_detailed,
    detect_travelers,
    match_traveler,
)


class AnalyzeTests(unittest.TestCase):
    def test_classifies_lodging(self):
        result = classify_document_detailed("Grand Hotel accommodation receipt")
        self.assertEqual(result.category, "lodging")
        self.assertGreater(result.confidence, 0.5)
        self.assertIn("Hotel", result.evidence)

    def test_classifies_by_filename_hint(self):
        self.assertEqual(classify_document("", "kim_hotel_receipt.jpg"), "lodging")

    def test_matches_english_name_in_reverse_order(self):
        travelers = [TravelerCandidate(1, "홍길동", "Gildong Hong", "Hong GD")]
        traveler_id, confidence, reason = match_traveler("Passenger: HONG GILDONG", travelers)
        self.assertEqual(traveler_id, 1)
        self.assertGreater(confidence, 0.9)
        self.assertIn("exact", reason)

    def test_detects_multiple_strong_travelers_without_auto_assignment(self):
        travelers = [
            TravelerCandidate(1, "김철수", "Chulsoo Kim", ""),
            TravelerCandidate(2, "홍길동", "Gildong Hong", ""),
        ]
        text = "Booking for Chulsoo Kim and Gildong Hong"
        traveler_id, confidence, reason = match_traveler(text, travelers)
        self.assertIsNone(traveler_id)
        self.assertGreater(confidence, 0.9)
        self.assertIn("multiple", reason)
        self.assertEqual(len(detect_travelers(text, travelers)), 2)

    def test_uploader_match_is_candidate_only(self):
        travelers = [TravelerCandidate(1, "김철수", "Chulsoo Kim", "")]
        traveler_id, confidence, reason = match_traveler("nameless restaurant receipt", travelers, "김철수")
        self.assertEqual(traveler_id, 1)
        self.assertLess(confidence, 0.9)
        self.assertIn("uploader", reason)

    def test_analyze_txt_document(self):
        travelers = [TravelerCandidate(1, "김철수", "Chulsoo Kim", "")]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hotel.txt"
            path.write_text("Hotel receipt\nGuest: Chulsoo Kim\nTotal KRW 120,000\n2026-07-01", encoding="utf-8")
            result = analyze_document(path, travelers)
        self.assertEqual(result.category, "lodging")
        self.assertEqual(result.matched_traveler_id, 1)
        self.assertEqual(result.amount_hint, "KRW 120,000")
        self.assertEqual(result.date_hint, "2026-07-01")
        self.assertEqual(result.status, "auto_matched")
        self.assertGreater(result.category_confidence, 0)
        self.assertIn("김철수", result.detected_travelers)

    def test_image_receipt_is_needs_review_without_ocr(self):
        travelers = [TravelerCandidate(1, "김철수", "Chulsoo Kim", "")]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "kim_hotel_receipt.jpg"
            path.write_bytes(b"not really an image")
            result = analyze_document(path, travelers, uploaded_by="김철수")
        self.assertEqual(result.category, "lodging")
        self.assertEqual(result.matched_traveler_id, 1)
        self.assertEqual(result.status, "needs_review")
        self.assertIn("OCR", result.notes)


if __name__ == "__main__":
    unittest.main()
