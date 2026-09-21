from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.schema import DEFAULT_SOURCE_PATHS, SITE_SLUGS, SOURCE_COLUMNS, TARGET_SITES


class SchemaTests(unittest.TestCase):
    def test_four_sources_and_thirteen_target_sites(self):
        self.assertEqual(
            DEFAULT_SOURCE_PATHS,
            (
                Path("/Volumes/PortableSSD/prediction/export_C00-C09.csv"),
                Path("/Volumes/PortableSSD/prediction/export_C10-C14.csv"),
                Path("/Volumes/PortableSSD/prediction/export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv"),
                Path("/Volumes/PortableSSD/prediction/export_C73-C75.csv"),
            ),
        )
        self.assertEqual(
            TARGET_SITES,
            frozenset({
                "Lip",
                "Tongue",
                "Gum and Other Mouth",
                "Floor of Mouth",
                "Salivary Gland",
                "Tonsil",
                "Oropharynx",
                "Nasopharynx",
                "Hypopharynx",
                "Other Oral Cavity and Pharynx",
                "Nose, Nasal Cavity and Middle Ear",
                "Larynx",
                "Thyroid",
            }),
        )
        self.assertEqual(
            SITE_SLUGS,
            {
                "Lip": "lip",
                "Tongue": "tongue",
                "Gum and Other Mouth": "gum-other-mouth",
                "Floor of Mouth": "floor-mouth",
                "Salivary Gland": "salivary-gland",
                "Tonsil": "tonsil",
                "Oropharynx": "oropharynx",
                "Nasopharynx": "nasopharynx",
                "Hypopharynx": "hypopharynx",
                "Other Oral Cavity and Pharynx": "other-oral-cavity-pharynx",
                "Nose, Nasal Cavity and Middle Ear": "nose-nasal-cavity-middle-ear",
                "Larynx": "larynx",
                "Thyroid": "thyroid",
            },
        )

    def test_source_columns_are_limited_to_the_tnm_pipeline(self):
        self.assertEqual(SOURCE_COLUMNS["age"], "Age recode with single ages and 90+")
        self.assertEqual(SOURCE_COLUMNS["ajcc_m_6"], "Derived AJCC M, 6th ed (2004-2015)")
        self.assertEqual(SOURCE_COLUMNS["combined_t"], "Derived SEER Combined T (2016-2017)")
        self.assertEqual(SOURCE_COLUMNS["primary_site"], "Primary Site")
        self.assertNotIn("summary_stage", SOURCE_COLUMNS)
        self.assertNotIn("eod_m", SOURCE_COLUMNS)


if __name__ == "__main__":
    unittest.main()
