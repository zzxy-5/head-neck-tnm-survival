from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from .csv_source import CsvSource
from .normalization import normalize_tnm_record, parse_year
from .schema import SOURCE_COLUMNS, TARGET_SITES, TNMRecord


@dataclass(frozen=True)
class CohortBundle:
    records: list[TNMRecord]
    flow_counts: dict[str, int]
    source_counts: dict[str, int]


def _classify_exclusion(error: ValueError) -> str:
    message = str(error).lower()
    if "sex" in message:
        return "invalid_sex_excluded"
    if "histology" in message:
        return "invalid_histology_excluded"
    if "survival months" in message:
        return "invalid_survival_excluded"
    if "age recode" in message:
        return "invalid_age_excluded"
    if "vital status" in message:
        return "invalid_outcome_excluded"
    if "diagnosis year" in message:
        return "invalid_year_excluded"
    return "invalid_record_excluded"


def load_cohort(paths: Sequence[Path]) -> CohortBundle:
    source = CsvSource(paths, tuple(SOURCE_COLUMNS.values()))
    records: list[TNMRecord] = []
    flow = Counter()

    for row in source.rows():
        flow["source_rows"] += 1
        if row[SOURCE_COLUMNS["site"]].strip() not in TARGET_SITES:
            flow["non_target_site_excluded"] += 1
            continue

        try:
            year = parse_year(row[SOURCE_COLUMNS["year"]])
        except (TypeError, ValueError):
            flow["invalid_year_excluded"] += 1
            continue

        if not 2010 <= year <= 2017:
            flow["outside_tnm_years_excluded"] += 1
            continue

        try:
            records.append(normalize_tnm_record(row))
        except ValueError as error:
            flow[_classify_exclusion(error)] += 1

    flow["tnm_cohort"] = len(records)
    return CohortBundle(
        records=records,
        flow_counts=dict(flow),
        source_counts=dict(source.source_counts),
    )
