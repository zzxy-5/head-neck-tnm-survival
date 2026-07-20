import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { LookupRow } from '../types'
import { ResultSummary } from './ResultSummary'

afterEach(cleanup)

const row: LookupRow = {
  key: 'full', cohort_type: 'tnm', stage_source: 'AJCC 7th / SEER Combined TNM', matching_level: 'full',
  sex: 'Female', site: 'Tongue', histology_group: '8050-8089: squamous cell neoplasms', age_group: '50-59',
  t_stage: 'T2', n_stage: 'N1', m_stage: 'M0', sample_size: 42, event_count: 18, censor_count: 24,
  median_survival_months: null, median_followup_months: 28, maximum_followup_months: 34,
  fixed_survival: {
    '12': { estimate: 0.734, confidence_interval: [0.701, 0.765], status: 'estimable' },
    '36': { estimate: null, confidence_interval: null, status: 'not_estimable' },
    '60': { estimate: null, confidence_interval: null, status: 'not_estimable' },
  },
  curve_months: [0, 12, 24, 34], curve_survival_probs: [1, 0.734, 0.68, 0.61], censor_months: [10],
  risk_table_months: [0, 12, 24, 36, 48, 60], risk_table_counts: [42, 34, 21, 0, 0, 0], data_quality_flag: 'small_sample',
}

describe('ResultSummary', () => {
  it('shows fixed 1, 3, and 5-year tiles with CI text or not estimable', () => {
    render(<ResultSummary locale="zh" row={row} />)
    expect(screen.getByText('1 年总生存率')).toBeInTheDocument()
    expect(screen.getByText('73.4%')).toBeInTheDocument()
    expect(screen.getByText('95% 置信区间 70.1%-76.5%')).toBeInTheDocument()
    expect(screen.getAllByText('不可估计')).toHaveLength(2)
  })

  it('renders the matching details and counts without a cohort selector', () => {
    render(<ResultSummary locale="en" row={row} />)
    expect(screen.getByText('Exact match')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Not reached')).toBeInTheDocument()
    expect(screen.getByText('(At last follow-up, the survival curve had not fallen to 50%)')).toBeInTheDocument()
    expect(screen.queryByText(/Summary Stage/)).not.toBeInTheDocument()
    expect(screen.queryByRole('complementary', { name: 'Research limitations' })).not.toBeInTheDocument()
  })

  it('shows the median-survival explanation only when the median is unreached', () => {
    const { rerender } = render(<ResultSummary locale="zh" row={row} />)

    expect(screen.getByText('（截至最后随访，生存曲线尚未下降至 50%）')).toBeInTheDocument()

    rerender(<ResultSummary locale="zh" row={{ ...row, median_survival_months: 20 }} />)
    expect(screen.queryByText('（截至最后随访，生存曲线尚未下降至 50%）')).not.toBeInTheDocument()
  })

  it('shows an unreached reverse-KM median follow-up explicitly', () => {
    render(<ResultSummary locale="zh" row={{ ...row, median_followup_months: null }} />)

    expect(screen.getByText('中位观察随访时间').parentElement).toHaveTextContent('未达到')
  })
})
