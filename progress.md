# Progress

## Expanded TNM Redesign

Status: Tasks 1-8 complete; Task 9 final verification and browser-QA follow-up
are complete; no files have been staged or committed.

- The isolated project now contains one detailed TNM survival lookup for
  diagnoses in 2010-2017, with 13 anatomical site groups and 211,160 eligible
  records from four CSV exports.
- The three added groups are Nose, Nasal Cavity and Middle Ear (4,969), Larynx
  (21,786), and Thyroid (99,715). The static build generates metadata, options,
  a site manifest, and 13 site-local lookup shards.
- Diagnoses from 2010-2015 use AJCC 7th edition T/N/M fields; diagnoses from
  2016-2017 use SEER Combined TNM. Raw `MX` is normalized to `M0`, while
  unknown T/N remains an explicit query value.
- The browser mirrors the original 11-level fallback, skips groups below 20
  records, loads only the selected site shard, and defaults to Chinese with a
  nonpersistent Chinese/English switch.
- The Kaplan-Meier view renders the stored step curve, axes, and separate
  number-at-risk table through actual follow-up. Confidence intervals appear
  only in the fixed 1-, 3-, and 5-year result tiles; the curve has no confidence
  shading.

## Task 8: Copy And Legacy Cleanup

Complete (2026-07-20).

- Added Chinese labels for Nose, Nasal Cavity and Middle Ear, Larynx, and
  Thyroid. The method panel now documents the 2010-2017 cohort, the two TNM
  sources, `MX` to `M0` normalization, fixed-time 95% confidence intervals, and
  the absence of curve confidence shading.
- Completed Chinese and English labels for every active fallback level and
  removed visible dual-cohort and legacy-stage copy.
- Deleted the unused cohort-tabs component and test, stale monolithic-artifact
  frontend test, paper-generation modules and their Python tests, the
  `build:paper` script, obsolete rendering dependencies, and old isolated
  paper outputs. Task 8 did not modify the root project.
- Retained `build_artifacts.py`, `validation.py`, real-artifact contract tests,
  and their negative checks that reject legacy stage fields, stale artifact
  names, curve CI arrays, and raw `MX` values.
- Rewrote `README.md` for the four source CSVs, 13 sites, 211,160 eligible
  records, 11-level fallback, static site-shard architecture, and current
  build/test commands.

Verification:

- Focused copy tests: 25 tests passed, including exhaustive localization of
  every histology in the real options artifact.
- Full frontend suite: 8 files, 49 tests passed.
- Full Python suite: 55 tests passed.
- `npm run build` passed.
- Keyword scan found no runnable legacy modules; remaining legacy terms are
  limited to negative validation/test assertions, and remaining `MX` references
  document or enforce the conversion policy.
- `git diff --check` found no whitespace errors. Git emitted the pre-existing
  external-drive AppleDouble pack-index warning; no Git repair, staging, or
  commit was performed.

## Task 9: Automated Acceptance

Automated acceptance complete (2026-07-20); browser interaction is intentionally
left to the controller.

- Recreated `src/artifacts.test.ts` for the single detailed-TNM artifact set.
  Its two tests read all real artifacts and assert exactly 16 JSON files, 13
  manifest sites, 211,160 eligible records, the added-site counts (4,969 nasal
  cavity/middle ear/paranasal sinus; 21,786 larynx; 99,715 thyroid), nonempty
  shards, index-to-row integrity, no `MX`/Summary Stage/EOD/curve-CI payloads,
  fixed-time estimate consistency, and curve termination at each row's actual
  maximum follow-up.
- Full frontend suite: 9 files, 51 tests passed. Full Python suite: 55 tests
  passed. Production TypeScript/Vite build passed. `git diff --check` exited
  successfully with no whitespace findings.
- The contract test uses Node file APIs, so `@types/node` was added as a dev
  dependency and enabled in `tsconfig.app.json`. The initial build correctly
  failed because the application TypeScript config did not provide those types;
  it passed after this focused configuration fix.
