import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { CoreData, LookupArtifact, LookupRow } from './types'
import { t } from './i18n'

const { loadCoreData, loadSiteShard, resolveLookup } = vi.hoisted(() => ({
  loadCoreData: vi.fn(),
  loadSiteShard: vi.fn(),
  resolveLookup: vi.fn(),
}))

vi.mock('./data', () => ({ loadCoreData, loadSiteShard }))
vi.mock('./lookup', async (importOriginal) => ({
  ...(await importOriginal<typeof import('./lookup')>()),
  resolveLookup,
}))

vi.mock('./components/SurvivalChart', () => ({
  SurvivalChart: () => <div data-testid="survival-chart" />,
}))

import App from './App'

const sites = [
  'Lip', 'Tongue', 'Gum and Other Mouth', 'Floor of Mouth', 'Salivary Gland',
  'Tonsil', 'Oropharynx', 'Nasopharynx', 'Hypopharynx',
  'Other Oral Cavity and Pharynx', 'Nose, Nasal Cavity and Middle Ear',
  'Larynx', 'Thyroid',
]

const core: CoreData = {
  metadata: { eligible_record_count: 211160 },
  options: {
    sites,
    sexes: ['Female', 'Male'],
    histology_groups: ['8050-8089: squamous cell neoplasms'],
    t_stages: ['T0', 'T1', 'T2', 'T3', 'T4', 'Unknown'],
    n_stages: ['N0', 'N1', 'N2', 'N3', 'Unknown'],
    m_stages: ['M0', 'M1', 'Unknown'],
  },
  manifest: { sites: Object.fromEntries(sites.map((site) => [site, `${site}.json`])) },
}

const row: LookupRow = {
  key: 'matched', cohort_type: 'tnm', stage_source: 'AJCC 7th / SEER Combined TNM',
  matching_level: 'full', sex: 'Female', site: 'Tongue',
  histology_group: '8050-8089: squamous cell neoplasms', age_group: '50-59',
  t_stage: 'T2', n_stage: 'N1', m_stage: 'M0', sample_size: 84, event_count: 24,
  censor_count: 60, median_survival_months: 76, median_followup_months: 48,
  maximum_followup_months: 120,
  fixed_survival: {
    '12': { estimate: 0.9, confidence_interval: [0.82, 0.94], status: 'estimable' },
    '36': { estimate: 0.76, confidence_interval: [0.66, 0.83], status: 'estimable' },
    '60': { estimate: 0.65, confidence_interval: [0.54, 0.74], status: 'estimable' },
  },
  curve_months: [0, 12, 60, 120], curve_survival_probs: [1, 0.9, 0.65, 0.4],
  censor_months: [], risk_table_months: [0, 12, 36, 60], risk_table_counts: [84, 72, 54, 39],
  data_quality_flag: 'stable',
}

function artifact(site: string): LookupArtifact {
  return { site, thresholds: { minimum_sample: 20, stable_sample: 50 }, rows: [{ ...row, site }], index: { matched: 0 } }
}

async function selectCompleteQuery(user: ReturnType<typeof userEvent.setup>, site = 'Tongue') {
  await user.selectOptions(screen.getByLabelText('性别'), 'Female')
  await user.selectOptions(screen.getByLabelText('解剖部位'), site)
  await user.selectOptions(screen.getByLabelText('组织学类型'), '8050-8089: squamous cell neoplasms')
  await user.type(screen.getByLabelText('诊断年龄'), '55')
  await user.selectOptions(screen.getByLabelText('T 分期'), 'T2')
  await user.selectOptions(screen.getByLabelText('N 分期'), 'N1')
  await user.selectOptions(screen.getByLabelText('M 分期'), 'M0')
}

