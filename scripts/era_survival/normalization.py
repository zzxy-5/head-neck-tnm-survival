from __future__ import annotations

import re
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from .schema import SOURCE_COLUMNS, TNMRecord

UNKNOWN_INPUTS = {"", "Blank(s)", "N/A", "Not applicable", "Unknown", "88", "99"}
AGE_RECODE_PATTERN = re.compile(r"(?P<age>\d+)(?:\+)? years")
AJCC_T = SOURCE_COLUMNS["ajcc_t"]
AJCC_N = SOURCE_COLUMNS["ajcc_n"]
AJCC_M = SOURCE_COLUMNS["ajcc_m"]
COMBINED_T = SOURCE_COLUMNS["combined_t"]
COMBINED_N = SOURCE_COLUMNS["combined_n"]
COMBINED_M = SOURCE_COLUMNS["combined_m"]


def parse_year(raw: str) -> int:
    year = int(str(raw).strip())
    if not 1900 <= year <= 2100:
        raise ValueError(f"Invalid diagnosis year: {raw}")
    return year


def parse_survival_months(raw: str) -> int:
    text = str(raw).strip()
    if not text:
        raise ValueError("Survival months is blank")
    try:
        months = Decimal(text)
    except InvalidOperation as error:
        raise ValueError(f"Invalid survival months: {raw}") from error
    if not months.is_finite():
        raise ValueError(f"Survival months must be finite: {raw}")
    if months < 0:
        raise ValueError(f"Survival months must be non-negative: {raw}")
    if months != months.to_integral_value():
        raise ValueError(f"Survival months must be an integer: {raw}")
    return int(months)


def parse_event(raw: str) -> bool:
    text = str(raw).strip()
    if text == "Dead":
        return True
    if text == "Alive":
        return False
    raise ValueError(f"Unsupported vital status: {raw}")


def _normalize_categorical(raw: str, field: str) -> str:
    text = str(raw).strip()
    if not text:
        raise ValueError(f"{field} is blank")
    return text


def age_groups(raw: str) -> tuple[str, str]:
    text = str(raw).strip()
    match = AGE_RECODE_PATTERN.fullmatch(text)
    if match is None:
        raise ValueError(f"Invalid age recode: {raw}")
    age = int(match["age"])
    if not 0 <= age <= 90:
        raise ValueError(f"Invalid age recode: {raw}")

    fine = (
        "<40" if age < 40 else "40-49" if age < 50 else "50-59" if age < 60
        else "60-69" if age < 70 else "70-79" if age < 80 else "80+"
    )
    coarse = "<60" if age < 60 else "60-69" if age < 70 else "70+"
    return fine, coarse


def _normalize_stage(raw: str, letter: str, valid_stages: set[str]) -> str:
    text = str(raw).strip().upper().replace(" ", "")
    if text in UNKNOWN_INPUTS:
        return "Unknown"
    text = re.sub(r"^[CPY]+", "", text)
    if text.startswith(letter):
        text = text[1:]
    stage = f"{letter}{text[0]}" if text else ""
    return stage if stage in valid_stages else "Unknown"


def normalize_t_stage(raw: str) -> str:
    return _normalize_stage(raw, "T", {"T0", "T1", "T2", "T3", "T4"})


def normalize_n_stage(raw: str) -> str:
    return _normalize_stage(raw, "N", {"N0", "N1", "N2", "N3"})


def normalize_m_stage(raw: str) -> str:
    text = str(raw).strip().upper().replace(" ", "")
    if text == "MX":
        return "M0"
    return _normalize_stage(text, "M", {"M0", "M1"})


def choose_tnm_source(row: Mapping[str, str], year: int) -> tuple[str, str, str, str]:
    if 2010 <= year <= 2015:
        return row[AJCC_T], row[AJCC_N], row[AJCC_M], "AJCC 7th edition"
    if 2016 <= year <= 2017:
        return row[COMBINED_T], row[COMBINED_N], row[COMBINED_M], "SEER Combined TNM"
    raise ValueError(f"Diagnosis year outside TNM cohort: {year}")


def _survival_record_fields(row: Mapping[str, str], year: int) -> dict[str, object]:
    age_group, coarse_age_group = age_groups(row[SOURCE_COLUMNS["age"]])
    return {
        "year": year,
        "sex": _normalize_categorical(row[SOURCE_COLUMNS["sex"]], "Sex"),
        "site": row[SOURCE_COLUMNS["site"]],
        "histology_group": _normalize_categorical(
            row[SOURCE_COLUMNS["histology"]], "Histology"
        ),
        "age_group": age_group,
        "coarse_age_group": coarse_age_group,
        "survival_months": parse_survival_months(row[SOURCE_COLUMNS["survival_months"]]),
        "event": parse_event(row[SOURCE_COLUMNS["vital_status"]]),
    }


def normalize_tnm_record(row: Mapping[str, str]) -> TNMRecord:
    year = parse_year(row[SOURCE_COLUMNS["year"]])
    raw_t_stage, raw_n_stage, raw_m_stage, stage_source = choose_tnm_source(row, year)
    return TNMRecord(
        **_survival_record_fields(row, year),
        t_stage=normalize_t_stage(raw_t_stage),
        n_stage=normalize_n_stage(raw_n_stage),
        m_stage=normalize_m_stage(raw_m_stage),
        stage_source=stage_source,
    )
