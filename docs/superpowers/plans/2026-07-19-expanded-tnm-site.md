# Expanded 2010-2017 TNM Survival Website Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the isolated dual-cohort website with a single 2010-2017 detailed TNM lookup covering 13 anatomical sites and 211,160 eligible SEER records.

**Architecture:** Stream four SEER CSV files into one normalized TNM record model, build the original website's ordered 11-level fallback groups, and emit one static lookup shard per anatomical site. The React application loads shared options/metadata once, lazily caches site shards, uses the original `5173` page layout and query interaction, and uses the larger `4174` KM chart plus its separate risk table without any confidence polygon.

**Tech Stack:** Python 3 standard library, React 19, TypeScript, Vite, Vitest, Testing Library, static JSON artifacts.

## Global Constraints

- Work only in `/Volumes/PortableSSD/prediction/.worktrees/seer-era-survival-atlas/seer-era-survival-atlas`; do not modify the original website in `/Volumes/PortableSSD/prediction`.
- Include diagnoses from 2010 through 2017 only.
- Use AJCC 7 T/N/M for 2010-2015 and SEER Combined T/N/M for 2016-2017.
- Convert every raw `MX` to `M0` before lookup keys are created; never expose `MX` in artifacts or UI.
- Retain unknown T/N as explicit website categories.
- Include exactly the 13 sites and 211,160 eligible records listed in the approved design.
- Do not create Summary Stage, EOD, paper-output, or era-comparison artifacts or UI.
- Display fixed-time Greenwood log-log 95% confidence intervals in result tiles only.
- Do not render a chart confidence polygon, band, or confidence-bound line.
- Retain the separate 0/12/24/36/48/60-month number-at-risk table below the chart.
- Default to Chinese and retain a nonpersistent Chinese/English switch.
- Do not run `git add` or `git commit`; update `progress.md` after completed tasks and leave final submission to the user.

---

### Task 1: Focus the schema and normalization on the 13-site TNM cohort

**Files:**
- Modify: `scripts/era_survival/schema.py`
- Modify: `scripts/era_survival/normalization.py`
- Modify: `tests/python/test_schema.py`
- Modify: `tests/python/test_normalization.py`

**Interfaces:**
- Produces: `TARGET_SITES`, `SITE_SLUGS`, `DEFAULT_SOURCE_PATHS`, `SOURCE_COLUMNS`, and `TNMRecord`.
- Produces: `normalize_tnm_record(row: Mapping[str, str]) -> TNMRecord`.
- Consumed by: cohort filtering, shard construction, metadata validation, and frontend manifest generation.

- [ ] **Step 1: Write failing schema tests for four inputs and 13 sites**

```python
def test_four_sources_and_thirteen_target_sites(self):
    self.assertEqual(len(DEFAULT_SOURCE_PATHS), 4)
    self.assertEqual(len(TARGET_SITES), 13)
    self.assertEqual(SITE_SLUGS["Larynx"], "larynx")
    self.assertEqual(SITE_SLUGS["Thyroid"], "thyroid")
    self.assertIn("Nose, Nasal Cavity and Middle Ear", TARGET_SITES)
```

- [ ] **Step 2: Write failing normalization tests for stage era, age, and MX**

```python
def test_2017_combined_tnm_and_mx_maps_to_m0(self):
    row = self.make_row(year="2017", combined_t="cT3", combined_n="cN2b", combined_m="MX")
    record = normalize_tnm_record(row)
    self.assertEqual((record.t_stage, record.n_stage, record.m_stage), ("T3", "N2", "M0"))
    self.assertEqual(record.stage_source, "SEER Combined TNM")

def test_single_age_recode_supports_90_plus(self):
    row = self.make_row(age="90+ years")
    self.assertEqual(normalize_tnm_record(row).age_group, "80+")
```

- [ ] **Step 3: Run the focused tests and confirm they fail**

Run:

```bash
PYTHONPATH=scripts python3 -m unittest tests.python.test_schema tests.python.test_normalization -v
```

Expected: failures for missing `TARGET_SITES`, the two new source paths, and `MX` still normalizing as unknown.

- [ ] **Step 4: Implement the focused schema**

Define four source paths, the exact target set, deterministic slugs, and only the columns needed by the detailed TNM pipeline:

