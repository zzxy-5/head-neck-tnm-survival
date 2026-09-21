import copy
import json
from pathlib import Path
import sys
import unittest

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "scripts"))

from era_survival.lookup_builder import THRESHOLDS
from era_survival.schema import SITE_SLUGS, TARGET_SITES
from era_survival.validation import (
    EXPECTED_ELIGIBLE_RECORD_COUNT,
    EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
    EXPECTED_SITE_V2_RECORD_COUNTS,
    EXPECTED_SOURCE_ROW_COUNT,
    FIXED_TIME_POLICY,
    MX_POLICY,
    STAGE_SOURCE_POLICY,
    validate_stage_source_for_year,
    validate_artifact_set,
)
from era_survival.site_mapping import SITE_V2_MAPPING_POLICY, SITE_V2_SLUGS


EXPECTED_ADDED_SITE_COUNTS = {
    "Nose, Nasal Cavity and Middle Ear": 4_969,
    "Larynx": 21_786,
    "Thyroid": 99_715,
}


def expected_site_counts() -> dict[str, int]:
    counts = {
        site: 8_000
        for site in list(SITE_SLUGS)[:9]
    }
    counts[list(SITE_SLUGS)[9]] = 12_690
    counts.update(EXPECTED_ADDED_SITE_COUNTS)
    assert sum(counts.values()) == EXPECTED_ELIGIBLE_RECORD_COUNT
    return counts


def lookup_row(site: str, count: int) -> dict:
    key = f"site_only|Any|{site}|Any|Any|Any|Any|Any"
    return {
        "key": key,
        "cohort_type": "tnm_2010_2017",
        "stage_source": "AJCC 7th edition; SEER Combined TNM",
        "matching_level": "site_only",
        "sex": "Any",
        "site": site,
        "histology_group": "Any",
        "age_group": "Any",
        "t_stage": "Any",
        "n_stage": "Any",
        "m_stage": "Any",
        "sample_size": count,
        "event_count": 0,
        "censor_count": count,
        "median_survival_months": None,
        "median_followup_months": 60.0,
        "maximum_followup_months": 60,
        "fixed_survival": {
            horizon: {
                "estimate": 1.0,
                "confidence_interval": [1.0, 1.0],
                "status": "estimable",
            }
            for horizon in ("12", "36", "60")
        },
        "curve_months": [0, 60],
        "curve_survival_probs": [1.0, 1.0],
        "censor_months": [60],
        "risk_table_months": [0, 12, 24, 36, 48, 60],
        "risk_table_counts": [count] * 6,
        "data_quality_flag": "stable",
    }


def valid_artifact_set() -> tuple[dict, dict, dict, dict[str, dict]]:
    site_counts = expected_site_counts()
    source_counts = {
        "export_C00-C09.csv": 500_000,
        "export_C10-C14.csv": 100_000,
        "export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv": 800_000,
        "export_C73-C75.csv": 408_471,
    }
    exclusion_counts = {
        "non_target_site_excluded": 1_000_000,
        "outside_tnm_years_excluded": 597_311,
    }
    metadata = {
        "version": 1,
        "generated_at": "2026-07-20T00:00:00Z",
        "source_counts": source_counts,
        "flow_counts": {
            "source_rows": EXPECTED_SOURCE_ROW_COUNT,
            **exclusion_counts,
            "tnm_cohort": EXPECTED_ELIGIBLE_RECORD_COUNT,
        },
        "exclusion_counts": exclusion_counts,
        "eligible_record_count": EXPECTED_ELIGIBLE_RECORD_COUNT,
        "site_record_counts": site_counts,
        "stage_source_policy": dict(STAGE_SOURCE_POLICY),
        "mx_policy": MX_POLICY,
        "fixed_time_policy": FIXED_TIME_POLICY,
        "thresholds": dict(THRESHOLDS),
    }
    options = {
        "version": 1,
        "sites": list(SITE_SLUGS),
        "sexes": ["Female", "Male"],
        "histology_groups": ["SCC"],
        "age_groups": ["<40", "40-49", "50-59", "60-69", "70-79", "80+"],
        "t_stages": ["T0", "T1", "T2", "T3", "T4", "Unknown"],
        "n_stages": ["N0", "N1", "N2", "N3", "Unknown"],
        "m_stages": ["M0", "M1", "Unknown"],
    }
    manifest = {
        "sites": {site: f"{slug}.json" for site, slug in SITE_SLUGS.items()}
    }
    shards = {}
    for site, count in site_counts.items():
        row = lookup_row(site, count)
        shards[site] = {
            "version": 1,
            "site": site,
            "cohort_type": "tnm_2010_2017",
            "cohort_years": [2010, 2017],
            "stage_sources": ["AJCC 7th edition", "SEER Combined TNM"],
            "thresholds": dict(THRESHOLDS),
            "confidence_interval": {"level": 0.95, "method": "Greenwood log-log"},
            "rows": [row],
            "index": {row["key"]: 0},
            "summary": {
                "record_count": count,
                "row_count": 1,
                "sexes": ["Female", "Male"],
                "histology_groups": ["SCC"],
            },
        }
    return metadata, options, manifest, shards