describe('App', () => {
  beforeEach(() => {
    loadCoreData.mockReset().mockResolvedValue(core)
    loadSiteShard.mockReset().mockImplementation((site: string) => Promise.resolve(artifact(site)))
    resolveLookup.mockReset().mockImplementation((next: LookupArtifact) => next.rows[0])
  })
  afterEach(cleanup)

  it('defaults to Chinese with one TNM page, 13 sites, and no Summary or MX option', async () => {
    render(<App />)
    await screen.findByLabelText('性别')

    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('头颈肿瘤 TNM 分期分层生存分析')
    expect(screen.queryByText('探索 2010-2017 年可比登记队列的实际总生存情况。')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: '中文' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.queryByRole('tab')).not.toBeInTheDocument()
    expect(screen.queryByText(/总体分期/)).not.toBeInTheDocument()
    expect(screen.getByLabelText('解剖部位').querySelectorAll('option')).toHaveLength(14)
    expect(screen.getByLabelText('M 分期')).toHaveTextContent('M0')
    expect(screen.getByLabelText('M 分期')).toHaveTextContent('M1')
    expect(Array.from(screen.getByLabelText('M 分期').querySelectorAll('option')).map((option) => option.getAttribute('value'))).toContain('Unknown')
    expect(screen.getByLabelText('M 分期')).not.toHaveTextContent('MX')
  })

  it('automatically resolves a complete query and preserves it across language changes', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('性别')
    await selectCompleteQuery(user)

    await waitFor(() => expect(resolveLookup).toHaveBeenCalled())
    expect(screen.getByText('84')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'English' }))

    expect(screen.getByLabelText('Sex')).toHaveValue('Female')
    expect(screen.getByLabelText('Anatomical site')).toHaveValue('Tongue')
    expect(screen.getByLabelText('Age at diagnosis')).toHaveValue(55)
    expect(screen.getByText('Reference group')).toBeInTheDocument()
  })

  it('places the research limitations after the survival chart', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('性别')
    await selectCompleteQuery(user)

    await waitFor(() => expect(screen.getByTestId('survival-chart')).toBeInTheDocument())
    const chart = screen.getByTestId('survival-chart')
    const caveat = screen.getByRole('complementary', { name: '研究局限性' })

    expect(chart.compareDocumentPosition(caveat) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('synchronizes document language and title while preserving the active query', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('性别')

    expect(document.documentElement).toHaveAttribute('lang', 'zh')
    expect(document.title).toBe(t('zh', 'header.title'))

    await selectCompleteQuery(user)
    await waitFor(() => expect(screen.getByText('84')).toBeInTheDocument())

    await user.click(screen.getByRole('button', { name: 'English' }))
    expect(document.documentElement).toHaveAttribute('lang', 'en')
    expect(document.title).toBe(t('en', 'header.title'))
    expect(screen.getByLabelText('Sex')).toHaveValue('Female')
    expect(screen.getByLabelText('Anatomical site')).toHaveValue('Tongue')
    expect(screen.getByText('Reference group')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '中文' }))
    expect(document.documentElement).toHaveAttribute('lang', 'zh')
    expect(document.title).toBe(t('zh', 'header.title'))
    expect(screen.getByLabelText('性别')).toHaveValue('Female')
    expect(screen.getByLabelText('解剖部位')).toHaveValue('Tongue')
    expect(screen.getByText('参照组例数')).toBeInTheDocument()
  })

  it('loads a selected site once and reuses cached shards when returning', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('解剖部位')
    const site = screen.getByLabelText('解剖部位')

    await user.selectOptions(site, 'Tongue')
    await waitFor(() => expect(loadSiteShard).toHaveBeenCalledWith('Tongue', core.manifest))
    await user.selectOptions(site, 'Larynx')
    await waitFor(() => expect(loadSiteShard).toHaveBeenCalledWith('Larynx', core.manifest))
    await user.selectOptions(site, 'Tongue')

    await waitFor(() => expect(loadSiteShard).toHaveBeenCalledTimes(2))
  })

  it('deduplicates in-flight site loads and ignores a stale response after the site changes', async () => {
    let resolveTongue!: (value: LookupArtifact) => void
    const tongue = new Promise<LookupArtifact>((resolve) => { resolveTongue = resolve })
    loadSiteShard.mockImplementation((site: string) => site === 'Tongue' ? tongue : Promise.resolve(artifact(site)))
    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('解剖部位')
    const site = screen.getByLabelText('解剖部位')

    await user.selectOptions(screen.getByLabelText('性别'), 'Female')
    await user.selectOptions(site, 'Tongue')
    await user.selectOptions(screen.getByLabelText('组织学类型'), '8050-8089: squamous cell neoplasms')
    await user.type(screen.getByLabelText('诊断年龄'), '55')
    await user.selectOptions(screen.getByLabelText('T 分期'), 'T2')
    await user.selectOptions(screen.getByLabelText('N 分期'), 'N1')
    await user.selectOptions(screen.getByLabelText('M 分期'), 'M0')
    await user.selectOptions(site, 'Larynx')
    expect(loadSiteShard).toHaveBeenCalledTimes(2)
    await waitFor(() => expect(screen.getAllByText('喉')).toHaveLength(2))
    await user.selectOptions(site, 'Tongue')
    await user.selectOptions(site, 'Larynx')
    expect(loadSiteShard).toHaveBeenCalledTimes(2)
    resolveTongue(artifact('Tongue'))
    await waitFor(() => expect(screen.getAllByText('喉')).toHaveLength(2))
  })

  it('does not surface a late failed shard after switching to a successful site', async () => {
    let rejectTongue!: (reason?: unknown) => void
    const tongue = new Promise<LookupArtifact>((_, reject) => { rejectTongue = reject })
    loadSiteShard.mockImplementation((nextSite: string) => nextSite === 'Tongue' ? tongue : Promise.resolve(artifact(nextSite)))

    const user = userEvent.setup()
    render(<App />)
    await screen.findByLabelText('解剖部位')
    const site = screen.getByLabelText('解剖部位')

    await user.selectOptions(site, 'Tongue')
    await waitFor(() => expect(loadSiteShard).toHaveBeenCalledWith('Tongue', core.manifest))
    await selectCompleteQuery(user, 'Larynx')

    await waitFor(() => expect(screen.getByText('84')).toBeInTheDocument())
    rejectTongue(new Error('late Tongue shard failure'))

    await waitFor(() => expect(screen.getByText('84')).toBeInTheDocument())
    expect(screen.queryByText('late Tongue shard failure')).not.toBeInTheDocument()
    expect(screen.queryByText(/Unable to load|failed/i)).not.toBeInTheDocument()
  })
})
