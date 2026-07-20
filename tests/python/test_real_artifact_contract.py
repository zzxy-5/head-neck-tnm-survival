import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.schema import SITE_SLUGS, TARGET_SITES


EXPECTED_SITE_COUNTS = {
    "Nose, Nasal Cavity and Middle Ear": 4_969,
    "Larynx": 21_786,
    "Thyroid": 99_715,
}
EXPECTED_SOURCES = {
    "export_C00-C09.csv",
    "export_C10-C14.csv",
    "export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv",
    "export_C73-C75.csv",
}


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


class RealArtifactContractTests(unittest.TestCase):
    def test_real_artifacts_reconcile(self):
        data = PROJECT / "public" / "data"
        metadata = read_json(data / "metadata.json")
        options = read_json(data / "options.json")
        manifest = read_json(data / "site_manifest.json")

        self.assertEqual(metadata["flow_counts"]["source_rows"], 1_808_471)
        self.assertEqual(set(metadata["source_counts"]), EXPECTED_SOURCES)
        self.assertEqual(sum(metadata["source_counts"].values()), 1_808_471)
        self.assertEqual(metadata["eligible_record_count"], 211_160)
        self.assertEqual(sum(metadata["site_record_counts"].values()), 211_160)
        self.assertEqual(set(metadata["site_record_counts"]), TARGET_SITES)
        for site, count in EXPECTED_SITE_COUNTS.items():
            self.assertEqual(metadata["site_record_counts"][site], count)

        self.assertEqual(options["sites"], list(SITE_SLUGS))
        self.assertEqual(options["m_stages"], ["M0", "M1", "Unknown"])
        self.assertEqual(
            manifest["sites"],
            {site: f"{slug}.json" for site, slug in SITE_SLUGS.items()},
        )

        expected_json_paths = {
            "metadata.json",
            "options.json",
            "site_manifest.json",
            *{f"lookup/{filename}" for filename in manifest["sites"].values()},
        }
        actual_json_paths = {
            path.relative_to(data).as_posix()
            for path in data.rglob("*.json")
        }
        self.assertEqual(actual_json_paths, expected_json_paths)

        all_artifacts = [metadata, options, manifest]
        for site, filename in manifest["sites"].items():
            shard = read_json(data / "lookup" / filename)
            self.assertEqual(shard["site"], site)
            self.assertGreater(shard["summary"]["record_count"], 0)
            self.assertGreater(len(shard["rows"]), 0)
            for row in shard["rows"]:
                self.assertNotIn("curve_ci_lower_probs", row)
                self.assertNotIn("curve_ci_upper_probs", row)
                self.assertIn("fixed_survival", row)
                for horizon in ("12", "36", "60"):
                    fixed = row["fixed_survival"][horizon]
                    self.assertIn("confidence_interval", fixed)
                    if fixed["status"] == "estimable":
                        self.assertEqual(len(fixed["confidence_interval"]), 2)
                self.assertIn("risk_table_months", row)
                self.assertIn("risk_table_counts", row)
                self.assertEqual(len(row["risk_table_months"]), len(row["risk_table_counts"]))
            all_artifacts.append(shard)

        payload = json.dumps(all_artifacts, ensure_ascii=False)
        self.assertNotIn("MX", payload)
        self.assertNotIn("summary_stage", payload.lower())
        self.assertNotIn("eod", payload.lower())


if __name__ == "__main__":
    unittest.main()
