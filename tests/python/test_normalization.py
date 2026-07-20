from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.normalization import (
    age_groups,
    choose_tnm_source,
    normalize_m_stage,
    normalize_n_stage,
    normalize_t_stage,
    normalize_tnm_record,
    parse_survival_months,
)
from era_survival.schema import SOURCE_COLUMNS, TNMRecord


class NormalizationTests(unittest.TestCase):
    def make_row(self, year="2015", **overrides):
        row = {
            SOURCE_COLUMNS["sex"]: "Female",
            SOURCE_COLUMNS["year"]: year,
            SOURCE_COLUMNS["site"]: "Tongue",
            SOURCE_COLUMNS["histology"]: "Squamous cell neoplasms",
            SOURCE_COLUMNS["age"]: "45 years",
            SOURCE_COLUMNS["survival_months"]: "12.0",
            SOURCE_COLUMNS["vital_status"]: "Dead",
            SOURCE_COLUMNS["ajcc_t"]: "T1",
            SOURCE_COLUMNS["ajcc_n"]: "N0",
            SOURCE_COLUMNS["ajcc_m"]: "M0",
            SOURCE_COLUMNS["combined_t"]: "T4a",
            SOURCE_COLUMNS["combined_n"]: "N2c",
            SOURCE_COLUMNS["combined_m"]: "M1",
        }
        row.update({SOURCE_COLUMNS[name]: value for name, value in overrides.items()})
        return row

    def test_survival_months_require_nonnegative_integral_value(self):
        self.assertEqual(parse_survival_months("12"), 12)
        self.assertEqual(parse_survival_months("12.0"), 12)

        for raw in ("12.9", "-0.5", "-1", "NaN", "Infinity", "-Infinity", ""):
            with self.subTest(raw=raw):
                try:
                    parse_survival_months(raw)
                except ValueError:
                    continue
                except Exception as error:
                    self.fail(f"{raw!r} raised {type(error).__name__}, expected ValueError")
                self.fail(f"{raw!r} was accepted")

    def test_single_age_recode_supports_90_plus(self):
        row = self.make_row(age="90+ years")
        self.assertEqual(normalize_tnm_record(row).age_group, "80+")

    def test_age_recode_rejects_malformed_forms(self):
        for raw in ("-1 years", "invalid45", "45-50 years", "years"):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    age_groups(raw)

    def test_combined_prefixes_and_substages_collapse(self):
        self.assertEqual(normalize_t_stage("p4A"), "T4")
        self.assertEqual(normalize_t_stage("T4a"), "T4")
        self.assertEqual(normalize_t_stage("c2"), "T2")
        self.assertEqual(normalize_t_stage("cX"), "Unknown")
        self.assertEqual(normalize_n_stage("p2C"), "N2")
        self.assertEqual(normalize_n_stage("N2c"), "N2")
        self.assertEqual(normalize_n_stage("N3b"), "N3")
        self.assertEqual(normalize_m_stage("MX"), "M0")
        self.assertEqual(normalize_m_stage("cX"), "Unknown")
        self.assertEqual(normalize_m_stage("Blank(s)"), "Unknown")

    def test_tnm_source_switches_between_defined_eras(self):
        row = {
            SOURCE_COLUMNS["ajcc_t"]: "T1",
            SOURCE_COLUMNS["ajcc_n"]: "N0",
            SOURCE_COLUMNS["ajcc_m"]: "M0",
            SOURCE_COLUMNS["combined_t"]: "c4A",
            SOURCE_COLUMNS["combined_n"]: "c2B",
            SOURCE_COLUMNS["combined_m"]: "c1",
        }
        self.assertEqual(
            choose_tnm_source(row, 2015),
            ("T1", "N0", "M0", "AJCC 7th edition"),
        )
        self.assertEqual(
            choose_tnm_source(row, 2016),
            ("c4A", "c2B", "c1", "SEER Combined TNM"),
        )

    def test_tnm_record_uses_only_the_years_era_columns(self):
        record_2015 = normalize_tnm_record(self.make_row(year="2015"))
        self.assertEqual(
            (record_2015.t_stage, record_2015.n_stage, record_2015.m_stage, record_2015.stage_source),
            ("T1", "N0", "M0", "AJCC 7th edition"),
        )

        record_2016 = normalize_tnm_record(self.make_row(year="2016"))
        self.assertEqual(
            (record_2016.t_stage, record_2016.n_stage, record_2016.m_stage, record_2016.stage_source),
            ("T4", "N2", "M1", "SEER Combined TNM"),
        )

    def test_2017_combined_tnm_and_mx_maps_to_m0(self):
        row = self.make_row(year="2017", combined_t="cT3", combined_n="cN2b", combined_m="MX")
        record = normalize_tnm_record(row)
        self.assertEqual((record.t_stage, record.n_stage, record.m_stage), ("T3", "N2", "M0"))
        self.assertEqual(record.stage_source, "SEER Combined TNM")

    def test_tnm_record_builds_dataclass_and_applies_year_boundaries(self):
        self.assertEqual(
            normalize_tnm_record(self.make_row(year="2010")),
            TNMRecord(
                year=2010,
                sex="Female",
                site="Tongue",
                histology_group="Squamous cell neoplasms",
                age_group="40-49",
                coarse_age_group="<60",
                survival_months=12,
                event=True,
                t_stage="T1",
                n_stage="N0",
                m_stage="M0",
                stage_source="AJCC 7th edition",
            ),
        )
        self.assertIsNotNone(normalize_tnm_record(self.make_row(year="2017")))
        with self.assertRaises(ValueError):
            normalize_tnm_record(self.make_row(year="2009"))
        with self.assertRaises(ValueError):
            normalize_tnm_record(self.make_row(year="2018"))

    def test_tnm_record_preserves_unknown_stages_for_website(self):
        record = normalize_tnm_record(
            self.make_row(year="2016", combined_t="Blank(s)", combined_n="cX", combined_m="Blank(s)")
        )
        self.assertEqual((record.t_stage, record.n_stage, record.m_stage), ("Unknown", "Unknown", "Unknown"))

    def test_categorical_fields_are_stripped_before_record_creation(self):
        record = normalize_tnm_record(
            self.make_row(sex=" Female ", histology=" Squamous cell neoplasms ")
        )
        self.assertEqual(record.sex, "Female")
        self.assertEqual(record.histology_group, "Squamous cell neoplasms")

    def test_blank_or_whitespace_sex_is_rejected(self):
        for raw in ("", "   "):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "(?i)sex"):
                    normalize_tnm_record(self.make_row(sex=raw))

    def test_blank_or_whitespace_histology_is_rejected(self):
        for raw in ("", "   "):
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, "(?i)histology"):
                    normalize_tnm_record(self.make_row(histology=raw))


if __name__ == "__main__":
    unittest.main()
