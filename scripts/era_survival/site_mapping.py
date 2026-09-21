"""Central ICD-O-3 primary-site parsing and site-v2 mapping.

The historical ``Site recode ICD-O-3/WHO 2008`` grouping remains site-v1.
This module adds the analysis grouping used by the revised oral/oropharynx
analysis without changing that historical field.
"""

from __future__ import annotations

import re


SITE_V2_ORAL_TONGUE = "Oral Tongue"
SITE_V2_MAIN_SITES = (
    "Lip",
    SITE_V2_ORAL_TONGUE,
    "Gum and Other Mouth",
    "Floor of Mouth",
    "Salivary Gland",
    "Oropharynx",
    "Hypopharynx",
    "Other Oral Cavity and Pharynx",
    "Nose, Nasal Cavity and Middle Ear",
    "Larynx",
)
SITE_V2_SLUGS = {
    "Lip": "lip",
    SITE_V2_ORAL_TONGUE: "oral-tongue",
    "Gum and Other Mouth": "gum-other-mouth",
    "Floor of Mouth": "floor-mouth",
    "Salivary Gland": "salivary-gland",
    "Oropharynx": "oropharynx",
    "Hypopharynx": "hypopharynx",
    "Other Oral Cavity and Pharynx": "other-oral-cavity-pharynx",
    "Nose, Nasal Cavity and Middle Ear": "nose-nasal-cavity-middle-ear",
    "Larynx": "larynx",
}
SITE_V2_ALL_SITES = SITE_V2_MAIN_SITES + ("Nasopharynx", "Thyroid")
SITE_V2_EXCLUDED_SITES = ("Nasopharynx", "Thyroid")

SITE_V2_MAPPING_POLICY = (
    "Primary Site is parsed as a three-digit SEER code or Cxx.x, then mapped "
    "to the revised site-v2 groups: Lip=C00.x; Oral Tongue=C02.0/C02.1/"
    "C02.2/C02.3/C02.8/C02.9; Gum and Other Mouth=C03.x/C05.0/C05.8/"
    "C05.9/C06.x; Floor of Mouth=C04.x; Salivary Gland=C07.x/C08.x; "
    "Oropharynx=C01.9/C02.4/C05.1/C05.2/C09.x/C10.x except C10.1; "
    "Hypopharynx=C12.9/C13.x; Other Oral Cavity and Pharynx=C14.x; "
    "Nose, Nasal Cavity and Middle Ear=C30.x/C31.x; Larynx=C32.x plus "
    "C10.1; Nasopharynx=C11.x; Thyroid=C73.9. Nasopharynx and Thyroid "
    "are retained in site-v2 counts but excluded from the main analysis."
)

_PRIMARY_SITE_RE = re.compile(r"^(?:C)?(?P<prefix>\d{2})(?:\.?)(?P<suffix>\d)$")


def parse_primary_site_code(raw: object) -> str:
    """Return canonical ``Cxx.x`` form for a raw SEER Primary Site code.

    The source exports normally contain values such as ``022``.  Accepting
    canonical ``C02.2`` as well makes fixtures and downstream analysis less
    brittle.  Syntactically valid but unmapped codes are rejected by
    :func:`map_site_v2` rather than silently assigned to a broad group.
    """

    text = "" if raw is None else str(raw).strip().upper()
    if not text:
        raise ValueError("Primary Site is blank")
    match = _PRIMARY_SITE_RE.fullmatch(text)
    if match is None:
        raise ValueError(f"Invalid Primary Site code: {raw!r}")
    return f"C{match['prefix']}.{match['suffix']}"


def map_site_v2(raw: object) -> tuple[str, bool, str]:
    """Map a raw Primary Site value to ``(site_v2, main, canonical_code)``."""

    code = parse_primary_site_code(raw)
    prefix = code[:3]
    if prefix == "C00":
        site = "Lip"
    elif code in {"C02.0", "C02.1", "C02.2", "C02.3", "C02.8", "C02.9"}:
        site = SITE_V2_ORAL_TONGUE
    elif prefix in {"C03", "C06"} or code in {"C05.0", "C05.8", "C05.9"}:
        site = "Gum and Other Mouth"
    elif prefix == "C04":
        site = "Floor of Mouth"
    elif prefix in {"C07", "C08"}:
        site = "Salivary Gland"
    elif code == "C01.9" or code == "C02.4" or code in {"C05.1", "C05.2"}:
        site = "Oropharynx"
    elif prefix == "C09" or (prefix == "C10" and code != "C10.1"):
        site = "Oropharynx"
    elif code == "C10.1" or prefix == "C32":
        site = "Larynx"
    elif code == "C12.9" or prefix == "C13":
        site = "Hypopharynx"
    elif prefix == "C14":
        site = "Other Oral Cavity and Pharynx"
    elif prefix in {"C30", "C31"}:
        site = "Nose, Nasal Cavity and Middle Ear"
    elif prefix == "C11":
        site = "Nasopharynx"
    elif code == "C73.9":
        site = "Thyroid"
    else:
        raise ValueError(f"Unmapped Primary Site code: {code}")
    return site, site not in SITE_V2_EXCLUDED_SITES, code