```python
TARGET_SITES = frozenset({
    "Lip", "Tongue", "Gum and Other Mouth", "Floor of Mouth",
    "Salivary Gland", "Tonsil", "Oropharynx", "Nasopharynx",
    "Hypopharynx", "Other Oral Cavity and Pharynx",
    "Nose, Nasal Cavity and Middle Ear", "Larynx", "Thyroid",
})

DEFAULT_SOURCE_PATHS = (
    PROJECT_ROOT.parents[2] / "export_C00-C09.csv",
    PROJECT_ROOT.parents[2] / "export_C10-C14.csv",
    PROJECT_ROOT.parents[2] / "export_C30-C39呼吸和胸腔内器官恶性肿瘤.csv",
    PROJECT_ROOT.parents[2] / "export_C73-C75.csv",
)
```

Here `PROJECT_ROOT.parents[2]` resolves from the nested project through the
worktree directories to `/Volumes/PortableSSD/prediction`, where the CSV files
actually live. Use `Age recode with single ages and 90+` as the source age
field. Remove Summary and EOD fields and record types from this focused schema.

- [ ] **Step 5: Implement normalization at the source boundary**

```python
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
```

Parse the leading integer from values such as `63 years`, treat `90+ years` as age 90, derive fine/coarse age groups, and preserve T/N unknown values as `Unknown`.

- [ ] **Step 6: Run focused tests and update progress**

Run the Step 3 command. Expected: all schema and normalization tests pass. Add the completed task and test result to `progress.md` without staging or committing.

---

### Task 2: Build and reconcile the 2010-2017 cohort

**Files:**
- Modify: `scripts/era_survival/cohorts.py`
- Modify: `scripts/era_survival/csv_source.py`
- Modify: `tests/python/test_cohorts.py`
- Modify: `tests/python/test_csv_source.py`

**Interfaces:**
- Consumes: `TARGET_SITES`, `SOURCE_COLUMNS`, `normalize_tnm_record`.
- Produces: `CohortBundle(records: list[TNMRecord], flow_counts: dict[str, int], source_counts: dict[str, int])`.
- Produces: `load_cohort(paths: Sequence[Path]) -> CohortBundle`.

- [ ] **Step 1: Write failing cohort tests for target-site and year filtering**

```python
def test_only_target_sites_and_2010_2017_enter_cohort(self):
    rows = [
        self.make_row(site="Larynx", year="2010"),
        self.make_row(site="Thyroid", year="2017"),
        self.make_row(site="Lung and Bronchus", year="2015"),
        self.make_row(site="Larynx", year="2018"),
    ]
    bundle = self.load_rows(rows)
    self.assertEqual([record.site for record in bundle.records], ["Larynx", "Thyroid"])
    self.assertEqual(bundle.flow_counts["non_target_site_excluded"], 1)
    self.assertEqual(bundle.flow_counts["outside_tnm_years_excluded"], 1)
```

- [ ] **Step 2: Write failing tests for exclusion reason accounting**

Assert blank/invalid survival months are counted separately from invalid age, outcome, and year, and assert source-file counts sum to `source_rows`.

- [ ] **Step 3: Run tests and confirm the old multi-cohort API fails**

```bash
PYTHONPATH=scripts python3 -m unittest tests.python.test_csv_source tests.python.test_cohorts -v
```

Expected: failures because `CohortBundle` still exposes Summary/EOD branches and does not use the four-source target-site contract.

- [ ] **Step 4: Implement a single-pass focused cohort loader**

```python
for row in CsvSource(paths, tuple(SOURCE_COLUMNS.values())).rows():
    flow["source_rows"] += 1
    if row[SOURCE_COLUMNS["site"]].strip() not in TARGET_SITES:
        flow["non_target_site_excluded"] += 1
        continue
    year = parse_year(row[SOURCE_COLUMNS["year"]])
    if not 2010 <= year <= 2017:
        flow["outside_tnm_years_excluded"] += 1
        continue
    try:
        records.append(normalize_tnm_record(row))
    except ValueError as error:
        flow[classify_exclusion(error)] += 1
```

Do not retain raw rows and do not construct Summary/EOD branches.

- [ ] **Step 5: Run tests and update progress**

Run the Step 3 command. Expected: all cohort and CSV source tests pass. Record completion in `progress.md`.

---

### Task 3: Implement the 11-level lookup and site shards

**Files:**
- Modify: `scripts/era_survival/lookup_builder.py`
- Modify: `scripts/era_survival/km.py`
- Modify: `tests/python/test_lookup_builder.py`
- Modify: `tests/python/test_km.py`

