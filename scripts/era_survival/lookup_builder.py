from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .km import FIXED_HORIZONS, KMResult, kaplan_meier
from .schema import SITE_SLUGS, TNMRecord

ANY_VALUE = "Any"
TNM_COHORT_TYPE = "tnm_2010_2017"
THRESHOLDS = {"minimum_sample": 20, "stable_sample": 50}
CONFIDENCE_INTERVAL = {"level": 0.95, "method": "Greenwood log-log"}
STAGE_SOURCE_BY_YEAR = {
    **{year: "AJCC 7th edition" for year in range(2010, 2016)},
    **{year: "SEER Combined TNM" for year in range(2016, 2018)},
}

TNM_MATCHING_LEVELS = (
    "full",
    "no_sex",
    "site_histology_coarse_age",
    "site_histology_tnm",
    "site_histology_m",
    "site_histology",
    "no_histology",
    "coarse_age",
    "site_tnm",
    "site_m",
    "site_only",
)


def _value(query: object, field: str) -> str:
    if isinstance(query, Mapping):
        return str(query[field])
    return str(getattr(query, field))


def _key(*segments: str) -> str:
    return "|".join(segments)


def tnm_key_candidates(query: object) -> list[str]:
    sex = _value(query, "sex")
    site = _value(query, "site")
    histology = _value(query, "histology_group")
    age = _value(query, "age_group")
    coarse_age = _value(query, "coarse_age_group")
    t_stage = _value(query, "t_stage")
    n_stage = _value(query, "n_stage")
    m_stage = _value(query, "m_stage")
    return [
        _key("full", sex, site, histology, age, t_stage, n_stage, m_stage),
        _key("no_sex", ANY_VALUE, site, histology, age, t_stage, n_stage, m_stage),
        _key(
            "site_histology_coarse_age",
            ANY_VALUE,
            site,
            histology,
            coarse_age,
            t_stage,
            n_stage,
            m_stage,
        ),
        _key(
            "site_histology_tnm",
            ANY_VALUE,
            site,
            histology,
            ANY_VALUE,
            t_stage,
            n_stage,
            m_stage,
        ),
        _key(
            "site_histology_m",
            ANY_VALUE,
            site,
            histology,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
            m_stage,
        ),
        _key(
            "site_histology",
            ANY_VALUE,
            site,
            histology,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
        ),
        _key(
            "no_histology",
            ANY_VALUE,
            site,
            ANY_VALUE,
            age,
            t_stage,
            n_stage,
            m_stage,
        ),
        _key(
            "coarse_age",
            ANY_VALUE,
            site,
            ANY_VALUE,
            coarse_age,
            t_stage,
            n_stage,
            m_stage,
        ),
        _key("site_tnm", ANY_VALUE, site, ANY_VALUE, ANY_VALUE, t_stage, n_stage, m_stage),
        _key("site_m", ANY_VALUE, site, ANY_VALUE, ANY_VALUE, ANY_VALUE, ANY_VALUE, m_stage),
        _key(
            "site_only",
            ANY_VALUE,
            site,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
            ANY_VALUE,
        ),
    ]


def _quality(sample_size: int) -> str:
    if sample_size >= THRESHOLDS["stable_sample"]:
        return "stable"
    if sample_size >= THRESHOLDS["minimum_sample"]:
        return "small_sample"
    return "very_small_sample"


def _survival_fields(km: KMResult) -> dict[str, Any]:
    return {
        "sample_size": km.sample_size,
        "event_count": km.event_count,
        "censor_count": km.censor_count,
        "median_survival_months": km.median_survival_months,
        "median_followup_months": km.median_followup_months,
        "maximum_followup_months": km.maximum_followup_months,
        "fixed_survival": {
            str(month): km.fixed[month].to_dict()
            for month in FIXED_HORIZONS
        },
        "curve_months": km.curve_months,
        "curve_survival_probs": km.curve_survival_probs,
        "censor_months": km.censor_months,
        "risk_table_months": km.risk_table_months,
        "risk_table_counts": km.risk_table_counts,
        "data_quality_flag": _quality(km.sample_size),
    }


