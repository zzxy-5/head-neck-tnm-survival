# Bilingual Interface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Chinese-first `中文 / English` interface switch that localizes all page copy and displayed artifact values without changing queries, data artifacts, or statistical behavior.

**Architecture:** `App` owns a non-persisted `Locale` state initialized to `zh`. A dependency-free `i18n.ts` module provides typed interface copy and raw-value display mappings; components receive `locale` as a prop, while form values, lookup keys, and source rows remain English. Locale-aware presentation helpers format survival output without mutating data.

**Tech Stack:** React 19, TypeScript, Vitest, Testing Library, Vite, existing CSS and Lucide icons.

## Global Constraints

- Default locale is `zh` on every mount and refresh.
- The visible switch is exactly `中文` and `English`; no preference persistence or browser-language detection.
- Translate all user-visible UI, accessible names, status messages, chart labels, risk-table labels, and supported raw artifact values.
- Keep select `value` attributes, submitted query objects, artifact JSON, lookup keys, cohort construction, and survival estimates unchanged.
- Keep SEER, AJCC, TNM, EOD, KM, T/N/M codes, years, and numeric statistics unchanged.
- Unknown raw values fall back to the original string.
- Do not add an internationalization dependency.
- Do not stage or commit; record progress and leave Git operations to the user.

---

## File Structure

- Create `src/i18n.ts`: locale type, typed copy, raw-value mappings, and localized display helpers.
- Create `src/i18n.test.ts`: dictionary completeness, value mapping, and fallback tests.
- Modify `src/presentation.ts` and `src/presentation.test.ts`: locale-aware survival and match formatting.
- Modify `src/App.tsx` and `src/App.test.tsx`: locale state, localized shell, state preservation, and switch integration.
- Modify `src/components/AppHeader.tsx`: language segmented control.
- Modify `src/components/CohortTabs.tsx` and its test: localized tab copy and accessible label.
- Modify `src/components/FilterPanel.tsx` and its test: localized labels/options with raw submitted values.
- Modify `src/components/StatusState.tsx`: localized default status and retry copy.
- Modify `src/components/ResultSummary.tsx` and its test: localized field labels, raw values, outcomes, and warnings.
- Modify `src/components/SurvivalChart.tsx`, `src/components/RiskTable.tsx`, and chart tests: localized SVG and risk-table text.
- Modify `src/components/CaveatBox.tsx`: localized interpretation note.
- Modify `src/styles.css`: stable language-switch dimensions and responsive header behavior.
- Modify `progress.md`: record bilingual feature and final verification counts.

---

### Task 1: Internationalization And Presentation Foundation

**Files:**
- Create: `src/i18n.ts`
- Create: `src/i18n.test.ts`
- Modify: `src/presentation.ts`
- Modify: `src/presentation.test.ts`

**Interfaces:**
- Produces: `type Locale = 'zh' | 'en'`
- Produces: `t(locale: Locale, key: CopyKey): string`
- Produces: `localizeValue(locale: Locale, value: string): string`
- Produces: `formatMedian(months: number | null, locale: Locale): string`
- Produces: `formatFixed(estimate: FixedEstimate, locale: Locale): FormattedFixedEstimate`
- Produces: `matchingLabel(level: string, locale: Locale): string`

- [ ] **Step 1: Write failing localization tests**

Add tests that require Chinese defaults, English parity, complete real-data mappings, and raw fallback:

```ts
import { describe, expect, it } from 'vitest'
import { localizeValue, t } from './i18n'

describe('i18n', () => {
  it('provides Chinese and English interface copy', () => {
    expect(t('zh', 'header.title')).toBe('SEER 分期年代生存图谱')
    expect(t('en', 'header.title')).toBe('SEER Era-Aware Survival Atlas')
    expect(t('zh', 'filter.submit')).toBe('查找可比队列')
    expect(t('en', 'filter.submit')).toBe('Find comparable cohort')
  })

  it.each([
    ['Female', '女性'],
    ['Male', '男性'],
    ['Tongue', '舌'],
    ['Floor of Mouth', '口底'],
    ['Squamous cell carcinoma', '鳞状细胞癌'],
    ['8050-8089: squamous cell neoplasms', '8050-8089：鳞状细胞肿瘤'],
    ['Localized', '局限期'],
    ['Regional', '区域期'],
    ['Distant', '远处转移期'],
    ['Unknown', '未知'],
    ['Any', '不限'],
  ])('localizes %s for display only', (raw, translated) => {
    expect(localizeValue('zh', raw)).toBe(translated)
    expect(localizeValue('en', raw)).toBe(raw)
  })

  it('falls back to the raw value', () => {
    expect(localizeValue('zh', 'Unexpected category')).toBe('Unexpected category')
  })
})
```

