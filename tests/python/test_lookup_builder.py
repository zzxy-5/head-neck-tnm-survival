import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.lookup_builder import (
    build_site_artifact,
    build_site_shards,
    tnm_key_candidates,
)
from era_survival.schema import TNMRecord


class LookupBuilderTests(unittest.TestCase):
    def setUp(self):
        self.larynx_record = TNMRecord(
            2016, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "SEER Combined TNM",
        )
        self.thyroid_record = TNMRecord(
            2016, "Female", "Thyroid", "Adenocarcinoma", "70-79", "70+", 60, False,
            "T1", "N0", "M0", "SEER Combined TNM",
        )

    def test_tnm_candidate_keys_follow_the_exact_eleven_level_order(self):
        self.assertEqual(
            tnm_key_candidates(self.larynx_record),
            [
                "full|Male|Larynx|SCC|50-59|T2|N1|M0",
                "no_sex|Any|Larynx|SCC|50-59|T2|N1|M0",
                "site_histology_coarse_age|Any|Larynx|SCC|<60|T2|N1|M0",
                "site_histology_tnm|Any|Larynx|SCC|Any|T2|N1|M0",
                "site_histology_m|Any|Larynx|SCC|Any|Any|Any|M0",
                "site_histology|Any|Larynx|SCC|Any|Any|Any|Any",
                "no_histology|Any|Larynx|Any|50-59|T2|N1|M0",
                "coarse_age|Any|Larynx|Any|<60|T2|N1|M0",
                "site_tnm|Any|Larynx|Any|Any|T2|N1|M0",
                "site_m|Any|Larynx|Any|Any|Any|Any|M0",
                "site_only|Any|Larynx|Any|Any|Any|Any|Any",
            ],
        )

    def test_site_artifact_has_ranked_rows_and_index_positions(self):
        other_full_match = TNMRecord(
            2016, "Female", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "SEER Combined TNM",
        )
        artifact = build_site_artifact(
            "Larynx", [self.larynx_record, self.larynx_record, other_full_match],
        )

        self.assertEqual(artifact["site"], "Larynx")
        self.assertEqual(
            [row["matching_level"] for row in artifact["rows"][:2]],
            ["full", "full"],
        )
        self.assertEqual(
            [row["sample_size"] for row in artifact["rows"][:2]],
            [2, 1],
        )
        self.assertEqual(
            artifact["index"],
            {row["key"]: offset for offset, row in enumerate(artifact["rows"])},
        )

    def test_site_artifact_rejects_cross_site_records(self):
        with self.assertRaisesRegex(ValueError, "Larynx"):
            build_site_artifact("Larynx", [self.larynx_record, self.thyroid_record])

    def test_build_site_shards_keeps_rows_site_scoped_and_serializes_no_mx(self):
        shards, manifest = build_site_shards([
            self.larynx_record,
            self.thyroid_record,
        ])

        self.assertEqual(set(shards), {"Larynx", "Thyroid"})
        self.assertEqual(
            manifest,
            {"sites": {"Larynx": "larynx.json", "Thyroid": "thyroid.json"}},
        )
        for site, artifact in shards.items():
            self.assertEqual(artifact["site"], site)
            self.assertTrue(all(row["site"] == site for row in artifact["rows"]))
            self.assertNotIn("MX", json.dumps(artifact, allow_nan=False))

    def test_site_artifact_and_shards_reject_unnormalized_mx_before_output(self):
        mx_record = TNMRecord(
            2016, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "MX", "SEER Combined TNM",
        )

        with self.assertRaisesRegex(ValueError, "M0"):
            build_site_artifact("Larynx", [mx_record])
        with self.assertRaisesRegex(ValueError, "M0"):
            build_site_shards([mx_record])

    def test_builder_rejects_stage_sources_from_the_wrong_diagnosis_era(self):
        wrong_2015 = TNMRecord(
            2015, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "SEER Combined TNM",
        )
        wrong_2016 = TNMRecord(
            2016, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "AJCC 7th edition",
        )

        for record in (wrong_2015, wrong_2016):
            with self.subTest(year=record.year, source=record.stage_source):
                with self.assertRaisesRegex(ValueError, "stage source"):
                    build_site_artifact("Larynx", [record])
                with self.assertRaisesRegex(ValueError, "stage source"):
                    build_site_shards([record])

    def test_builder_accepts_the_exact_stage_source_for_each_diagnosis_era(self):
        ajcc_record = TNMRecord(
            2015, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "AJCC 7th edition",
        )
        combined_record = TNMRecord(
            2016, "Male", "Larynx", "SCC", "50-59", "<60", 24, True,
            "T2", "N1", "M0", "SEER Combined TNM",
        )

        artifact = build_site_artifact("Larynx", [ajcc_record, combined_record])

        self.assertEqual(
            artifact["stage_sources"],
            ["AJCC 7th edition", "SEER Combined TNM"],
        )


if __name__ == "__main__":
    unittest.main()