**Interfaces:**
- Consumes: `TNMRecord` and `SITE_SLUGS`.
- Produces: `tnm_key_candidates(record_or_query: object) -> list[str]` with exactly 11 ordered keys.
- Produces: `build_site_artifact(site: str, records: Sequence[TNMRecord]) -> dict`.
- Produces: `build_site_shards(records: Sequence[TNMRecord]) -> tuple[dict[str, dict], dict]`.

- [ ] **Step 1: Write failing tests for all 11 fallback levels**

```python
self.assertEqual(
    [key.split("|", 1)[0] for key in tnm_key_candidates(record)],
    [
        "full", "no_sex", "site_histology_coarse_age",
        "site_histology_tnm", "site_histology_m", "site_histology",
        "no_histology", "coarse_age", "site_tnm", "site_m", "site_only",
    ],
)
```

- [ ] **Step 2: Write failing shard tests**

Build records for Larynx and Thyroid and assert two artifacts, a manifest entry per site, no row crossing site boundaries, and `MX` absent from serialized row values and keys.

- [ ] **Step 3: Preserve fixed-horizon and risk-table tests while removing curve CI output**

Keep KM confidence calculations internally for fixed estimates. Add an assertion that `_survival_fields()` emits `fixed_survival`, `curve_months`, `curve_survival_probs`, and the risk table, but does not emit `curve_ci_lower_probs` or `curve_ci_upper_probs`.

- [ ] **Step 4: Run tests and confirm the current seven-level builder fails**

```bash
PYTHONPATH=scripts python3 -m unittest tests.python.test_km tests.python.test_lookup_builder -v
```

Expected: failure because the current builder has seven fallback levels and emits curve CI arrays.

- [ ] **Step 5: Implement the original 11-level key order**

Use the exact order in the approved design. Generate observations once per key, reject cross-site input in `build_site_artifact`, sort rows by matching-level rank then descending sample size, and generate an index matching row positions.

- [ ] **Step 6: Emit only fixed-time confidence intervals**

Keep `KMResult` curve CI arrays as internal calculation state if useful, but omit them from JSON rows. Preserve:

```python
"fixed_survival": {
    str(month): km.fixed[month].to_dict()
    for month in (12, 36, 60)
},
"risk_table_months": [0, 12, 24, 36, 48, 60],
"risk_table_counts": km.risk_table_counts,
```

- [ ] **Step 7: Run tests and update progress**

Run the Step 4 command. Expected: all KM and lookup-builder tests pass. Record completion in `progress.md`.

---

### Task 4: Generate validated metadata, options, manifest, and real shards

**Files:**
- Modify: `scripts/build_artifacts.py`
- Modify: `scripts/era_survival/validation.py`
- Create: `tests/python/test_real_artifact_contract.py`
- Modify: `tests/python/test_build_artifacts.py`
- Modify: `tests/python/test_validation.py`
- Replace generated files under: `public/data/`

**Interfaces:**
- Consumes: `load_cohort`, `build_site_shards`, and the four default source paths.
- Produces: `metadata.json`, `options.json`, `site_manifest.json`, and `lookup/*.json`.
- Produces: `validate_artifact_set(metadata, options, manifest, shards) -> None`.

- [ ] **Step 1: Write failing unit tests for the artifact set**

Assert atomic output contains only the three core files plus 13 lookup shards. Assert metadata contains source counts, exclusion counts, per-site eligible counts, stage-source policy, MX policy, fixed-time policy, and minimum sample thresholds.

- [ ] **Step 2: Write the real-data contract test**

```python
EXPECTED_SITE_COUNTS = {
    "Nose, Nasal Cavity and Middle Ear": 4969,
    "Larynx": 21786,
    "Thyroid": 99715,
}

def test_real_artifacts_reconcile(self):
    metadata = read_json("public/data/metadata.json")
    self.assertEqual(metadata["eligible_record_count"], 211160)
    self.assertEqual(metadata["site_record_counts"]["Larynx"], 21786)
    self.assertNotIn("MX", json.dumps(read_all_artifacts()))
    self.assertNotIn("summary_stage", json.dumps(read_all_artifacts()).lower())
```

- [ ] **Step 3: Run unit tests and confirm failure**

```bash
PYTHONPATH=scripts python3 -m unittest tests.python.test_build_artifacts tests.python.test_validation -v
```

Expected: failures because the current builder writes Summary, TNM, and EOD monoliths.

- [ ] **Step 4: Implement focused artifact orchestration and validation**