Extend presentation tests:

```ts
expect(formatMedian(null, 'zh')).toBe('未达到')
expect(formatMedian(36, 'zh')).toBe('36.0 个月')
expect(formatFixed(notEstimable, 'zh')).toEqual({
  value: '不可估计',
  interval: '随访时间未达到该时间点',
})
expect(matchingLabel('site_only', 'zh')).toBe('仅匹配解剖部位')
expect(matchingLabel('site_only', 'en')).toBe('Site only')
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```bash
npm test -- --run src/i18n.test.ts src/presentation.test.ts
```

Expected: failure because `i18n.ts` and locale parameters do not exist.

- [ ] **Step 3: Implement the typed copy and raw-value map**

Create `src/i18n.ts` with this public structure:

```ts
export type Locale = 'zh' | 'en'

const en = {
  'language.label': 'Language',
  'header.eyebrow': 'Retrospective registry analysis',
  'header.title': 'SEER Era-Aware Survival Atlas',
  'header.description': 'Explore observed survival among comparable registry cohorts while preserving stage-era boundaries.',
  'header.notice': 'For research reference only',
  'tabs.label': 'Survival cohort',
  'tabs.summary': 'Summary Stage · 2004-2023',
  'tabs.tnm': 'TNM · 2010-2017',
  'method.active': 'Active analysis',
  'method.summaryTitle': 'Overall cohort method',
  'method.summaryDescription': 'Diagnoses from 2004-2023 are compared using Localized, Regional, and Distant Summary Stage categories.',
  'method.tnmTitle': 'Detailed TNM method',
  'method.tnmDescription': 'Diagnoses from 2010-2017 use AJCC 7th edition definitions, including SEER Combined TNM for 2016-2017.',
  'filter.region': 'Cohort filters',
  'filter.eyebrow': 'Cohort definition',
  'filter.heading': 'Match registry records',
  'filter.sex': 'Sex',
  'filter.site': 'Anatomical site',
  'filter.histology': 'Histology',
  'filter.age': 'Age at diagnosis',
  'filter.summaryStage': 'Summary Stage',
  'filter.tStage': 'T stage',
  'filter.nStage': 'N stage',
  'filter.mStage': 'M stage',
  'filter.select': 'Select…',
  'filter.ageError': 'Enter a whole number from 0 to 120.',
  'filter.submit': 'Find comparable cohort',
  'filter.reset': 'Reset filters',
  'status.loading': 'Loading cohort data…',
  'status.error': 'Cohort data could not be loaded.',
  'status.empty': 'No comparable cohort met the minimum sample size.',
  'status.emptyDetailed': 'No reportable cohort reached the public minimum of 20 records. Broaden the filters or choose another cohort.',
  'status.retry': 'Retry data load',
  'intro.eyebrow': 'Subgroup estimate',
  'intro.title': 'Select a registry cohort',
  'intro.description': 'Set the cohort characteristics to view retrospective subgroup-level survival estimates and the stored Kaplan-Meier curve.',
  'result.region': 'Survival results',
  'result.matchedRegion': 'Matched reference group',
  'result.matchedTitle': 'Matched reference group',
  'result.cohortYears': 'Cohort years',
  'result.stageSource': 'Stage source',
  'result.matchUsed': 'Match used',
  'result.sex': 'Sex',
  'result.site': 'Anatomical site',
  'result.histology': 'Histology',
  'result.ageGroup': 'Age group',
  'result.stage': 'Stage',
  'result.outcomes': 'Observed outcomes',
  'result.referenceGroup': 'Reference group',
  'result.deaths': 'Deaths',
  'result.censored': 'Censored records',
  'result.medianOs': 'Median overall survival',
  'result.medianFollowup': 'Median follow-up',
  'result.yearOsSuffix': 'year overall survival',
  'quality.stable': 'Stable reference group (n >= 50)',
  'quality.small': 'Interpret cautiously: small reference group (n = 20-49)',
  'quality.verySmall': 'Not reportable in the public tool (n < 20)',
  'chart.region': 'Kaplan-Meier estimate',
  'chart.title': 'Kaplan-Meier overall survival curve',
  'chart.description': 'Stored overall survival estimate with its 95% confidence interval. The curve ends at the last stored follow-up month and is not extrapolated.',
  'chart.yAxis': 'Overall survival (%)',
  'chart.xAxis': 'Months since diagnosis',
  'risk.label': 'Number at risk',
  'risk.month': 'Month',
  'risk.atRisk': 'At risk',
  'caveat.region': 'Research limitations',
  'caveat.title': 'Interpretation',
  'caveat.body': 'These are retrospective subgroup-level estimates, not individualized predictions. Staging definitions and source variables differ by diagnosis era. This tool is not standalone clinical decision support.',
  'footer': 'Registry-derived estimates for research reference only. Not individualized clinical prediction.',
} as const

