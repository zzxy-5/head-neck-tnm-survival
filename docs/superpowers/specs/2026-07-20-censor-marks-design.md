# Kaplan-Meier Censor Marks Design

## Scope

Add censor marks and a censor legend to the existing single-cohort Kaplan-Meier
overall survival chart. Do not add confidence bands, borders, text bubbles, or
per-marker labels. Do not rebuild the lookup artifacts.

## Data Semantics

- Use the existing `LookupRow.censor_months` array.
- Render one mark for each distinct stored censor month at or before
  `maximum_followup_months`.
- Multiple censored records in the same month remain represented by one mark
  because the stored artifact contains distinct censor months rather than
  per-month censor counts.
- Place each mark at the Kaplan-Meier survival probability effective at that
  month. When deaths and censoring share a month, use the post-event survival
  level because the estimator applies deaths before censoring.

## Chart Presentation

- Render each censor mark as an SVG vertical `<line>` centered on the survival
  step at its follow-up month.
- Use the same deep teal color as the survival curve:
  `var(--primary-dark)`.
- Use a `1.35 px` non-scaling stroke and a medium-small vertical length.
- Use a plain butt-ended line with no border, fill, shadow, glow, tooltip, or
  text bubble.
- Keep the marks inside the supported curve range and do not extrapolate.

## Legend

- Add one compact legend item between the chart summary and the SVG plot.
- Show the same vertical mark followed by `删失` in Chinese and `Censored` in
  English.
- Keep the legend visually subordinate to the chart title and patient summary.

## Component Boundaries

- `SurvivalChart.tsx` derives the plotted censor coordinates from the stored
  curve and renders the marks and legend.
- `i18n.ts` owns the localized legend label.
- Existing lookup artifacts, Python Kaplan-Meier calculations, and risk-table
  behavior remain unchanged.

## Validation

- Component tests verify mark count, distinct-month positioning, post-event
  placement for a tied month, color, stroke width, non-scaling stroke, and the
  absence of decorative attributes.
- Component tests verify Chinese and English legend labels and that no marks
  render when `censor_months` is empty.
- Browser QA verifies desktop and narrow layouts, visual alignment with the
  curve, no horizontal overflow, and no console warnings or errors.
- Run the full frontend test suite and production build.

## Git Handling

Record the work in `progress.md`, but do not stage or commit any files. The user
will perform the Git commit manually.