- Artifact reconciliation: 16 JSON files total, 34,253,376 bytes (13 lookup
  shards: 34,249,950 bytes; core metadata/options/manifest: 1,130/1,820/476
  bytes). Metadata confirms AJCC 7th edition for 2010-2015, SEER Combined TNM
  for 2016-2017, and `MX` normalized to `M0`.
- The current-project Vite server uses strict port binding at
  `http://127.0.0.1:4174/`. The original `http://127.0.0.1:5173/` listener
  remains separate and was not modified or stopped. Process IDs are omitted
  because they change whenever a development server is restarted.
- `git status --short` shows all project changes unstaged; `git diff --cached
  --name-only` returned no staged paths. No commit was created.

Residual notes: the external drive's AppleDouble Git pack-index warning still
appears on Git commands, but no Git repair was attempted. `npm install` reports
five dependency-audit findings (three moderate, one high, one critical); no
automatic audit fix was run.

Controller browser QA covered 1440 x 1000 and 390 x 844. Real Larynx, Thyroid,
and nasal cavity/middle ear/paranasal sinus queries returned stored results;
fixed-time confidence intervals, 167-month support, no curve confidence band,
site-shard switching, language/result retention, risk-table-only horizontal
scrolling, and empty warning/error console logs were verified. A language
metadata defect found during QA was fixed and rechecked after restarting Vite
to clear its external-drive transform cache.

## Task 9: Browser-QA Language Metadata Fix

Complete (2026-07-20).

- Added an `App` regression test for initial Chinese metadata, English
  switching, Chinese restoration, and preservation of the active filters and
  result.
- Confirmed RED before the fix: the rendered content changed language while
  `document.documentElement.lang` was absent.
- Added a minimal locale effect in `App.tsx` that synchronizes both
  `document.documentElement.lang` and `document.title` from `header.title`.
- App focused suite: 6 tests passed. Full frontend suite: 9 files, 52 tests
  passed. `npm run build` passed.
- No files were staged or committed.

## Final Whole-Branch Review

Complete (2026-07-20).

- Enforced the exact diagnosis-era/stage-source contract at the normalized
  record and validation boundaries.
- Replaced raw observation-time follow-up with reverse Kaplan-Meier median
  follow-up. When the reverse curve does not cross 50%, the JSON value is
  `null` and the interface reports “未达到 / Not reached”.
- Rebuilt all four CSV inputs: 16 JSON files, 13 shards, 29,941 lookup rows,
  211,160 eligible records, and 12,904 rows with unreached median follow-up.
- Improved mobile KM labels: at 390 x 844 the 351 px SVG rendered ordinary
  labels at 13.5 px, retained 0/36/60/maximum ticks, had no CI band, and did
  not create page or chart horizontal overflow.
- Restored the repository-level `.gitignore` to its original behavior and
  synchronized both the static and runtime page titles.
- Final independent review: approved with no P0-P3 findings.

Fresh final verification: 9 frontend files / 54 tests passed; 67 Python tests
passed; the TypeScript/Vite production build passed; `git diff --check` exited
zero; both ports 4174 and 5173 returned HTTP 200; and the staging area remained
empty. Browser QA passed at 1440 x 1000 and 390 x 844 with no console warnings
or errors. No Git staging or commit was performed.

## Task 10: Research Copy Revision

Complete (2026-07-20).

- Reframed the page as a SEER-based retrospective analysis of TNM
  stage-stratified survival in head and neck tumors.
- Replaced the method note with the approved Kaplan-Meier wording, including
  the AJCC 7th edition/SEER Combined TNM eras, `MX` to `cM0` normalization and
  inclusion in `M0`, fixed 1-, 3-, and 5-year overall survival with 95%
  confidence intervals, and omission of curve confidence bands.
- Renamed the cohort panel to study cohort construction and case selection
  criteria, broadened the research notice to clinical and research reference,
  revised the footer, and removed the header subtitle without leaving an empty
  layout element.
- Updated parallel English copy so the language switch does not expose the old
  terminology.
- Focused i18n/App tests passed (2 files, 26 tests). Browser QA passed in
  Chinese and English at desktop and mobile widths with no horizontal overflow,
  element overlap, console warnings, or console errors.