export type CopyKey = keyof typeof en
const zh: Record<CopyKey, string> = {
  ...en,
  'language.label': '语言',
  'header.eyebrow': '回顾性登记数据库分析',
  'header.title': 'SEER 分期年代生存图谱',
  'header.description': '在保留不同分期年代边界的前提下，探索可比登记队列的实际观察生存情况。',
  'header.notice': '仅供科研参考',
  'tabs.label': '生存分析队列',
  'tabs.summary': '总体分期 · 2004-2023',
  'tabs.tnm': 'TNM · 2010-2017',
  'method.active': '当前分析',
  'method.summaryTitle': '总体队列方法',
  'method.summaryDescription': '比较 2004-2023 年诊断病例的局限期、区域期和远处转移期总体分期。',
  'method.tnmTitle': '详细 TNM 方法',
  'method.tnmDescription': '2010-2017 年诊断病例采用 AJCC 第 7 版定义，其中 2016-2017 年使用 SEER Combined TNM。',
  'filter.region': '队列筛选条件',
  'filter.eyebrow': '队列定义',
  'filter.heading': '匹配登记病例',
  'filter.sex': '性别',
  'filter.site': '解剖部位',
  'filter.histology': '组织学类型',
  'filter.age': '诊断年龄',
  'filter.summaryStage': '总体分期',
  'filter.tStage': 'T 分期',
  'filter.nStage': 'N 分期',
  'filter.mStage': 'M 分期',
  'filter.select': '请选择…',
  'filter.ageError': '请输入 0 至 120 之间的整数。',
  'filter.submit': '查找可比队列',
  'filter.reset': '重置筛选条件',
  'status.loading': '正在加载队列数据…',
  'status.error': '无法加载队列数据。',
  'status.empty': '没有达到最小样本量要求的可比队列。',
  'status.emptyDetailed': '没有队列达到公开展示所需的 20 例最小样本量。请放宽筛选条件或选择其他队列。',
  'status.retry': '重新加载数据',
  'intro.eyebrow': '亚组生存估计',
  'intro.title': '请选择登记队列',
  'intro.description': '设置队列特征后，可查看回顾性亚组生存估计及已储存的 Kaplan-Meier 曲线。',
  'result.region': '生存结果',
  'result.matchedRegion': '匹配的参照组',
  'result.matchedTitle': '匹配的参照组',
  'result.cohortYears': '队列年份',
  'result.stageSource': '分期来源',
  'result.matchUsed': '实际匹配层级',
  'result.sex': '性别',
  'result.site': '解剖部位',
  'result.histology': '组织学类型',
  'result.ageGroup': '年龄组',
  'result.stage': '分期',
  'result.outcomes': '观察结局',
  'result.referenceGroup': '参照组例数',
  'result.deaths': '死亡数',
  'result.censored': '删失记录数',
  'result.medianOs': '中位总生存期',
  'result.medianFollowup': '中位观察随访时间',
  'result.yearOsSuffix': '年总生存率',
  'quality.stable': '稳定参照组（n >= 50）',
  'quality.small': '请谨慎解释：小样本参照组（n = 20-49）',
  'quality.verySmall': '不在公开工具中展示（n < 20）',
  'chart.region': 'Kaplan-Meier 估计',
  'chart.title': 'Kaplan-Meier 总生存曲线',
  'chart.description': '已储存的总生存估计及其 95% 置信区间。曲线止于最后一个已储存随访月，不进行外推。',
  'chart.yAxis': '总生存率（%）',
  'chart.xAxis': '诊断后月数',
  'risk.label': '在险人数',
  'risk.month': '月',
  'risk.atRisk': '在险',
  'caveat.region': '研究局限性',
  'caveat.title': '结果解释',
  'caveat.body': '这些结果是回顾性亚组层面的估计，并非个体化预测。不同诊断年代的分期定义和来源变量存在差异。本工具不能作为独立的临床决策支持。',
  'footer': '登记数据库衍生估计，仅供科研参考，并非个体化临床预测。',
}

