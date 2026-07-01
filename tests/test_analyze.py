import unittest
from pathlib import Path
import tempfile

from tripdoc.analyze import TravelerCandidate, analyze_document, classify_document, match_traveler


class AnalyzeTests(unittest.TestCase):
    def test_classifies_lodging(self):
        self.assertEqual(classify_document("Grand Hotel accommodation receipt"), "lodging")

    def test_matches_english_name_in_reverse_order(self):
        travelers = [
            TravelerCandidate(1, "홍길동", "Gildong Hong", "Hong GD"),
        ]
        traveler_id, confidence, _ = match_traveler("Passenger: HONG GILDONG", travelers)
        self.assertEqual(traveler_id, 1)
        self.assertGreater(confidence, 0.9)

    def test_analyze_txt_document(self):
        travelers = [TravelerCandidate(1, "김철수", "Chulsoo Kim", "")]
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "hotel.txt"
            path.write_text("Hotel receipt\nGuest: Chulsoo Kim\nTotal KRW 120,000\n2026-07-01")
            result = analyze_document(path, travelers)
        self.assertEqual(result.category, "lodging")
        self.assertEqual(result.matched_traveler_id, 1)
        self.assertEqual(result.amount_hint, "KRW 120,000")


if __name__ == "__main__":
    unittest.main()