Write artifacts to temporary sibling paths, validate the complete set, then replace targets. Remove stale `summary_lookup.json`, `tnm_lookup.json`, and `descriptive_2018_2023.json` only after the new set validates. Validation must assert:

```python
metadata["eligible_record_count"] == 211_160
sum(metadata["site_record_counts"].values()) == 211_160
set(metadata["site_record_counts"]) == TARGET_SITES
set(manifest["sites"]) == TARGET_SITES
options["m_stages"] == ["M0", "M1", "Unknown"]
```

- [ ] **Step 5: Run unit tests**

Run the Step 3 command. Expected: all build and validation unit tests pass.

- [ ] **Step 6: Build the real artifacts**

```bash
PYTHONPATH=scripts python3 scripts/build_artifacts.py
```

Expected summary: 1,808,471 source rows, 211,160 eligible records, 13 site shards, 4,969 nasal cavity/middle ear/paranasal sinus records, 21,786 larynx records, and 99,715 thyroid records.

- [ ] **Step 7: Run the real artifact contract and inspect sizes**

```bash
PYTHONPATH=scripts python3 -m unittest tests.python.test_real_artifact_contract -v
du -sh public/data public/data/lookup
find public/data/lookup -type f -name '*.json' -exec ls -lh {} \;
```

Expected: contract passes; all 13 shards are nonempty and individually loadable. Record counts and artifact sizes in `progress.md`.

---

### Task 5: Add frontend shard types, loading, caching, and lookup order

**Files:**
- Modify: `src/types.ts`
- Modify: `src/data.ts`
- Modify: `src/data.test.ts`
- Modify: `src/lookup.ts`
- Modify: `src/lookup.test.ts`

**Interfaces:**
- Produces: `CoreData { metadata, options, manifest }`.
- Produces: `loadCoreData(fetcher?) -> Promise<CoreData>`.
- Produces: `loadSiteShard(site, manifest, fetcher?) -> Promise<LookupArtifact>`.
- Produces: `tnmCandidateKeys(query: TNMQuery) -> string[]` and `resolveLookup(artifact, query) -> LookupRow | null`.

- [ ] **Step 1: Write failing loader tests**

Assert core files load once, the requested site maps through the manifest, a 404 names the failed shard, and no Summary/EOD URL is requested.

- [ ] **Step 2: Write failing lookup tests for 11 levels and minimum sample**

Use one artifact with candidate rows at several fallback levels. Assert the first row with `sample_size >= 20` is returned and a 19-record row is skipped.

- [ ] **Step 3: Run tests and confirm failure**

```bash
npm test -- --run src/data.test.ts src/lookup.test.ts
```

Expected: failures because loading is cohort-based and lookup supports only seven TNM levels.

- [ ] **Step 4: Implement focused types and loaders**

Remove `CohortKind`, Summary fields, and curve CI arrays. Add:

```ts
export interface SiteManifest {
  sites: Record<string, string>
}

export interface LookupArtifact {
  site: string
  thresholds: { minimum_sample: number; stable_sample: number }
  rows: LookupRow[]
  index: Record<string, number>
}
```

Load `${BASE_URL}data/options.json`, `metadata.json`, and `site_manifest.json`, then `${BASE_URL}data/lookup/${manifest.sites[site]}`.

- [ ] **Step 5: Implement the exact 11-level browser candidate order**

Mirror the Python key order exactly and assert all generated keys use the selected site and the query M value (`M0`, `M1`, or `Unknown`; never `MX`).

- [ ] **Step 6: Run tests and update progress**

Run the Step 3 command. Expected: all loader and lookup tests pass. Record completion in `progress.md`.

---