const copy = { zh, en }
export function t(locale: Locale, key: CopyKey): string { return copy[locale][key] }
```

Define the complete raw-value map from the real artifacts and test fixtures:

```ts
const zhValues: Record<string, string> = {
  Female: '女性',
  Male: '男性',
  Any: '不限',
  Unknown: '未知',
  Localized: '局限期',
  Regional: '区域期',
  Distant: '远处转移期',
  'Floor of Mouth': '口底',
  'Gum and Other Mouth': '牙龈及口腔其他部位',
  Hypopharynx: '下咽',
  Lip: '唇',
  Nasopharynx: '鼻咽',
  Oropharynx: '口咽',
  'Other Oral Cavity and Pharynx': '口腔及咽其他部位',
  'Salivary Gland': '唾液腺',
  Tongue: '舌',
  Tonsil: '扁桃体',
  'Squamous cell carcinoma': '鳞状细胞癌',
  '8000-8009: unspecified neoplasms': '8000-8009：未特指肿瘤',
  '8010-8049: epithelial neoplasms, NOS': '8010-8049：上皮性肿瘤，非特指',
  '8050-8089: squamous cell neoplasms': '8050-8089：鳞状细胞肿瘤',
  '8090-8119: basal cell neoplasms': '8090-8119：基底细胞肿瘤',
  '8120-8139: transitional cell papillomas and carcinomas': '8120-8139：移行细胞乳头状瘤和癌',
  '8140-8389: adenomas and adenocarcinomas': '8140-8389：腺瘤和腺癌',
  '8390-8429: adnexal and skin appendage neoplasms': '8390-8429：皮肤附属器肿瘤',
  '8430-8439: mucoepidermoid neoplasms': '8430-8439：黏液表皮样肿瘤',
  '8440-8499: cystic, mucinous and serous neoplasms': '8440-8499：囊性、黏液性和浆液性肿瘤',
  '8500-8549: ductal and lobular neoplasms': '8500-8549：导管和小叶肿瘤',
  '8550-8559: acinar cell neoplasms': '8550-8559：腺泡细胞肿瘤',
  '8560-8579: complex epithelial neoplasms': '8560-8579：复杂上皮性肿瘤',
  '8680-8719: paragangliomas and glumus tumors': '8680-8719：副神经节瘤和血管球瘤',
  '8720-8799: nevi and melanomas': '8720-8799：痣和黑色素瘤',
  '8800-8809: soft tissue tumors and sarcomas, NOS': '8800-8809：软组织肿瘤和肉瘤，非特指',
  '8810-8839: fibromatous neoplasms': '8810-8839：纤维组织肿瘤',
  '8840-8849: myxomatous neoplasms': '8840-8849：黏液样肿瘤',
  '8850-8889: lipomatous neoplasms': '8850-8889：脂肪组织肿瘤',
  '8890-8929: myomatous neoplasms': '8890-8929：肌源性肿瘤',
  '8930-8999: complex mixed and stromal neoplasms': '8930-8999：复杂混合性和间质性肿瘤',
  '9040-9049: synovial-like neoplasms': '9040-9049：滑膜样肿瘤',
  '9060-9099: germ cell neoplasms': '9060-9099：生殖细胞肿瘤',
  '9120-9169: blood vessel tumors': '9120-9169：血管肿瘤',
  '9180-9249: osseous and chondromatous neoplasms': '9180-9249：骨和软骨肿瘤',
  '9260-9269: miscellaneous bone tumors (C40._, C41._)': '9260-9269：其他骨肿瘤（C40._、C41._）',
  '9270-9349: odontogenic tumors (C41._)': '9270-9349：牙源性肿瘤（C41._）',
  '9350-9379: miscellaneous tumors': '9350-9379：其他肿瘤',
  '9380-9489: gliomas': '9380-9489：胶质瘤',
  '9490-9529: neuroepitheliomatous neoplasms': '9490-9529：神经上皮性肿瘤',
  '9540-9579: nerve sheath tumors': '9540-9579：神经鞘肿瘤',
  '9580-9589: granular cell tumors & alveolar soft part sarcoma': '9580-9589：颗粒细胞瘤和腺泡状软组织肉瘤',
  'SEER Summary Stage 2000': 'SEER 总体分期 2000',
  'AJCC 7th': 'AJCC 第 7 版',
  'AJCC 7th / SEER Combined TNM': 'AJCC 第 7 版 / SEER Combined TNM',
  'SEER Combined TNM': 'SEER Combined TNM',
  'SEER Combined TNM (AJCC 7th era)': 'SEER Combined TNM（AJCC 第 7 版年代）',
}

