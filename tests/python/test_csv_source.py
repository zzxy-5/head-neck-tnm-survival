import csv
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.csv_source import CsvSource


class CsvSourceTests(unittest.TestCase):
    def write_csv(self, path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def test_rows_projects_required_columns_and_tracks_each_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            self.write_csv(path, ["Sex", "Unused"], [{"Sex": "Female", "Unused": "x"}])
            source = CsvSource((path,), required_columns=("Sex",))
            self.assertEqual(list(source.rows()), [{"Sex": "Female"}])
            self.assertEqual(source.source_counts, {"source.csv": 1})

    def test_rows_tracks_counts_for_each_source_file(self):
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.csv"
            second = Path(directory) / "second.csv"
            self.write_csv(first, ["Sex"], [{"Sex": "Female"}, {"Sex": "Male"}])
            self.write_csv(second, ["Sex"], [{"Sex": "Female"}])

            source = CsvSource((first, second), required_columns=("Sex",))

            self.assertEqual(len(list(source.rows())), 3)
            self.assertEqual(source.source_counts, {"first.csv": 2, "second.csv": 1})

    def test_rows_normalizes_missing_selected_cell_to_empty_string(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            path.write_text("Sex,Survival months\nFemale\n", encoding="utf-8")
            source = CsvSource((path,), required_columns=("Sex", "Survival months"))
            self.assertEqual(list(source.rows()), [{"Sex": "Female", "Survival months": ""}])

    def test_missing_column_names_are_reported_together(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.csv"
            self.write_csv(path, ["Sex"], [])
            with self.assertRaisesRegex(ValueError, "Survival months, Year of diagnosis"):
                list(CsvSource((path,), required_columns=("Sex", "Survival months", "Year of diagnosis")).rows())