### Task 6: Rebuild the single-screen query interface in the original site's layout

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/App.test.tsx`
- Modify: `src/components/FilterPanel.tsx`
- Modify: `src/components/FilterPanel.test.tsx`
- Modify: `src/components/ResultSummary.tsx`
- Modify: `src/components/ResultSummary.test.tsx`
- Modify: `src/components/AppHeader.tsx`

**Interfaces:**
- Consumes: `loadCoreData`, `loadSiteShard`, `resolveLookup`, `LookupArtifact`.
- Produces: a single detailed TNM screen with cached per-site artifacts and automatic result updates.

- [ ] **Step 1: Write failing application tests**

Cover Chinese default, absence of cohort tabs and Summary text, 13 site options, `MX` absence, automatic lookup after a complete form, shard fetch on site change, no refetch within one site, cached reuse when returning to a site, language switching without query reset, and loading/error states scoped to the selected site.

- [ ] **Step 2: Write failing filter and result tests**

Assert the filter fields are sex, site, histology, numeric age, T, N, and M; M options are exactly `M0`, `M1`, `Unknown`; and fixed estimate tiles display `95% CI` text or `不可估计` when status is `not_estimable`.

- [ ] **Step 3: Run focused frontend tests**

```bash
npm test -- --run src/App.test.tsx src/components/FilterPanel.test.tsx src/components/ResultSummary.test.tsx
```

Expected: failures because the current application still has cohort tabs and submit-based dual-cohort state.

- [ ] **Step 4: Implement site-shard state and cache**

```ts
const [core, setCore] = useState<CoreData | null>(null)
const [site, setSite] = useState('Hypopharynx')
const [artifact, setArtifact] = useState<LookupArtifact | null>(null)
const cache = useRef(new Map<string, LookupArtifact>())