export function localizeValue(locale: Locale, value: string): string {
  return locale === 'zh' ? (zhValues[value] ?? value) : value
}
```

Update presentation helpers to require `locale`, using `未达到`, `不可估计`, `个月`, `95% 置信区间`, and the Chinese matching-level map for `zh`; preserve current English output for `en`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 1 command again. Expected: all i18n and presentation tests pass.

---

### Task 2: Chinese-First App Shell And Language Switch

**Files:**
- Modify: `src/App.tsx`
- Modify: `src/App.test.tsx`
- Modify: `src/components/AppHeader.tsx`
- Modify: `src/components/CohortTabs.tsx`
- Modify: `src/components/CohortTabs.test.tsx`
- Modify: `src/components/StatusState.tsx`
- Modify: `src/styles.css`

**Interfaces:**
- Consumes: `Locale`, `t`
- Produces: `AppHeader({ locale, onLocaleChange })`
- Produces: `CohortTabs({ activeCohort, locale, onChange })`
- Produces: `StatusState({ locale, state, message? })`

- [ ] **Step 1: Write failing app integration tests**

Add tests that assert default Chinese, English switching, no extra data request, and preserved cohort/result:

```ts
expect(screen.getByRole('heading', { name: 'SEER 分期年代生存图谱' })).toBeInTheDocument()
expect(screen.getByRole('button', { name: '中文' })).toHaveAttribute('aria-pressed', 'true')
await user.click(screen.getByRole('button', { name: 'English' }))
expect(screen.getByRole('heading', { name: 'SEER Era-Aware Survival Atlas' })).toBeInTheDocument()
expect(loadLookup).toHaveBeenCalledTimes(1)
expect(screen.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true')
```

After producing a matched result, switch language and assert the result remains mounted and `resolveLookup` is not called again. Update cohort-tab tests to render with `locale="zh"` and assert Chinese labels plus unchanged arrow-key behavior.

- [ ] **Step 2: Run the focused tests and verify RED**

```bash
npm test -- --run src/App.test.tsx src/components/CohortTabs.test.tsx
```

Expected: failures because locale props and the language switch do not exist.

- [ ] **Step 3: Implement locale ownership and shell copy**

In `App`:

```tsx
const [locale, setLocale] = useState<Locale>('zh')
const emptyCopy = t(locale, 'status.emptyDetailed')

<AppHeader locale={locale} onLocaleChange={setLocale} />
<CohortTabs activeCohort={activeCohort} locale={locale} onChange={changeCohort} />
```

Pass `locale` through all rendered page components. Build method copy from `t(locale, ...)` during render rather than using an English module-level constant. Do not include `locale` in artifact-loading dependencies and do not include it in the `FilterPanel` key.

Implement the header switch:

```tsx
<div aria-label={t(locale, 'language.label')} className="language-switch" role="group">
  {(['zh', 'en'] as const).map((option) => (
    <button
      aria-pressed={locale === option}
      key={option}
      onClick={() => onLocaleChange(option)}
      type="button"
    >
      {option === 'zh' ? '中文' : 'English'}
    </button>
  ))}
</div>
```

Localize status, retry, method, intro, filter-region accessible label, and footer copy. Add `.app-header__actions` and `.language-switch` styles with stable 72 px options, 38 px height, 4 px radius, clear pressed state, and a mobile rule that allows the actions to wrap below the title without overflow.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 2 command again. Expected: all selected tests pass.

---

### Task 3: Localized Filters With Raw Query Values

**Files:**
- Modify: `src/components/FilterPanel.tsx`
- Modify: `src/components/FilterPanel.test.tsx`

**Interfaces:**
- Consumes: `Locale`, `t`, `localizeValue`
- Produces: `FilterPanel({ artifact, cohort, locale, onSubmit })`

- [ ] **Step 1: Write failing query-integrity tests**

Render with `locale="zh"`, select Chinese-visible options, and assert raw submissions:

```ts
expect(screen.getByLabelText('性别')).toBeInTheDocument()
expect(screen.getByRole('option', { name: '女性' })).toHaveValue('Female')
expect(screen.getByRole('option', { name: '舌' })).toHaveValue('Tongue')
await user.selectOptions(screen.getByLabelText('性别'), 'Female')
await user.selectOptions(screen.getByLabelText('解剖部位'), 'Tongue')
await user.selectOptions(screen.getByLabelText('组织学类型'), '8050-8089: squamous cell neoplasms')
await user.type(screen.getByLabelText('诊断年龄'), '55')
await user.selectOptions(screen.getByLabelText('总体分期'), 'Localized')
await user.click(screen.getByRole('button', { name: '查找可比队列' }))
expect(onSubmit).toHaveBeenCalledWith({
  sex: 'Female',
  site: 'Tongue',
  histology_group: '8050-8089: squamous cell neoplasms',
  age: 55,
  summary_stage: 'Localized',
})
```

Add a rerender test: select values in Chinese, rerender with English, and assert values remain selected and labels change.

- [ ] **Step 2: Run the focused test and verify RED**

```bash
npm test -- --run src/components/FilterPanel.test.tsx
```

- [ ] **Step 3: Implement localized field and option display**

Add `locale` to props. Extend `SelectField` with `locale` and render:

```tsx
<option value="">{t(locale, 'filter.select')}</option>
{options.map((option) => (
  <option key={option} value={option}>{localizeValue(locale, option)}</option>
))}
```

Replace every visible label, age error, submit text, reset title, and reset accessible name with `t(locale, key)`. Keep `FormValues`, stage arrays, `update`, and `submit` unchanged. Keep the reset effect dependent only on `[artifact, cohort]`, never on locale.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 3 command again. Expected: existing English behavior and new Chinese raw-value behavior pass.

---

### Task 4: Localized Results, Chart, Risk Table, And Caveat

**Files:**
- Modify: `src/components/ResultSummary.tsx`
- Modify: `src/components/ResultSummary.test.tsx`
- Modify: `src/components/SurvivalChart.tsx`
- Modify: `src/components/SurvivalChart.test.tsx`
- Modify: `src/components/RiskTable.tsx`
- Modify: `src/components/CaveatBox.tsx`

**Interfaces:**
- Consumes: `Locale`, `t`, `localizeValue`, locale-aware presentation helpers
- Produces: locale props on all four user-facing result components

- [ ] **Step 1: Write failing result and chart tests**

Render result and chart with `locale="zh"` and assert:

```ts
expect(screen.getByRole('region', { name: '生存结果' })).toBeInTheDocument()
expect(screen.getByText('舌')).toBeInTheDocument()
expect(screen.getByText('鳞状细胞癌')).toBeInTheDocument()
expect(screen.getByText('未达到')).toBeInTheDocument()
expect(screen.getAllByText('不可估计')).toHaveLength(2)
expect(screen.getByText('95% 置信区间 70.1%-76.5%')).toBeInTheDocument()
expect(screen.getByText(/回顾性亚组层面的估计/)).toBeInTheDocument()
```

Chart assertions:

```ts
expect(screen.getByRole('img', { name: 'Kaplan-Meier 总生存曲线' })).toBeInTheDocument()
expect(within(svg).getByText('总生存率（%）')).toBeInTheDocument()
expect(within(svg).getByText('诊断后月数')).toBeInTheDocument()
expect(screen.getByRole('table', { name: '在险人数' })).toBeInTheDocument()
expect(within(table).getByRole('rowheader', { name: '在险' })).toBeInTheDocument()
```

- [ ] **Step 2: Run focused tests and verify RED**

```bash
npm test -- --run src/components/ResultSummary.test.tsx src/components/SurvivalChart.test.tsx
```

- [ ] **Step 3: Implement localized result display**

Add `locale` props. Call `formatFixed(..., locale)`, `formatMedian(..., locale)`, and `matchingLabel(..., locale)`. Localize `row.sex`, `row.site`, `row.histology_group`, `row.age_group`, `row.summary_stage`, and `row.stage_source` with `localizeValue`. Preserve T/N/M codes unchanged through the fallback behavior.

Use localized fixed-time labels:

```tsx
<dt>
  {locale === 'zh'
    ? `${Number(month) / 12}${t(locale, 'result.yearOsSuffix')}`
    : `${Number(month) / 12}-${t(locale, 'result.yearOsSuffix')}`}
</dt>
```

Render the quality message from localized copy keys and pass locale into `CaveatBox`.

- [ ] **Step 4: Implement localized chart and risk-table text**

Use `t(locale, ...)` for section labels, SVG title/description, axis labels, table accessible name, caption, month header, and at-risk row header. Keep path calculations and numeric values byte-for-byte unchanged.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 4 command again. Expected: all result and chart tests pass in both locales.

---

### Task 5: Full Verification, Rendered QA, And Progress Record

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: completed bilingual interface
- Produces: verified, documented, uncommitted feature

- [ ] **Step 1: Run all frontend tests**

```bash
npm test -- --run
```

Expected: all existing and new frontend tests pass with no warnings.

- [ ] **Step 2: Run the production build**

```bash
npm run build
```

Expected: TypeScript and Vite build succeed.

- [ ] **Step 3: Run the unchanged Python suite**

```bash
MPLCONFIGDIR=/private/tmp/seer-era-mpl PYTHONPATH=scripts \
  .venv/bin/python -m unittest discover -s tests/python -p 'test_*.py'
```

Expected: all 101 existing Python tests pass, confirming no data-analysis regression.

- [ ] **Step 4: Perform rendered desktop and mobile QA**

Start the dev server on an available port. Check at 1440x1000 and 390x844:

- Chinese is the initial language.
- `中文 / English` is keyboard operable and has a visible selected state.
- Both Summary and TNM filter forms retain values when language changes.
- A matched result, empty result, and not-estimable result translate fully.
- Chart title, axes, description, and risk table translate without SVG overlap.
- No page-level horizontal overflow or clipped switch/button/select text appears.
- Switching language does not issue another artifact request.

- [ ] **Step 5: Record progress and inspect Git scope**

Append bilingual implementation details and exact verification counts to `progress.md`. Run:

```bash
git diff --check
git status --short
```

Expected: no whitespace errors, only the isolated project and existing root `.gitignore` change are visible, and nothing is staged. Do not run `git add` or `git commit`.
