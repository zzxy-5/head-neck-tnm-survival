# Kaplan-Meier Censor Marks Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render same-color vertical censor marks at each stored distinct censor month and add a localized censor legend to the Kaplan-Meier chart.

**Architecture:** Keep the artifact contract unchanged and derive censor coordinates entirely inside `SurvivalChart.tsx`. For each stored censor month, find the last curve point at or before that month so tied deaths are reflected before the censor mark is placed. Render accessible localized legend copy outside the SVG plot and plain non-scaling SVG lines inside it.

**Tech Stack:** React 19, TypeScript, SVG, CSS, Vitest, Testing Library, Vite.

## Global Constraints

- Use existing `LookupRow.censor_months`; do not rebuild lookup artifacts.
- Render one mark per distinct stored censor month at or before `maximum_followup_months`.
- Use `var(--primary-dark)`, `1.35 px` non-scaling strokes, and medium-small vertical marks.
- Do not add confidence bands, borders, fills, shadows, glow, tooltips, text bubbles, or per-marker labels.
- Show `删失` in Chinese and `Censored` in English in one compact legend item.
- Do not stage or commit files; the user will commit manually.

---

### Task 1: Specify Censor Marks and Legend with Failing Tests

**Files:**
- Modify: `src/components/SurvivalChart.test.tsx`

**Interfaces:**
- Consumes: `LookupRow.censor_months: number[]`, `curve_months: number[]`, and `curve_survival_probs: number[]`.
- Produces: Test contracts for `[data-testid="censor-mark"]` lines and localized legend text.

- [ ] **Step 1: Add representative censor months to the shared fixture**

Add censor months that cover a point between events and a month tied with an event:

```ts
const row = {
  // existing fields
  curve_months: [0, 6, 12, 24, 34],
  curve_survival_probs: [1, 0.9, 0.8, 0.7, 0.64],
  censor_months: [10, 12, 30],
  // existing fields
} as LookupRow
```

- [ ] **Step 2: Add the failing mark-style and placement assertions**

Inside the main chart test, assert that all three marks render and that the tied
month uses the post-event survival level:

```ts
const censorMarks = container.querySelectorAll('[data-testid="censor-mark"]')
expect(censorMarks).toHaveLength(3)
for (const mark of censorMarks) {
  expect(mark).toHaveAttribute('stroke', 'var(--primary-dark)')
  expect(mark).toHaveAttribute('stroke-width', '1.35')
  expect(mark).toHaveAttribute('vector-effect', 'non-scaling-stroke')
  expect(mark).not.toHaveAttribute('filter')
}
expect(container.querySelector('[data-censor-month="12"]')).toHaveAttribute(
  'data-survival-probability',
  '0.8',
)
expect(screen.getByText('Censored')).toBeInTheDocument()
```

- [ ] **Step 3: Add localization and empty-state assertions**

Extend the Chinese localization test and add an empty-array test:

```ts
expect(screen.getByText('删失')).toBeInTheDocument()

const { container } = render(
  <SurvivalChart locale="en" row={{ ...row, censor_months: [] }} />,
)
expect(container.querySelectorAll('[data-testid="censor-mark"]')).toHaveLength(0)
expect(screen.getByText('Censored')).toBeInTheDocument()
```

- [ ] **Step 4: Run the focused test and confirm RED**

Run:

```bash
npm test -- src/components/SurvivalChart.test.tsx
```

Expected: FAIL because censor marks and `Censored` / `删失` legend copy are not yet rendered.

---

### Task 2: Derive and Render Censor Coordinates

**Files:**
- Modify: `src/components/SurvivalChart.tsx`
- Modify: `src/i18n.ts`

**Interfaces:**
- Consumes: the supported curve points returned by `supportedPoints(row)`.
- Produces: `CensorPoint { month: number; survival: number }[]`, SVG censor lines, and `chart.censored` localized copy.

- [ ] **Step 1: Add localized legend copy**

Add the key to both locale dictionaries:

```ts
// English
'chart.censored': 'Censored',

// Chinese
'chart.censored': '删失',
```

- [ ] **Step 2: Add the coordinate derivation helper**

Place this helper beside `supportedPoints` and `stepPath`:

```ts
interface CensorPoint extends CurvePoint {}

function supportedCensorPoints(row: LookupRow, points: CurvePoint[]): CensorPoint[] {
  return row.censor_months
    .filter((month) => month <= row.maximum_followup_months)
    .map((month) => {
      const survival = points.reduce(
        (current, point) => (point.month <= month ? point.survival : current),
        1,
      )
      return { month, survival }
    })
}
```