def valid_site_v2_artifact_set() -> tuple[dict, dict, dict, dict[str, dict]]:
    metadata, options, _manifest, _shards = valid_artifact_set()
    site_counts = {
        site: EXPECTED_SITE_V2_RECORD_COUNTS[site]
        for site in SITE_V2_SLUGS
    }
    metadata.update({
        "cohort_version": "site_v2_main",
        "source_eligible_record_count": EXPECTED_ELIGIBLE_RECORD_COUNT,
        "eligible_record_count": EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
        "site_record_counts": site_counts,
        "precomputed_combination_count": 22_474,
        "returnable_combination_count": 4_010,
        "site_v2_record_counts": dict(EXPECTED_SITE_V2_RECORD_COUNTS),
        "main_analysis_record_count": EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
        "site_v2_excluded_site_counts": {
            "Nasopharynx": 4_493,
            "Thyroid": 99_715,
        },
        "site_v2_mapping_policy": SITE_V2_MAPPING_POLICY,
    })
    options["sites"] = list(SITE_V2_SLUGS)
    manifest = {
        "sites": {site: f"{slug}.json" for site, slug in SITE_V2_SLUGS.items()}
    }
    shards = {}
    for site, count in site_counts.items():
        row = lookup_row(site, count)
        shards[site] = {
            "version": 1,
            "site": site,
            "cohort_type": "tnm_2010_2017",
            "cohort_years": [2010, 2017],
            "stage_sources": ["AJCC 7th edition", "SEER Combined TNM"],
            "thresholds": dict(THRESHOLDS),
            "confidence_interval": {"level": 0.95, "method": "Greenwood log-log"},
            "rows": [row],
            "index": {row["key"]: 0},
            "summary": {
                "record_count": count,
                "row_count": 1,
                "sexes": ["Female", "Male"],
                "histology_groups": ["SCC"],
            },
        }
    return metadata, options, manifest, shards


class ArtifactSetValidationTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = valid_artifact_set()

    def validate(self, artifacts=None):
        validate_artifact_set(*(artifacts or self.artifacts))

    def test_complete_focused_artifact_set_passes(self):
        self.validate()

    def test_site_v2_main_artifact_set_passes_with_exact_ten_site_contract(self):
        artifacts = valid_site_v2_artifact_set()
        validate_artifact_set(
            *artifacts,
            site_slugs=SITE_V2_SLUGS,
            expected_eligible_record_count=EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
            cohort_version="site_v2_main",
        )

        broken = copy.deepcopy(artifacts)
        broken[0]["site_record_counts"]["Oropharynx"] -= 1
        with self.assertRaisesRegex(ValueError, "site_record_counts"):
            validate_artifact_set(
                *broken,
                site_slugs=SITE_V2_SLUGS,
                expected_eligible_record_count=EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
                cohort_version="site_v2_main",
            )

    def test_site_v2_metadata_is_validated_while_legacy_metadata_remains_valid(self):
        artifacts = copy.deepcopy(self.artifacts)
        metadata = artifacts[0]
        metadata.update({
            "site_v2_record_counts": dict(EXPECTED_SITE_V2_RECORD_COUNTS),
            "main_analysis_record_count": EXPECTED_MAIN_ANALYSIS_RECORD_COUNT,
            "site_v2_excluded_site_counts": {
                "Nasopharynx": 4_493,
                "Thyroid": 99_715,
            },
            "site_v2_mapping_policy": SITE_V2_MAPPING_POLICY,
        })
        self.validate(artifacts)

        broken = copy.deepcopy(artifacts)
        broken[0]["site_v2_record_counts"]["Oropharynx"] -= 1
        with self.assertRaisesRegex(ValueError, "site_v2_record_counts.Oropharynx"):
            self.validate(broken)

        missing = copy.deepcopy(artifacts)
        del missing[0]["site_v2_mapping_policy"]
        with self.assertRaisesRegex(ValueError, "site_v2_mapping_policy"):
            self.validate(missing)

        mismatched_exclusion = copy.deepcopy(artifacts)
        mismatched_exclusion[0]["site_v2_excluded_site_counts"] = {
            "Nasopharynx": 99_715,
            "Thyroid": 4_493,
        }
        with self.assertRaisesRegex(ValueError, "site_v2_excluded_site_counts.Nasopharynx"):
            self.validate(mismatched_exclusion)

    def test_source_and_eligible_totals_are_exact_and_reconcile(self):
        for field, value in (
            ("source_rows", EXPECTED_SOURCE_ROW_COUNT - 1),
            ("tnm_cohort", EXPECTED_ELIGIBLE_RECORD_COUNT - 1),
        ):
            with self.subTest(field=field):
                artifacts = copy.deepcopy(self.artifacts)
                artifacts[0]["flow_counts"][field] = value
                with self.assertRaisesRegex(ValueError, field):
                    self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[0]["source_counts"]["export_C73-C75.csv"] -= 1
        with self.assertRaisesRegex(ValueError, "source_counts"):
            self.validate(artifacts)

    def test_exclusions_partition_source_rows(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[0]["exclusion_counts"]["non_target_site_excluded"] -= 1
        with self.assertRaisesRegex(ValueError, "exclusion_counts"):
            self.validate(artifacts)

    def test_site_counts_cover_exactly_thirteen_sites_and_expected_totals(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[0]["site_record_counts"].pop("Lip")
        with self.assertRaisesRegex(ValueError, "site_record_counts"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[0]["site_record_counts"]["Larynx"] -= 1
        artifacts[0]["site_record_counts"]["Lip"] += 1
        with self.assertRaisesRegex(ValueError, "Larynx"):
            self.validate(artifacts)

    def test_options_have_all_sites_and_exact_m_stage_choices(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[1]["m_stages"] = ["M0", "M1", "MX", "Unknown"]
        with self.assertRaisesRegex(ValueError, "m_stages"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[1]["sites"].pop()
        with self.assertRaisesRegex(ValueError, "options.sites"):
            self.validate(artifacts)

    def test_manifest_and_shards_cover_exactly_the_target_sites(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[2]["sites"]["Larynx"] = "wrong.json"
        with self.assertRaisesRegex(ValueError, "manifest.sites.Larynx"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3].pop("Thyroid")
        with self.assertRaisesRegex(ValueError, "shards"):
            self.validate(artifacts)

    def test_shard_summary_and_site_only_row_reconcile_with_metadata(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["summary"]["record_count"] -= 1
        with self.assertRaisesRegex(ValueError, "Larynx.*record_count"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["rows"][0]["sample_size"] -= 1
        with self.assertRaisesRegex(ValueError, "sample_size"):
            self.validate(artifacts)

    def test_rows_reject_eod_fields_curve_confidence_arrays_and_mx(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["rows"][0]["eod_t_stage"] = "T1"
        with self.assertRaisesRegex(ValueError, "EOD"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["rows"][0]["curve_ci_lower_probs"] = [1.0, 1.0]
        with self.assertRaisesRegex(ValueError, "curve_ci_lower_probs"):
            self.validate(artifacts)

        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["rows"][0]["m_stage"] = "MX"
        with self.assertRaisesRegex(ValueError, "MX"):
            self.validate(artifacts)

    def test_rows_reject_unsupported_stage_sources(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["rows"][0]["stage_source"] = "EOD 2018"
        with self.assertRaisesRegex(ValueError, "stage_source"):
            self.validate(artifacts)

    def test_validation_rejects_stage_sources_from_the_wrong_diagnosis_era(self):
        for year, source in (
            (2015, "SEER Combined TNM"),
            (2016, "AJCC 7th edition"),
        ):
            with self.subTest(year=year, source=source):
                with self.assertRaisesRegex(ValueError, "stage source"):
                    validate_stage_source_for_year(year, source, "record")

    def test_validation_accepts_exact_stage_sources_for_each_diagnosis_era(self):
        validate_stage_source_for_year(2010, "AJCC 7th edition", "record")
        validate_stage_source_for_year(2015, "AJCC 7th edition", "record")
        validate_stage_source_for_year(2016, "SEER Combined TNM", "record")
        validate_stage_source_for_year(2017, "SEER Combined TNM", "record")

    def test_shard_stage_sources_must_cover_both_documented_eras(self):
        artifacts = copy.deepcopy(self.artifacts)
        artifacts[3]["Larynx"]["stage_sources"] = ["AJCC 7th edition"]

        with self.assertRaisesRegex(ValueError, "stage_sources"):
            self.validate(artifacts)

    def test_metadata_requires_documented_policies_and_thresholds(self):
        for field in ("stage_source_policy", "mx_policy", "fixed_time_policy", "thresholds"):
            with self.subTest(field=field):
                artifacts = copy.deepcopy(self.artifacts)
                del artifacts[0][field]
                with self.assertRaisesRegex(ValueError, field):
                    self.validate(artifacts)

    def test_focused_payload_contains_no_summary_stage_or_uppercase_mx(self):
        payload = json.dumps(self.artifacts, ensure_ascii=False)
        self.assertNotIn("summary_stage", payload.lower())
        self.assertNotIn("MX", payload)


if __name__ == "__main__":
    unittest.main()