- No files were staged or committed.

## Task 11: Survival Curve and Risk-Set Presentation

Complete (2026-07-20).

- Added a visible overall-survival-curve heading with the matched cohort's
  actual sample size and reverse Kaplan-Meier median follow-up. Unreached median
  follow-up is displayed as unreached rather than as a fabricated month value.
- Renamed the Chinese risk table caption and row label to “风险集人数” and its
  time row to “随访时间（月）”; synchronized the English labels.
- Reduced the deep-teal Kaplan-Meier step line to 2.25 px, kept it free of
  confidence bands, shadows, glow, and filters, and used a non-scaling SVG
  stroke so the requested visual width is retained on narrow screens.
- Expanded the component regression suite to cover the bilingual heading and
  summary, real/null follow-up formatting, risk-set terminology, line color,
  width, non-scaling behavior, and absence of filters.
- No files were staged or committed.

## Task 12: Median Survival Annotation and Result Order

Complete (2026-07-20).

- Removed the final confidence-band readability sentence from the Chinese and
  English method paragraphs while retaining the implemented no-band chart
  behavior.
- Moved the research-limitations box below the survival curve and risk-set
  table, making it the final result element before the page footer.
- Added a standard Kaplan-Meier median-survival annotation using the stored
  `median_survival_months`: dashed 50% horizontal and median-month vertical
  guides, an intersection marker, and a localized month label.
- When median overall survival is unreached, the chart shows a localized
  unreached label and renders no false marker or guide lines.
- Added regression coverage for exact method copy, result ordering, reached
  median annotation, and unreached median behavior.
- No files were staged or committed.

## Task 13: Unreached Median Explanation and Follow-up Axis

Complete (2026-07-20).

- Added a localized explanatory note beneath “未达到 / Not reached” only when
  the matched cohort's median overall survival is unreached; reached medians do
  not show the note.
- Renamed the Kaplan-Meier chart x-axis to “随访时间 / Follow-up time”.
- Added component regression coverage for both languages and for suppressing
  the unreached explanation when a median month is available.
- Browser QA passed for the 78-patient unreached example at desktop and narrow
  widths with no horizontal overflow or console warnings/errors.
- No files were staged or committed.

## Task 14: Kaplan-Meier Censor Marks

Complete (2026-07-20).

- Used the existing distinct `censor_months` artifact field without rebuilding
  data. Each stored censor month is placed at the Kaplan-Meier survival level
  effective at that month, including the post-event level for tied months.
- Added plain vertical censor marks in the same deep teal as the survival curve
  with a 1.35 px non-scaling stroke, no border, tooltip, bubble, shadow, glow,
  or per-marker text.
- Added a compact unframed legend labeled “删失 / Censored”.
- Added component regression coverage for mark count, tied-month placement,
  visual attributes, localization, and the empty-censor case.
- Full frontend verification passed: 9 test files and 59 tests; the production
  build passed. Browser QA of the real 78-patient cohort showed 41 distinct
  censor-month marks with no desktop/mobile overflow or console warnings/errors.
- No files were staged or committed.

## Task 15: Standalone Repository and GitHub Pages Setup

Complete (2026-07-21).

- Copied the finished application into the standalone directory
  `/Volumes/PortableSSD/prediction/head-neck-tnm-survival`, excluding local
  dependencies, build output, Python environments, caches, and AppleDouble
  metadata.
- Initialized an independent `main` Git repository and configured `origin` as
  `https://github.com/zzxy-5/head-neck-tnm-survival.git`.
- Set the Vite base path to `/head-neck-tnm-survival/` and added a GitHub Pages
  Actions workflow that installs dependencies, builds `dist`, uploads the Pages
  artifact, and deploys it.
- Expanded `.gitignore` for Vite, Python, coverage, TypeScript build cache, and
  AppleDouble files. Website data in `public/data` remains included.
- Verification passed: 9 frontend test files / 59 tests, production build, and
  local production URLs for both the app and metadata returned HTTP 200.
- No files were staged, committed, or pushed.