The `<=` comparison intentionally selects the post-event value when an event and censor occur in the same month.

- [ ] **Step 3: Derive visible censor points in the component**

After the visible curve points are known, add:

```ts
const censorPoints = supportedCensorPoints(row, visiblePoints).filter(
  (point) => point.month <= xMaximum,
)
const censorHalfHeight = 7
```

- [ ] **Step 4: Render the compact legend**

Insert the legend between `.survival-chart__heading` and the chart SVG:

```tsx
<div className="survival-chart__legend">
  <svg aria-hidden="true" className="survival-chart__legend-mark" viewBox="0 0 12 18">
    <line
      stroke="var(--primary-dark)"
      strokeWidth="1.35"
      vectorEffect="non-scaling-stroke"
      x1="6"
      x2="6"
      y1="2"
      y2="16"
    />
  </svg>
  <span>{t(locale, 'chart.censored')}</span>
</div>
```

- [ ] **Step 5: Render plain censor lines over the survival curve**

Place these immediately after the survival path so the marks remain readable:

```tsx
{censorPoints.map((point) => {
  const centerY = y(point.survival)
  return (
    <line
      className="survival-chart__censor-mark"
      data-censor-month={point.month}
      data-survival-probability={point.survival}
      data-testid="censor-mark"
      key={point.month}
      stroke="var(--primary-dark)"
      strokeWidth="1.35"
      vectorEffect="non-scaling-stroke"
      x1={x(point.month)}
      x2={x(point.month)}
      y1={Math.max(margin.top, centerY - censorHalfHeight)}
      y2={Math.min(height - margin.bottom, centerY + censorHalfHeight)}
    />
  )
})}
```

- [ ] **Step 6: Run the focused test and confirm GREEN**

Run:

```bash
npm test -- src/components/SurvivalChart.test.tsx
```

Expected: 8 SurvivalChart tests pass.

---

### Task 3: Style the Legend Without Decorative Framing

**Files:**
- Modify: `src/styles.css`
- Test: `src/components/SurvivalChart.test.tsx`

**Interfaces:**
- Consumes: `.survival-chart__legend` and `.survival-chart__legend-mark` from Task 2.
- Produces: A compact, responsive, unframed legend row.

- [ ] **Step 1: Add the legend styles**

Place after `.survival-chart__heading p`:

```css
.survival-chart__legend {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  min-height: 18px;
  margin: -4px 0 8px;
  color: var(--muted);
  font-size: 12px;
}

.survival-chart__legend-mark {
  display: block;
  width: 12px;
  height: 18px;
  overflow: visible;
}
```

- [ ] **Step 2: Add a regression assertion against decorative framing**

```ts
const legend = screen.getByText('Censored').parentElement
expect(legend).toHaveClass('survival-chart__legend')
expect(legend).not.toHaveAttribute('title')
```

- [ ] **Step 3: Re-run the focused test**

Run:

```bash
npm test -- src/components/SurvivalChart.test.tsx
```

Expected: all focused tests pass.

---

### Task 4: Verify the Real App and Record Progress

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: the completed chart feature.
- Produces: verified desktop/mobile behavior and a progress record.

- [ ] **Step 1: Run the full automated verification**

Run:

```bash
npm test
npm run build
git diff --check
```

Expected: all frontend tests pass, the production build succeeds, and `git diff --check` exits zero. The existing external-drive AppleDouble pack-index warning may still print while Git exits zero.

- [ ] **Step 2: Restart and verify the local preview**

Restart Vite on `127.0.0.1:4174`, then load the existing 78-patient tongue cohort. Verify that censor marks sit on the KM step line, the Chinese legend reads `删失`, the marker is visually smaller and thinner than the survival curve, and no tooltip or bubble appears.

- [ ] **Step 3: Verify responsive behavior**

Check the normal in-app browser width and `390 x 844`. Confirm no horizontal page overflow, chart clipping, legend overlap, or console warnings/errors. Confirm the risk table remains independently scrollable where needed.

- [ ] **Step 4: Record completion**

Append a dated task to `progress.md` covering the data interpretation, mark style, legend localization, tests, build, and browser QA.

- [ ] **Step 5: Confirm Git remains manual**

Run:

```bash
git diff --cached --name-only
```

Expected: no staged files. Do not run `git add`, `git commit`, or `git push`.
