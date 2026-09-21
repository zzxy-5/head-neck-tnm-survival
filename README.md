# SEER Detailed TNM Survival Lookup

This static website provides retrospective, subgroup-level overall survival
estimates for the frozen 10-site `site_v2` main-analysis cohort. It uses a
single detailed TNM cohort of diagnoses from 2010 through 2017.

## Data scope

The build reads four SEER exports from the parent workspace:

- `/Volumes/PortableSSD/prediction/export_C00-C09.csv`
- `/Volumes/PortableSSD/prediction/export_C10-C14.csv`
- `/Volumes/PortableSSD/prediction/export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv`
- `/Volumes/PortableSSD/prediction/export_C73-C75.csv`

The 1,808,471 source rows first yield 211,160 TNM-eligible records. The frozen
main-analysis definition excludes the prespecified nasopharynx and thyroid
groups and contains exactly 106,952 records across 10 `site_v2` groups:

| Site | Eligible records |
| --- | ---: |
| Lip | 5,065 |
| Oral Tongue | 12,233 |
| Gum and Other Mouth | 9,444 |
| Floor of Mouth | 3,605 |
| Salivary Gland | 9,282 |
| Oropharynx | 34,483 |
| Hypopharynx | 4,209 |
| Other Oral Cavity and Pharynx | 1,740 |
| Nose, Nasal Cavity and Middle Ear | 4,969 |
| Larynx | 21,922 |
| **Total** | **106,952** |

## Methods

- Diagnoses from 2010-2015 use Derived AJCC 7th edition T/N/M fields.
- Diagnoses from 2016-2017 use Derived SEER Combined T/N/M fields.
- T categories are `T0`-`T4` or `Unknown`; N categories are `N0`-`N3` or
  `Unknown`; M categories are `M0`, `M1`, or `Unknown`.
- Raw `MX` is normalized to `M0` before lookup keys and website artifacts are
  created. It is never exposed in the interface.
- Kaplan-Meier fixed 1-, 3-, and 5-year estimates include Greenwood log-log
  95% confidence intervals when observed follow-up supports that horizon.
  The curve is not extrapolated and has no confidence-interval shading.
- Median follow-up is estimated with reverse Kaplan-Meier and is reported as
  not reached when the reverse curve does not cross 50%.
- The public minimum is 20 records. The browser tries the ordered 11-level
  fallback and skips groups below that threshold.

The query dimensions are sex, anatomical site, histology group, age, T, N, and
M. The fallback order is: exact match; sex omitted; broader age with sex
omitted; age and sex omitted; site/histology/M; site/histology; histology
omitted; histology omitted with broader age; site/TNM; site/M; and site only.
These estimates are for research reference, not individualized clinical
prediction or standalone clinical decision support.

## Static data architecture

`public/data/` contains three shared files and one lazy-loaded lookup shard per
site:

- `metadata.json`: source provenance, cohort flow, record counts, policies,
  and thresholds.
- `options.json`: shared filter choices, including all 10 `site_v2` sites.
- `site_manifest.json`: site-to-shard map.
- `lookup/<site>.json`: site-local rows and lookup index.

The application loads shared data first, then fetches and caches only the
selected site shard. The generated artifact contract rejects unsupported stage
fields and raw `MX` values.

## Commands

Install frontend dependencies and run the website checks:

```bash
npm install
npm test
npm run build
npm run dev -- --port 4174
```

The development server is available at `http://127.0.0.1:4174/` while running.

Run the complete Python suite:

```bash
PYTHONPATH=scripts python3 -m unittest discover -s tests/python -p 'test_*.py'
```

Rebuild static artifacts from all four exports:

```bash
PYTHONPATH=scripts python3 scripts/build_artifacts.py \
  --site-v2-main \
  --input /Volumes/PortableSSD/prediction/export_C00-C09.csv \
  --input /Volumes/PortableSSD/prediction/export_C10-C14.csv \
  --input /Volumes/PortableSSD/prediction/export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv \
  --input /Volumes/PortableSSD/prediction/export_C73-C75.csv
```

The project intentionally has no paper-generation command or generated paper
outputs. Git staging and commits are left to the user.
