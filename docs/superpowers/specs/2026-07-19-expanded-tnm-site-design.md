# Expanded 2010-2017 TNM Survival Website Design

Date: 2026-07-19

## Objective

Replace the isolated project's current Summary Stage plus TNM interface with a
single detailed TNM survival lookup modeled on the existing website at
`http://127.0.0.1:5173/`. The original website remains unchanged. The new
website uses the four SEER CSV exports and adds nasal cavity/middle ear/paranasal
sinus, larynx, and thyroid malignancies to the ten existing oral cavity and
pharyngeal site groups.

## Source Data and Scope

The build reads these four files from the parent workspace:

- `export_C00-C09.csv`
- `export_C10-C14.csv`
- `export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv`
- `export_C73-C75.csv`

Only diagnoses from 2010 through 2017 are eligible. The included anatomical
site groups are:

1. Lip
2. Tongue
3. Gum and Other Mouth
4. Floor of Mouth
5. Salivary Gland
6. Tonsil
7. Oropharynx
8. Nasopharynx
9. Hypopharynx
10. Other Oral Cavity and Pharynx
11. Nose, Nasal Cavity and Middle Ear
12. Larynx
13. Thyroid

All other records in the broad C30-C39 and C73-C75 exports, including lung,
bronchus, pleura, thymus, adrenal, lymphoma, and other non-target recodes, are
excluded before normalization.

## Verified Record Counts

Website eligibility requires a target site, a diagnosis year from 2010 through
2017, parseable age and survival months, a supported vital status, and nonblank
sex and histology. Unknown T or N remains eligible for website lookup.

| Site | Eligible records | T/N known |
| --- | ---: | ---: |
| Floor of Mouth | 3,605 | 3,569 |
| Gum and Other Mouth | 10,947 | 10,763 |
| Hypopharynx | 4,209 | 4,186 |
| Larynx | 21,786 | 21,589 |
| Lip | 5,065 | 4,873 |
| Nasopharynx | 4,493 | 4,429 |
| Nose, Nasal Cavity and Middle Ear | 4,969 | 4,582 |
| Oropharynx | 3,451 | 3,381 |
| Other Oral Cavity and Pharynx | 1,740 | 1,265 |
| Salivary Gland | 9,282 | 9,122 |
| Thyroid | 99,715 | 99,171 |
| Tongue | 26,135 | 25,890 |
| Tonsil | 15,763 | 15,651 |
| **Total** | **211,160** | **208,471** |

The three added site groups contribute 126,470 eligible records. Invalid
survival months exclude 22 nasal cavity/middle ear/paranasal sinus records, 173
larynx records, and 278 thyroid records.

## TNM Normalization

- Diagnoses from 2010-2015 use Derived AJCC T/N/M, 7th edition.
- Diagnoses from 2016-2017 use Derived SEER Combined T/N/M.
- T is normalized to T0, T1, T2, T3, T4, or Unknown.
- N is normalized to N0, N1, N2, N3, or Unknown.
- M is normalized to M0, M1, or Unknown.
- Every raw MX value is converted to M0 at the normalization boundary. MX is
  never emitted in options, lookup keys, rows, metadata, or visible results.
- Unknown T or N is retained as an explicit website category and is not treated
  as stage-era absence.

Age is derived from `Age recode with single ages and 90+` and grouped as `<40`,
`40-49`, `50-59`, `60-69`, `70-79`, and `80+`. The website accepts a numeric
age and derives the matching age group in the browser, matching the original
website interaction.

## Lookup Method

The query dimensions are sex, anatomical site, broad histology group, age,
T, N, and M. The lookup uses the original website's ordered 11-level fallback:

1. Full match
2. Sex omitted
3. Broader age group with sex omitted
4. Age and sex omitted
5. Site, histology, and M only
6. Site and histology only
7. Histology omitted
8. Histology omitted with broader age group
9. Site and TNM only
10. Site and M only
11. Site only

Groups with fewer than 20 records do not return a formal survival estimate.
Groups with 20-49 records are marked small sample; groups with at least 50 are
marked relatively stable.

## Survival Estimation

Overall survival is estimated offline with Kaplan-Meier methods. The artifacts
store sample size, events, censoring, median survival, median follow-up, fixed
12-, 36-, and 60-month estimates, number at risk, censor markers, and the KM
step curve.

Greenwood log-log 95% confidence intervals are calculated for the three fixed
time estimates and displayed as text inside their result tiles. Confidence
bands and confidence-bound curves are not rendered. A fixed-time result is
reported as not estimable when observed follow-up does not support that horizon;
the last earlier KM value must not be carried forward as a 3- or 5-year result.

## Static Artifact Architecture

The application remains a backend-free static website. To avoid loading one
large lookup file, generated data is split by site:

- `metadata.json` records sources, policies, exclusions, and reconciliation
  counts.
- `options.json` lists the 13 sites and shared filter choices.
- A manifest maps each site to one JSON lookup shard.
- `lookup/<site>.json` contains lookup rows and an index for that site only.

The browser loads metadata and options initially, then loads and caches the
selected site's shard. Changing sex, histology, age, or TNM does not refetch the
site shard. This internal change does not alter the original website's visible
query behavior.

## Interface

The new interface follows the original website at `http://127.0.0.1:5173/` for
its overall layout, visual language, controls, result tiles, fallback
explanation, and responsive behavior. Chinese is the default language and a
Chinese/English switch remains available without persistence.

There is one detailed TNM query screen. Summary Stage, EOD descriptive output,
cohort tabs, and era comparison UI are removed. The KM visualization uses the
larger, clearer chart styling from the current project at
`http://127.0.0.1:4174/`, while removing its confidence polygon entirely. The
chart displays the KM step line, axes, grid, and supported follow-up range; it
does not display confidence shading or confidence-bound curves. The separate
table immediately below the chart is retained and reports the number at risk at
0, 12, 24, 36, 48, and 60 months. On narrow screens, only this table may scroll
horizontally.

## Validation and Testing

The build must fail if required columns are absent, target-site counts do not
reconcile, non-target sites enter the cohort, 2016-2017 rows use the wrong TNM
source, or MX survives normalization. Real-artifact contract tests assert the
13 sites, 211,160 eligible records, the three added-site counts, and absence of
Summary Stage and MX from website artifacts.

Python tests cover source filtering, age/TNM normalization, MX-to-M0 mapping,
Kaplan-Meier estimates, fixed-horizon estimability, fallback construction,
shard generation, and validation. Frontend tests cover site-shard loading and
caching, the 11-level fallback, bilingual presentation, confidence intervals in
tiles, the 4174 chart styling without a confidence polygon, the retained risk
table, empty/error states, and mobile layout.

Final verification includes the full Python and frontend suites, a production
build, artifact reconciliation, `git diff --check`, and desktop/mobile browser
QA. Progress and README documentation are updated. No Git staging or commit is
performed; the user will commit manually.
