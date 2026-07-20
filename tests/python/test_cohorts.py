import csv
from pathlib import Path
import sys
import tempfile
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.cohorts import CohortBundle, load_cohort
from era_survival.schema import SOURCE_COLUMNS


class CohortAssemblyTests(unittest.TestCase):
    def make_row(self, year="2015", site="Tongue", **overrides):
        row = dict.fromkeys(SOURCE_COLUMNS.values(), "")
        row.update({
            SOURCE_COLUMNS["sex"]: "Female",
            SOURCE_COLUMNS["year"]: year,
            SOURCE_COLUMNS["site"]: site,
            SOURCE_COLUMNS["histology"]: "Squamous cell neoplasms",
            SOURCE_COLUMNS["age"]: "45 years",
            SOURCE_COLUMNS["survival_months"]: "12",
            SOURCE_COLUMNS["vital_status"]: "Dead",
            SOURCE_COLUMNS["ajcc_t"]: "T1",
            SOURCE_COLUMNS["ajcc_n"]: "N0",
            SOURCE_COLUMNS["ajcc_m"]: "M0",
            SOURCE_COLUMNS["combined_t"]: "T2",
            SOURCE_COLUMNS["combined_n"]: "N1",
            SOURCE_COLUMNS["combined_m"]: "M0",
        })
        row.update({SOURCE_COLUMNS[name]: value for name, value in overrides.items()})
        return row

    def write_rows(self, directory, name, rows):
        fixture_path = Path(directory) / name
        with fixture_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(SOURCE_COLUMNS.values()))
            writer.writeheader()
            writer.writerows(rows)
        return fixture_path

    def load_rows(self, rows):
        with tempfile.TemporaryDirectory() as directory:
            return load_cohort((self.write_rows(directory, "fixture.csv", rows),))

    def test_only_target_sites_and_2010_2017_enter_cohort(self):
        rows = [
            self.make_row(site="Larynx", year="2010"),
            self.make_row(site="Thyroid", year="2017"),
            self.make_row(site="Lung and Bronchus", year="2015"),
            self.make_row(site="Larynx", year="2018"),
        ]
        bundle = self.load_rows(rows)

        self.assertIsInstance(bundle, CohortBundle)
        self.assertEqual([record.site for record in bundle.records], ["Larynx", "Thyroid"])
        self.assertEqual(bundle.flow_counts["non_target_site_excluded"], 1)
        self.assertEqual(bundle.flow_counts["outside_tnm_years_excluded"], 1)
        self.assertEqual(bundle.flow_counts["tnm_cohort"], 2)

    def test_exclusion_reasons_and_source_counts_are_accounted_separately(self):
        with tempfile.TemporaryDirectory() as directory:
            first = self.write_rows(directory, "first.csv", [
                self.make_row(survival_months=""),
                self.make_row(survival_months="not-a-number"),
                self.make_row(age="not-an-age"),
                self.make_row(vital_status="Unknown"),
            ])
            second = self.write_rows(directory, "second.csv", [
                self.make_row(year="not-a-year"),
                self.make_row(site="Larynx", year="2010"),
            ])
            bundle = load_cohort((first, second))

        self.assertEqual(bundle.flow_counts["invalid_survival_excluded"], 2)
        self.assertEqual(bundle.flow_counts["invalid_age_excluded"], 1)
        self.assertEqual(bundle.flow_counts["invalid_outcome_excluded"], 1)
        self.assertEqual(bundle.flow_counts["invalid_year_excluded"], 1)
        self.assertEqual(bundle.flow_counts["tnm_cohort"], 1)
        self.assertEqual(bundle.source_counts, {"first.csv": 4, "second.csv": 2})
        self.assertEqual(sum(bundle.source_counts.values()), bundle.flow_counts["source_rows"])

    def test_blank_or_whitespace_categorical_values_are_excluded_by_reason(self):
        bundle = self.load_rows([
            self.make_row(sex=""),
            self.make_row(sex="   "),
            self.make_row(histology=""),
            self.make_row(histology="   "),
            self.make_row(),
        ])

        self.assertEqual(bundle.flow_counts["invalid_sex_excluded"], 2)
        self.assertEqual(bundle.flow_counts["invalid_histology_excluded"], 2)
        self.assertEqual(bundle.flow_counts["tnm_cohort"], 1)
        self.assertEqual(bundle.records[0].sex, "Female")
        self.assertEqual(bundle.records[0].histology_group, "Squamous cell neoplasms")


if __name__ == "__main__":
    unittest.main()
