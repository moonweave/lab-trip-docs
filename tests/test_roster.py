import unittest
from pathlib import Path
import tempfile

from tripdoc.roster import load_roster


class RosterTests(unittest.TestCase):
    def test_load_csv_roster(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "roster.csv"
            path.write_text("이름,영문명,별칭,소속\n김철수,Chulsoo Kim,Kim CS,Lab A\n", encoding="utf-8")
            records = load_roster(path)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["display_name"], "김철수")
        self.assertEqual(records[0]["english_name"], "Chulsoo Kim")


if __name__ == "__main__":
    unittest.main()

