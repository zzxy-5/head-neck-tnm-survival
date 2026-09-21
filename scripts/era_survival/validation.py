from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import math
from typing import Any

from .lookup_builder import THRESHOLDS
from .schema import DEFAULT_SOURCE_PATHS, SITE_SLUGS, TARGET_SITES
from .site_mapping import (
    SITE_V2_ALL_SITES,
    SITE_V2_EXCLUDED_SITES,
    SITE_V2_MAIN_SITES,
    SITE_V2_MAPPING_POLICY,
    SITE_V2_SLUGS,
)

EXPECTED_SOURCE_ROW_COUNT = 1_808_471
EXPECTED_ELIGIBLE_RECORD_COUNT = 211_160
EXPECTED_ADDED_SITE_COUNTS = {
    "Nose, Nasal Cavity and Middle Ear": 4_969,
    "Larynx": 21_786,
    "Thyroid": 99_715,
}
EXPECTED_SITE_V2_RECORD_COUNTS = {
    "Lip": 5_065,
    "Oral Tongue": 12_233,
    "Gum and Other Mouth": 9_444,
    "Floor of Mouth": 3_605,
    "Salivary Gland": 9_282,
    "Oropharynx": 34_483,
    "Hypopharynx": 4_209,
    "Other Oral Cavity and Pharynx": 1_740,
    "Nose, Nasal Cavity and Middle Ear": 4_969,
    "Larynx": 21_922,
    "Nasopharynx": 4_493,
    "Thyroid": 99_715,
}
EXPECTED_MAIN_ANALYSIS_RECORD_COUNT = 106_952
EXPECTED_SITE_V2_MAIN_COUNTS = {
    site: EXPECTED_SITE_V2_RECORD_COUNTS[site]
    for site in SITE_V2_MAIN_SITES
}
STAGE_SOURCE_POLICY = {
    "2010-2015": "AJCC 7th edition",
    "2016-2017": "SEER Combined TNM",
}
MX_POLICY = (
    "Explicit legacy unknown-metastasis codes in the 2010-2015 AJCC "
    "6th-edition audit field, or in the 2016-2017 Combined M field, map to M0"
)
FIXED_TIME_POLICY = (
    "Estimate only when observed follow-up reaches the requested horizon"
)

_AGE_GROUPS = ["<40", "40-49", "50-59", "60-69", "70-79", "80+"]
_T_STAGES = ["T0", "T1", "T2", "T3", "T4", "Unknown"]
_N_STAGES = ["N0", "N1", "N2", "N3", "Unknown"]
_M_STAGES = ["M0", "M1", "Unknown"]
_STAGE_SOURCES = frozenset(STAGE_SOURCE_POLICY.values())


def _fail(location: str, message: str) -> None:
    raise ValueError(f"{location}: {message}")


def validate_stage_source_for_year(year: int, stage_source: str, location: str) -> None:
    if 2010 <= year <= 2015:
        expected = STAGE_SOURCE_POLICY["2010-2015"]
    elif 2016 <= year <= 2017:
        expected = STAGE_SOURCE_POLICY["2016-2017"]
    else:
        _fail(location, f"diagnosis year {year} is outside the 2010-2017 cohort")
    if stage_source != expected:
        _fail(
            location,
            f"stage source {stage_source!r} does not match year {year}; "
            f"expected {expected!r}",
        )


