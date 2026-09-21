from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_PATHS = (
    PROJECT_ROOT.parent / "export_C00-C09.csv",
    PROJECT_ROOT.parent / "export_C10-C14.csv",
    PROJECT_ROOT.parent / "export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv",
    PROJECT_ROOT.parent / "export_C73-C75.csv",
)
PUBLIC_DATA_DIR = PROJECT_ROOT / "public" / "data"

TARGET_SITES = frozenset({
    "Lip", "Tongue", "Gum and Other Mouth", "Floor of Mouth",
    "Salivary Gland", "Tonsil", "Oropharynx", "Nasopharynx",
    "Hypopharynx", "Other Oral Cavity and Pharynx",
    "Nose, Nasal Cavity and Middle Ear", "Larynx", "Thyroid",
})

SITE_SLUGS = {
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
}

SOURCE_COLUMNS = {
    "sex": "Sex",
    "year": "Year of diagnosis",
    "site": "Site recode ICD-O-3/WHO 2008",
    "histology": "Histology recode - broad groupings",
    "age": "Age recode with single ages and 90+",
    "survival_months": "Survival months",
    "vital_status": "Vital status recode (study cutoff used)",
    "ajcc_t": "Derived AJCC T, 7th ed (2010-2015)",
    "ajcc_n": "Derived AJCC N, 7th ed (2010-2015)",
    "ajcc_m": "Derived AJCC M, 7th ed (2010-2015)",
    "ajcc_m_6": "Derived AJCC M, 6th ed (2004-2015)",
    "combined_t": "Derived SEER Combined T (2016-2017)",
    "combined_n": "Derived SEER Combined N (2016-2017)",
    "combined_m": "Derived SEER Combined M (2016-2017)",
    "primary_site": "Primary Site",
}

@dataclass(frozen=True)
class TNMRecord:
    year: int
    sex: str
    site: str
    histology_group: str
    age_group: str
    coarse_age_group: str
    survival_months: int
    event: bool
    t_stage: str
    n_stage: str
    m_stage: str
    stage_source: str
    # ``site`` remains the site-v1 compatibility field.  These defaults keep
    # legacy positional fixtures valid while normalized real rows populate all
    # three site-v2 fields.
    site_v1: str | None = field(default=None, compare=False)
    site_v2: str | None = field(default=None, compare=False)
    main_analysis_included: bool | None = field(default=None, compare=False)
