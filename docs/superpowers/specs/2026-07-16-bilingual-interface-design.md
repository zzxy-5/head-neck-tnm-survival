# Bilingual Interface Design

## Objective

Add a Chinese and English display option to the SEER Era-Aware Survival Atlas without changing source artifacts, lookup keys, cohort construction, survival estimates, or fallback behavior.

The interface defaults to Chinese on every page load. Users can switch between `中文` and `English` from the page header. The choice is intentionally not persisted, so a refresh returns to Chinese.

## Scope

The selected language controls all user-visible interface copy:

- project header and scientific description;
- cohort tabs and active-analysis notes;
- filter labels, placeholders, options, validation messages, submit and reset controls;
- loading, error, retry, empty, and initial-result states;
- result provenance, outcome labels, matching descriptions, quality notices, and research caveats;
- Kaplan-Meier chart title, accessible name, axes, legend, support note, and risk table;
- footer language.

Raw data values displayed in filters and results are translated where applicable. Examples include sex, anatomical site, histology, Summary Stage, matching level, and Unknown/Any categories.

The following are out of scope:

- translating generated paper outputs, CSV headers, JSON artifacts, README, or methods files;
- changing data generation or statistical analysis;
- persisting the selected language;
- language-specific URLs or browser-language detection;
- adding additional languages.

## Architecture

Create a small, dependency-free internationalization module under `src/`. It will define:

- `Locale` as `'zh' | 'en'`;
- a complete interface-copy dictionary for both locales;
- typed translation keys;
- display-value helpers that map raw artifact values to localized labels while falling back to the original value when no mapping exists;
- locale-aware formatting helpers for months, confidence intervals, unavailable estimates, and matching descriptions.

`App` owns the locale state and initializes it to `zh`. It passes the locale to the header and page components. A small language switch in the header calls `setLocale` directly. Locale changes do not alter active cohort, loaded artifacts, filter values, search state, or the matched result.

No third-party internationalization package will be added. The current interface is compact, has two fixed languages, and does not need asynchronous language bundles, locale routing, pluralization infrastructure, or persistence.

## Language Switch

The header displays a compact two-option segmented control labeled accessibly as language selection. Its visible options are `中文` and `English`.

- Chinese is selected on initial render.
- Selecting English updates the full interface immediately.
- Selecting Chinese restores Chinese immediately.
- Refreshing resets the interface to Chinese.
- The control is keyboard accessible and exposes the selected state.
- Its dimensions remain stable across languages and responsive breakpoints.

## Data Values And Query Integrity

Select elements continue to use the existing raw English artifact values in their `value` attributes. Only option text is localized. For example:

- value `Female` displays `女性` in Chinese and `Female` in English;
- value `Tongue` displays `舌` in Chinese and `Tongue` in English;
- value `Squamous cell carcinoma` displays `鳞状细胞癌` in Chinese and the original label in English;
- value `Localized` displays `局限期` in Chinese and `Localized` in English;
- value `Unknown` displays `未知` in Chinese and `Unknown` in English.

Submitted query objects remain unchanged and continue to contain raw English values. Lookup candidate keys and JSON artifacts are not modified. Result fields are localized only when rendered.

Scientific abbreviations and stage codes such as SEER, AJCC, TNM, EOD, KM, T2, N1, and M0 remain unchanged. Their surrounding explanatory language is translated.

## Component Changes

- `AppHeader` receives the current locale and a locale-change callback and renders the switch.
- `App` owns locale state, selects localized method and status text, and passes locale into child components.
- `CohortTabs`, `FilterPanel`, `ResultSummary`, `SurvivalChart`, `RiskTable`, `CaveatBox`, and `StatusState` receive locale-aware copy or the locale itself.
- Presentation helpers become locale-aware so survival estimates, median survival, matching descriptions, and confidence intervals are consistent across components.
- Component boundaries remain otherwise unchanged; data loading and lookup resolution are not coupled to locale.

## Fallback And Error Behavior

If a raw artifact value does not exist in the translation map, the interface displays the original value. This prevents missing labels and preserves the ability to inspect unexpected categories.

Loading failures, retry actions, empty results, invalid age input, unavailable fixed-time estimates, and small-sample warnings are translated in both languages. A language change during loading or after an error updates the visible status without starting another data request.

## Accessibility And Responsive Behavior

All visible labels and related accessible names use the selected language. The language control itself remains understandable in either mode because its two option labels are language names in their native forms.

The existing tab, form, SVG chart, table, and region semantics are preserved. The language switch supports keyboard interaction and communicates selection state. Chinese labels are checked at desktop, tablet, and mobile widths for wrapping, clipping, chart overlap, and horizontal overflow.

## Testing And Acceptance Criteria

Automated tests will verify:

1. The initial interface is Chinese and no browser-language or persisted preference overrides it.
2. The language switch changes the complete visible interface to English and back to Chinese.
3. Switching language preserves the active cohort, selected filters, loaded artifact cache, and displayed result.
4. Chinese option labels submit the original English query values.
5. Result metadata and raw categories are localized without mutating the source row.
6. Loading, error, empty, unavailable-estimate, and research-caveat copy exists in both languages.
7. Chart labels, accessible names, and risk-table labels change with locale.
8. Existing lookup, artifact, Python, and production-build tests continue to pass.

Rendered QA will cover desktop and mobile views, both cohorts, both languages, a matched result, an empty result, and a `Not estimable` result. The page must have no incoherent overlap or page-level horizontal overflow.

## Git Policy

The design and implementation remain uncommitted. The user will review and perform Git staging and commits manually when the feature is complete.