def _mapping(value: object, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        _fail(location, "must be an object")
    return value


def _list(value: object, location: str) -> list:
    if not isinstance(value, list):
        _fail(location, "must be an array")
    return value


def _nonnegative_int(value: object, location: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        _fail(location, "must be a non-negative integer")
    return value


def _number(value: object, location: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0
    ):
        _fail(location, "must be a finite non-negative number")
    return value


def _probability(value: object, location: str) -> float:
    number = _number(value, location)
    if number > 1:
        _fail(location, "must be between zero and one")
    return number


def _required(container: Mapping[str, Any], fields: Sequence[str], location: str) -> None:
    for field in fields:
        if field not in container:
            _fail(f"{location}.{field}", "is required")


def _string_list(value: object, location: str, *, nonempty: bool = True) -> list[str]:
    values = _list(value, location)
    if nonempty and not values:
        _fail(location, "must not be empty")
    if any(not isinstance(item, str) or not item for item in values):
        _fail(location, "must contain non-empty strings")
    if len(set(values)) != len(values):
        _fail(location, "must not contain duplicates")
    return values


def _validate_row_stage_source(value: object, location: str) -> None:
    if not isinstance(value, str) or not value:
        _fail(location, "must be a non-empty supported stage source")
    sources = value.split("; ")
    if (
        not sources
        or len(sources) != len(set(sources))
        or not set(sources) <= _STAGE_SOURCES
        or value != "; ".join(sorted(sources))
    ):
        _fail(location, "contains an unsupported stage source")


def _validate_fixed_survival(row: Mapping[str, Any], key: str, maximum: float) -> None:
    fixed = _mapping(row.get("fixed_survival"), f"{key}.fixed_survival")
    if set(fixed) != {"12", "36", "60"}:
        _fail(f"{key}.fixed_survival", "keys must be exactly 12, 36, and 60")
    for raw_horizon, raw_entry in fixed.items():
        horizon = int(raw_horizon)
        location = f"{key}.fixed_survival.{raw_horizon}"
        entry = _mapping(raw_entry, location)
        status = entry.get("status")
        estimate = entry.get("estimate")
        interval = entry.get("confidence_interval")
        if status == "not_estimable":
            if estimate is not None or interval is not None or maximum >= horizon:
                _fail(location, "not_estimable values conflict with observed follow-up")
            continue
        if status != "estimable":
            _fail(f"{location}.status", "must be estimable or not_estimable")
        if maximum < horizon:
            _fail(location, "estimable horizon exceeds observed follow-up")
        estimate_value = _probability(estimate, f"{location}.estimate")
        bounds = _list(interval, f"{location}.confidence_interval")
        if len(bounds) != 2:
            _fail(f"{location}.confidence_interval", "must contain two values")
        low = _probability(bounds[0], f"{location}.confidence_interval[0]")
        high = _probability(bounds[1], f"{location}.confidence_interval[1]")
        if not low <= estimate_value <= high:
            _fail(f"{location}.confidence_interval", "must contain the estimate")


def _validate_lookup_row(row: Mapping[str, Any], shard_site: str) -> None:
    key = row.get("key")
    if not isinstance(key, str) or not key:
        _fail(f"{shard_site}.row.key", "must be a non-empty string")
    if row.get("site") != shard_site:
        _fail(f"{key}.site", f"must equal {shard_site}")
    if any("eod" in field.lower() for field in row):
        _fail(f"{key}.EOD", "EOD fields must be omitted")
    if "curve_ci_lower_probs" in row or "curve_ci_upper_probs" in row:
        _fail(f"{key}.curve_ci_lower_probs", "curve confidence arrays must be omitted")
    if row.get("m_stage") not in {*_M_STAGES, "Any"}:
        _fail(f"{key}.m_stage", f"unsupported value {row.get('m_stage')}")
    _validate_row_stage_source(row.get("stage_source"), f"{key}.stage_source")

    sample_size = _nonnegative_int(row.get("sample_size"), f"{key}.sample_size")
    event_count = _nonnegative_int(row.get("event_count"), f"{key}.event_count")
    censor_count = _nonnegative_int(row.get("censor_count"), f"{key}.censor_count")
    if sample_size != event_count + censor_count:
        _fail(f"{key}.sample_size", "must equal event_count plus censor_count")

    maximum = _number(row.get("maximum_followup_months"), f"{key}.maximum_followup_months")
    for field in ("median_survival_months", "median_followup_months"):
        value = row.get(field)
        if value is not None and _number(value, f"{key}.{field}") > maximum:
            _fail(f"{key}.{field}", "must not exceed maximum follow-up")

    curve_months = _list(row.get("curve_months"), f"{key}.curve_months")
    curve_survival = _list(row.get("curve_survival_probs"), f"{key}.curve_survival_probs")
    if not curve_months or len(curve_months) != len(curve_survival):
        _fail(f"{key}.curve", "month and survival arrays must be nonempty and aligned")
    for position, month in enumerate(curve_months):
        if _number(month, f"{key}.curve_months[{position}]") > maximum:
            _fail(f"{key}.curve_months[{position}]", "must not exceed maximum follow-up")
    if curve_months[0] != 0 or any(a > b for a, b in zip(curve_months, curve_months[1:])):
        _fail(f"{key}.curve_months", "must start at zero and be non-decreasing")
    for position, probability in enumerate(curve_survival):
        _probability(probability, f"{key}.curve_survival_probs[{position}]")
    if curve_survival[0] != 1 or any(a < b for a, b in zip(curve_survival, curve_survival[1:])):
        _fail(f"{key}.curve_survival_probs", "must start at one and be non-increasing")

    censor_months = _list(row.get("censor_months"), f"{key}.censor_months")
    for position, month in enumerate(censor_months):
        if _number(month, f"{key}.censor_months[{position}]") > maximum:
            _fail(f"{key}.censor_months[{position}]", "must not exceed maximum follow-up")
    if any(a >= b for a, b in zip(censor_months, censor_months[1:])):
        _fail(f"{key}.censor_months", "must be strictly increasing")

    risk_months = _list(row.get("risk_table_months"), f"{key}.risk_table_months")
    risk_counts = _list(row.get("risk_table_counts"), f"{key}.risk_table_counts")
    if not risk_months or len(risk_months) != len(risk_counts):
        _fail(f"{key}.risk_table", "month and count arrays must be nonempty and aligned")
    for position, month in enumerate(risk_months):
        _number(month, f"{key}.risk_table_months[{position}]")
    if any(a >= b for a, b in zip(risk_months, risk_months[1:])):
        _fail(f"{key}.risk_table_months", "must be strictly increasing")
    for position, count in enumerate(risk_counts):
        if _nonnegative_int(count, f"{key}.risk_table_counts[{position}]") > sample_size:
            _fail(f"{key}.risk_table_counts[{position}]", "must not exceed sample_size")
    if risk_months[0] == 0 and risk_counts[0] != sample_size:
        _fail(f"{key}.risk_table_counts", "count at month zero must equal sample_size")
    if any(a < b for a, b in zip(risk_counts, risk_counts[1:])):
        _fail(f"{key}.risk_table_counts", "must be non-increasing")

    expected_quality = (
        "stable" if sample_size >= THRESHOLDS["stable_sample"]
        else "small_sample" if sample_size >= THRESHOLDS["minimum_sample"]
        else "very_small_sample"
    )
    if row.get("data_quality_flag") != expected_quality:
        _fail(f"{key}.data_quality_flag", f"must equal {expected_quality}")
    _validate_fixed_survival(row, key, maximum)


def _validate_shard(site: str, artifact: object, expected_count: int) -> None:
    shard = _mapping(artifact, f"shards.{site}")
    if shard.get("version") != 1:
        _fail(f"shards.{site}.version", "must equal 1")
    if shard.get("site") != site:
        _fail(f"shards.{site}.site", f"must equal {site}")
    if shard.get("cohort_type") != "tnm_2010_2017":
        _fail(f"shards.{site}.cohort_type", "must equal tnm_2010_2017")
    if shard.get("cohort_years") != [2010, 2017]:
        _fail(f"shards.{site}.cohort_years", "must equal 2010 through 2017")
    if shard.get("thresholds") != THRESHOLDS:
        _fail(f"shards.{site}.thresholds", f"must equal {THRESHOLDS}")
    sources = _string_list(shard.get("stage_sources"), f"shards.{site}.stage_sources")
    if set(sources) != _STAGE_SOURCES:
        _fail(
            f"shards.{site}.stage_sources",
            "must cover both documented diagnosis eras",
        )

    rows = _list(shard.get("rows"), f"shards.{site}.rows")
    if not rows:
        _fail(f"shards.{site}.rows", "must not be empty")
    index = _mapping(shard.get("index"), f"shards.{site}.index")
    expected_index = {}
    for position, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"shards.{site}.rows[{position}]")
        _validate_lookup_row(row, site)
        key = row["key"]
        if key in expected_index:
            _fail(f"shards.{site}.index", f"duplicate key {key}")
        expected_index[key] = position
    if dict(index) != expected_index:
        _fail(f"shards.{site}.index", "must map every row key to its exact position")

    summary = _mapping(shard.get("summary"), f"shards.{site}.summary")
    if summary.get("record_count") != expected_count:
        _fail(f"shards.{site}.summary.record_count", f"must equal {expected_count}")
    if summary.get("row_count") != len(rows):
        _fail(f"shards.{site}.summary.row_count", "must equal the number of rows")
    site_only = [row for row in rows if row.get("matching_level") == "site_only"]
    if len(site_only) != 1 or site_only[0].get("sample_size") != expected_count:
        _fail(f"shards.{site}.site_only.sample_size", "must equal the site record count")


def validate_artifact_set(
    metadata: Mapping[str, Any],
    options: Mapping[str, Any],
    manifest: Mapping[str, Any],
    shards: Mapping[str, Mapping[str, Any]],
    *,
    site_slugs: Mapping[str, str] = SITE_SLUGS,
    expected_eligible_record_count: int = EXPECTED_ELIGIBLE_RECORD_COUNT,
    cohort_version: str = "site_v1",
) -> None:
    _required(metadata, (
        "version", "generated_at", "source_counts", "flow_counts", "exclusion_counts",
        "eligible_record_count", "site_record_counts", "stage_source_policy", "mx_policy",
        "fixed_time_policy", "thresholds",
    ), "metadata")
    if metadata["version"] != 1:
        _fail("metadata.version", "must equal 1")
    if not isinstance(metadata["generated_at"], str) or not metadata["generated_at"].strip():
        _fail("metadata.generated_at", "must be a non-empty string")

    source_counts = _mapping(metadata["source_counts"], "metadata.source_counts")
    expected_sources = {path.name for path in DEFAULT_SOURCE_PATHS}
    if set(source_counts) != expected_sources:
        _fail("metadata.source_counts", "must contain exactly the four configured source files")
    source_total = sum(
        _nonnegative_int(count, f"metadata.source_counts.{name}")
        for name, count in source_counts.items()
    )
    if source_total != EXPECTED_SOURCE_ROW_COUNT:
        _fail("metadata.source_counts", f"must sum to {EXPECTED_SOURCE_ROW_COUNT}")

    flow = _mapping(metadata["flow_counts"], "metadata.flow_counts")
    if flow.get("source_rows") != EXPECTED_SOURCE_ROW_COUNT:
        _fail("metadata.flow_counts.source_rows", f"must equal {EXPECTED_SOURCE_ROW_COUNT}")
    if flow.get("tnm_cohort") != EXPECTED_ELIGIBLE_RECORD_COUNT:
        _fail("metadata.flow_counts.tnm_cohort", f"must equal {EXPECTED_ELIGIBLE_RECORD_COUNT}")
    for field, value in flow.items():
        _nonnegative_int(value, f"metadata.flow_counts.{field}")

    exclusions = _mapping(metadata["exclusion_counts"], "metadata.exclusion_counts")
    flow_exclusions = {field: value for field, value in flow.items() if field.endswith("_excluded")}
    if dict(exclusions) != flow_exclusions:
        _fail("metadata.exclusion_counts", "must equal the exclusion fields in flow_counts")
    if sum(exclusions.values()) + EXPECTED_ELIGIBLE_RECORD_COUNT != EXPECTED_SOURCE_ROW_COUNT:
        _fail("metadata.exclusion_counts", "must partition source rows with the eligible cohort")

    if metadata["eligible_record_count"] != expected_eligible_record_count:
        _fail(
            "metadata.eligible_record_count",
            f"must equal {expected_eligible_record_count}",
        )
    site_counts = _mapping(metadata["site_record_counts"], "metadata.site_record_counts")
    expected_sites = set(site_slugs)
    if set(site_counts) != expected_sites:
        _fail("metadata.site_record_counts", "must contain exactly the configured sites")
    for site, count in site_counts.items():
        _nonnegative_int(count, f"metadata.site_record_counts.{site}")
    if sum(site_counts.values()) != expected_eligible_record_count:
        _fail(
            "metadata.site_record_counts",
            f"must sum to {expected_eligible_record_count}",
        )
    if cohort_version == "site_v1":
        if expected_sites != TARGET_SITES:
            _fail("site_slugs", "site-v1 must use the 13 legacy sites")
        for site, count in EXPECTED_ADDED_SITE_COUNTS.items():
            if site_counts.get(site) != count:
                _fail(f"metadata.site_record_counts.{site}", f"must equal {count}")
    elif cohort_version == "site_v2_main":
        if dict(site_slugs) != SITE_V2_SLUGS:
            _fail("site_slugs", "site-v2 main must use the frozen 10-site mapping")
        if metadata.get("cohort_version") != "site_v2_main":
            _fail("metadata.cohort_version", "must equal site_v2_main")
        if metadata.get("source_eligible_record_count") != EXPECTED_ELIGIBLE_RECORD_COUNT:
            _fail(
                "metadata.source_eligible_record_count",
                f"must equal {EXPECTED_ELIGIBLE_RECORD_COUNT}",
            )
        for site, count in EXPECTED_SITE_V2_MAIN_COUNTS.items():
            if site_counts.get(site) != count:
                _fail(f"metadata.site_record_counts.{site}", f"must equal {count}")
    else:
        _fail("cohort_version", f"unsupported value {cohort_version!r}")

    # Site-v2 metadata is optional for legacy, already-built public artifacts;
    # any newly generated metadata must include and reconcile the full v2 set.
    v2_fields = {
        "site_v2_record_counts",
        "main_analysis_record_count",
        "site_v2_excluded_site_counts",
        "site_v2_mapping_policy",
    }
    if cohort_version == "site_v2_main" or any(field in metadata for field in v2_fields):
        _required(metadata, tuple(v2_fields), "metadata")
        v2_counts = _mapping(metadata["site_v2_record_counts"], "metadata.site_v2_record_counts")
        if set(v2_counts) != set(SITE_V2_ALL_SITES):
            _fail("metadata.site_v2_record_counts", "must contain exactly the 12 site-v2 groups")
        for site, expected in EXPECTED_SITE_V2_RECORD_COUNTS.items():
            count = _nonnegative_int(v2_counts.get(site), f"metadata.site_v2_record_counts.{site}")
            if count != expected:
                _fail(f"metadata.site_v2_record_counts.{site}", f"must equal {expected}")
        if sum(v2_counts.values()) != EXPECTED_ELIGIBLE_RECORD_COUNT:
            _fail("metadata.site_v2_record_counts", f"must sum to {EXPECTED_ELIGIBLE_RECORD_COUNT}")

        main_count = _nonnegative_int(
            metadata["main_analysis_record_count"], "metadata.main_analysis_record_count"
        )
        if main_count != EXPECTED_MAIN_ANALYSIS_RECORD_COUNT:
            _fail("metadata.main_analysis_record_count", f"must equal {EXPECTED_MAIN_ANALYSIS_RECORD_COUNT}")
        excluded = _mapping(
            metadata["site_v2_excluded_site_counts"],
            "metadata.site_v2_excluded_site_counts",
        )
        if set(excluded) != set(SITE_V2_EXCLUDED_SITES):
            _fail("metadata.site_v2_excluded_site_counts", "must contain Nasopharynx and Thyroid")
        for site in SITE_V2_EXCLUDED_SITES:
            excluded_count = _nonnegative_int(
                excluded[site], f"metadata.site_v2_excluded_site_counts.{site}"
            )
            if excluded_count != v2_counts[site]:
                _fail(
                    f"metadata.site_v2_excluded_site_counts.{site}",
                    f"must equal site_v2_record_counts.{site}",
                )
        if sum(excluded.values()) + main_count != EXPECTED_ELIGIBLE_RECORD_COUNT:
            _fail("metadata.site_v2_excluded_site_counts", "must partition the eligible v2 cohort")
        if metadata["site_v2_mapping_policy"] != SITE_V2_MAPPING_POLICY:
            _fail("metadata.site_v2_mapping_policy", "must equal the documented site-v2 mapping policy")

    for field, expected in (
        ("stage_source_policy", STAGE_SOURCE_POLICY),
        ("mx_policy", MX_POLICY),
        ("fixed_time_policy", FIXED_TIME_POLICY),
        ("thresholds", THRESHOLDS),
    ):
        if metadata[field] != expected:
            _fail(f"metadata.{field}", f"must equal the documented policy {expected}")

    _required(options, (
        "version", "sites", "sexes", "histology_groups", "age_groups",
        "t_stages", "n_stages", "m_stages",
    ), "options")
    if options["version"] != 1:
        _fail("options.version", "must equal 1")
    if options["sites"] != list(site_slugs):
        _fail("options.sites", "must contain all configured sites in display order")
    _string_list(options["sexes"], "options.sexes")
    _string_list(options["histology_groups"], "options.histology_groups")
    if options["age_groups"] != _AGE_GROUPS:
        _fail("options.age_groups", f"must equal {_AGE_GROUPS}")
    if options["t_stages"] != _T_STAGES:
        _fail("options.t_stages", f"must equal {_T_STAGES}")
    if options["n_stages"] != _N_STAGES:
        _fail("options.n_stages", f"must equal {_N_STAGES}")
    if options["m_stages"] != _M_STAGES:
        _fail("options.m_stages", f"must equal {_M_STAGES}")

    manifest_sites = _mapping(manifest.get("sites"), "manifest.sites")
    if set(manifest_sites) != expected_sites:
        _fail("manifest.sites", "must contain exactly the configured sites")
    for site, slug in site_slugs.items():
        expected_filename = f"{slug}.json"
        if manifest_sites.get(site) != expected_filename:
            _fail(f"manifest.sites.{site}", f"must equal {expected_filename}")
    if set(shards) != expected_sites:
        _fail("shards", "must contain exactly the configured sites")
    for site in site_slugs:
        _validate_shard(site, shards[site], site_counts[site])

    payload = json.dumps([metadata, options, manifest, shards], ensure_ascii=False, allow_nan=False)
    if '"MX"' in payload:
        _fail("artifacts", "must not contain MX")
    if "summary_stage" in payload.lower():
        _fail("artifacts", "must not contain Summary Stage fields")