def _validate_normalized_records(records: Sequence[TNMRecord]) -> None:
    if any(record.m_stage == "MX" for record in records):
        raise ValueError("TNM records must use normalized M0 instead of MX")
    for record in records:
        expected_source = STAGE_SOURCE_BY_YEAR.get(record.year)
        if expected_source is None:
            raise ValueError(
                f"TNM record year {record.year} is outside the 2010-2017 cohort"
            )
        if record.stage_source != expected_source:
            raise ValueError(
                f"TNM record year {record.year} has stage source "
                f"{record.stage_source!r}; expected {expected_source!r}"
            )


def build_site_artifact(
    site: str,
    records: Sequence[TNMRecord],
    *,
    site_slugs: Mapping[str, str] = SITE_SLUGS,
) -> dict[str, Any]:
    """Build one site-scoped artifact using the production TNM logic.

    ``site_slugs`` defaults to the deployed v1 mapping.  Analysis-only
    rebuilds may pass an explicit alternative mapping without mutating the
    production constant or changing any matching, KM, or serialization rule.
    """

    if site not in site_slugs:
        raise ValueError(f"Unsupported TNM site: {site}")
    if any(record.site != site for record in records):
        raise ValueError(f"Site artifact for {site} received records from another site")
    _validate_normalized_records(records)

    grouped: dict[str, list[tuple[int, bool]]] = defaultdict(list)
    grouped_sources: dict[str, set[str]] = defaultdict(set)
    for record in records:
        observation = (record.survival_months, record.event)
        for key in tnm_key_candidates(record):
            grouped[key].append(observation)
            grouped_sources[key].add(record.stage_source)

    rows = []
    for key, observations in grouped.items():
        matching_level, sex, row_site, histology, age, t_stage, n_stage, m_stage = key.split("|")
        rows.append({
            "key": key,
            "cohort_type": TNM_COHORT_TYPE,
            "stage_source": "; ".join(sorted(grouped_sources[key])),
            "matching_level": matching_level,
            "sex": sex,
            "site": row_site,
            "histology_group": histology,
            "age_group": age,
            "t_stage": t_stage,
            "n_stage": n_stage,
            "m_stage": m_stage,
            **_survival_fields(kaplan_meier(observations)),
        })

    rank = {level: position for position, level in enumerate(TNM_MATCHING_LEVELS)}
    rows.sort(key=lambda row: (rank[row["matching_level"]], -row["sample_size"], row["key"]))
    return {
        "version": 1,
        "site": site,
        "cohort_type": TNM_COHORT_TYPE,
        "cohort_years": [2010, 2017],
        "stage_sources": sorted({record.stage_source for record in records}),
        "thresholds": dict(THRESHOLDS),
        "confidence_interval": dict(CONFIDENCE_INTERVAL),
        "rows": rows,
        "index": {row["key"]: position for position, row in enumerate(rows)},
        "summary": {
            "record_count": len(records),
            "row_count": len(rows),
            "sexes": sorted({record.sex for record in records}),
            "histology_groups": sorted({record.histology_group for record in records}),
        },
    }


def build_site_shards(
    records: Sequence[TNMRecord],
    *,
    site_slugs: Mapping[str, str] = SITE_SLUGS,
) -> tuple[dict[str, dict], dict]:
    _validate_normalized_records(records)
    records_by_site: dict[str, list[TNMRecord]] = defaultdict(list)
    for record in records:
        if record.site not in site_slugs:
            raise ValueError(f"Unsupported TNM site: {record.site}")
        records_by_site[record.site].append(record)

    sites = [site for site in site_slugs if site in records_by_site]
    shards = {
        site: build_site_artifact(site, records_by_site[site], site_slugs=site_slugs)
        for site in sites
    }
    return shards, {"sites": {site: f"{site_slugs[site]}.json" for site in sites}}