useEffect(() => {
  const cached = cache.current.get(site)
  if (cached) return setArtifact(cached)
  void loadSiteShard(site, core!.manifest).then((next) => {
    cache.current.set(site, next)
    setArtifact(next)
  })
}, [core, site])
```

Guard against stale responses by comparing the requested site before setting visible state.

- [ ] **Step 5: Implement original-site interaction and result layout**

Use the `5173` input panel/result panel structure. Resolve the result with `useMemo` whenever the complete query or loaded shard changes. Show the matched fallback level, sample size, event/censor counts, median survival/follow-up, and 1/3/5-year tiles with fixed-time CI text.

- [ ] **Step 6: Run focused tests and update progress**

Run the Step 3 command. Expected: all App, filter, and result tests pass. Record completion in `progress.md`.

---

### Task 7: Use the 4174 chart style without confidence shading and retain its risk table

**Files:**
- Modify: `src/components/SurvivalChart.tsx`
- Modify: `src/components/SurvivalChart.test.tsx`
- Retain/modify: `src/components/RiskTable.tsx`
- Modify: `src/styles.css`

**Interfaces:**
- Consumes: `LookupRow.curve_months`, `curve_survival_probs`, `maximum_followup_months`, `risk_table_months`, and `risk_table_counts`.
- Produces: a responsive SVG KM chart and separate accessible risk table.

- [ ] **Step 1: Replace the confidence-band test with absence assertions**

```tsx
render(<SurvivalChart locale="zh" row={row} />)
expect(screen.getByTestId('survival-path')).toBeInTheDocument()
expect(screen.queryByTestId('confidence-band')).not.toBeInTheDocument()
expect(container.querySelector('.survival-chart__confidence')).toBeNull()
```

- [ ] **Step 2: Add risk-table and supported-follow-up tests**

Assert the table contains 0/12/24/36/48/60 and their counts, the SVG path ends at `maximum_followup_months`, and no path is extended to 60 when maximum follow-up is shorter.

- [ ] **Step 3: Run the chart tests and confirm failure**

```bash
npm test -- --run src/components/SurvivalChart.test.tsx
```

Expected: failure because the confidence polygon is still rendered.

- [ ] **Step 4: Remove all confidence polygon code and preserve 4174 geometry**

Change `CurvePoint` to `{ month: number; survival: number }`, align only month/survival arrays, remove `stepCoordinates`, `upperCoordinates`, `lowerCoordinates`, and the polygon JSX. Keep the `960 x 520` view box, axes, grid, dynamic supported x maximum, and current line styling.

- [ ] **Step 5: Preserve the separate responsive risk table**

Keep `<RiskTable>` immediately after the SVG. Retain horizontal overflow only on `.risk-table-wrap` below 520 px and the sticky first column; ensure the page itself has no horizontal overflow.

- [ ] **Step 6: Run chart tests and update progress**

Run the Step 3 command. Expected: all chart and risk-table assertions pass. Record completion in `progress.md`.

---

### Task 8: Finalize bilingual copy, remove obsolete modules, and align documentation

**Files:**
- Modify: `src/i18n.ts`
- Modify: `src/i18n.test.ts`
- Modify: `src/presentation.ts`
- Modify: `src/presentation.test.ts`
- Delete: `src/components/CohortTabs.tsx`
- Delete: `src/components/CohortTabs.test.tsx`
- Delete: `scripts/build_paper_outputs.py`
- Delete: `scripts/era_survival/descriptive.py`
- Delete: `scripts/era_survival/paper_config.py`
- Delete: `scripts/era_survival/paper_figures.py`
- Delete: `scripts/era_survival/paper_outputs.py`
- Delete: `scripts/era_survival/paper_tables.py`
- Delete: `scripts/era_survival/paper_text.py`
- Delete: obsolete Summary/EOD/paper Python tests
- Modify: `README.md`
- Modify: `package.json`

**Interfaces:**
- Produces: complete Chinese/English labels for 13 sites, histologies, result statuses, fallback levels, and method copy.
- Removes: all runtime and command references to Summary Stage, EOD, and paper generation.

- [ ] **Step 1: Write failing copy tests**

Assert Chinese translations for `Larynx`, `Thyroid`, and `Nose, Nasal Cavity and Middle Ear`; assert the method copy says 2010-2017 and MX is treated as M0; assert no visible copy advertises Summary Stage or EOD.

- [ ] **Step 2: Run copy tests and confirm failure**

```bash
npm test -- --run src/i18n.test.ts src/presentation.test.ts
```

Expected: failures for the three new site labels and obsolete dual-cohort copy.

- [ ] **Step 3: Implement focused copy and remove obsolete files**

Use these Chinese site labels:

```ts
'Nose, Nasal Cavity and Middle Ear': '鼻腔、中耳及鼻旁窦',
'Larynx': '喉',
'Thyroid': '甲状腺',
```

Remove cohort-tab keys/components, Summary/EOD descriptions, and the `build:paper` package script. Delete generated paper outputs only within this isolated project. Update README commands, source files, cohort definition, site counts, MX policy, fixed-time policy, and static shard architecture.

- [ ] **Step 4: Run copy tests and scan source text**

```bash
npm test -- --run src/i18n.test.ts src/presentation.test.ts
rg -n "Summary Stage|summary_lookup|descriptive_2018|EOD|build:paper|MX" src scripts package.json README.md
```

Expected: tests pass; remaining `MX` references are limited to documented conversion tests/policy, and no removed module is imported or callable.

- [ ] **Step 5: Update progress**

Record deletions, README changes, and focused test results in `progress.md`.

---

### Task 9: Full verification and browser QA

**Files:**
- Modify: `src/artifacts.test.ts`
- Modify: `progress.md`
- Update generated artifacts under: `public/data/`

**Interfaces:**
- Verifies the complete static website and leaves the worktree ready for the user's manual Git submission.

- [ ] **Step 1: Update the frontend real-artifact contract**

Assert 13 manifest entries, 211,160 metadata records, exact added-site counts, nonempty lookup shards, valid sampled index entries, no `MX`, no Summary Stage artifact, and fixed-estimate status/null consistency.

- [ ] **Step 2: Run all automated checks**

```bash
npm test -- --run
PYTHONPATH=scripts python3 -m unittest discover -s tests/python -p 'test_*.py'
npm run build
git diff --check
```

Expected: all frontend tests, all Python tests, the TypeScript/Vite build, and whitespace validation pass.

- [ ] **Step 3: Start the development server on an available port**

```bash
npm run dev -- --host 127.0.0.1 --port 4174 --strictPort
```

If 4174 is already occupied by this project, reuse that server after confirming it serves the rebuilt assets. Do not stop the original website on 5173.

- [ ] **Step 4: Perform desktop browser QA at 1440 x 1000**

Verify Chinese default; 13 site choices; automatic Larynx, Thyroid, and nasal/sinus queries; 2017 Combined TNM metadata; M options without MX; confidence intervals in fixed-time tiles; 4174-style SVG with no confidence polygon; separate risk table; language switching without filter/result reset; and no console errors.

- [ ] **Step 5: Perform mobile browser QA at 390 x 844**

Verify no page-level horizontal overflow, no clipped controls or result values, readable chart labels, nonblank SVG pixels, and horizontal scrolling confined to the risk table with its first column visible.

- [ ] **Step 6: Reconcile final artifacts and working tree**

```bash
python3 -c 'import json; d=json.load(open("public/data/metadata.json")); print(d["eligible_record_count"], d["site_record_counts"])'
git status --short
```

Expected: `211160`, the 13 approved site counts, only intended unstaged project changes, and no staged files.

- [ ] **Step 7: Record completion and hand off manual Git submission**

Add final test counts, build result, artifact counts/sizes, browser QA viewports, and any honest residual caveat to `progress.md`. Tell the user the exact `git add` and `git commit` commands to run manually; do not run them.
