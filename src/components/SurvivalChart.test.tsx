import { cleanup, render, screen, within } from '@testing-library/react'
import { afterEach, describe, expect, it } from 'vitest'

import type { LookupRow } from '../types'
import { SurvivalChart } from './SurvivalChart'

afterEach(cleanup)

const row = {
  sample_size: 42,
  median_survival_months: 18,
  median_followup_months: 28.2,
  curve_months: [0, 6, 12, 24, 34],
  curve_survival_probs: [1, 0.9, 0.8, 0.7, 0.64],
  censor_months: [10, 12, 30],
  risk_table_months: [0, 12, 24, 36, 48, 60],
  risk_table_counts: [42, 36, 25, 0, 0, 0],
  maximum_followup_months: 34,
} as LookupRow

describe('SurvivalChart', () => {
  it('renders the stored step curve, labels, and all risk entries without confidence shading', () => {
    const { container } = render(<SurvivalChart locale="en" row={row} />)

    const svg = screen.getByRole('img', { name: 'Kaplan-Meier overall survival curve' })
    expect(svg).toHaveAttribute('viewBox', '0 0 960 520')
    expect(within(svg).getByText('Overall survival (%)')).toBeInTheDocument()
    expect(within(svg).getByText('Follow-up time')).toBeInTheDocument()
    expect(container.querySelectorAll('[data-testid="survival-path"]')).toHaveLength(1)
    expect(screen.queryByTestId('confidence-band')).not.toBeInTheDocument()
    expect(container.querySelector('.survival-chart__confidence')).toBeNull()
    expect(screen.getByRole('heading', { name: 'Overall survival curve' })).toBeInTheDocument()
    expect(screen.getByText('Patients included: 42')).toBeInTheDocument()
    expect(screen.getByText('Median follow-up: 28.2 months')).toBeInTheDocument()

    const survivalPath = container.querySelector('[data-testid="survival-path"]')
    expect(survivalPath?.getAttribute('d')).toContain('H')
    expect(survivalPath?.getAttribute('d')).not.toContain('NaN')
    expect(survivalPath?.getAttribute('data-maximum-month')).toBe('34')
    expect(survivalPath).toHaveAttribute('stroke', 'var(--primary-dark)')
    expect(survivalPath).toHaveAttribute('stroke-width', '2.25')
    expect(survivalPath).toHaveAttribute('vector-effect', 'non-scaling-stroke')
    expect(survivalPath).not.toHaveAttribute('filter')

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
    const legend = screen.getByText('Censored').parentElement
    expect(legend).toHaveClass('survival-chart__legend')
    expect(legend).not.toHaveAttribute('title')

    const medianMarker = screen.getByTestId('median-survival-marker')
    expect(medianMarker).toHaveAttribute('data-median-month', '18')
    expect(within(svg).getByText('Median overall survival: 18.0 months')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: 'Number at risk' })
    expect(within(table).getByRole('rowheader', { name: 'Follow-up time (months)' })).toBeInTheDocument()
    expect(within(table).getByRole('rowheader', { name: 'Number at risk' })).toBeInTheDocument()
    for (const month of row.risk_table_months) {
      expect(within(table).getByRole('columnheader', { name: String(month) })).toBeInTheDocument()
    }
    for (const count of [42, 36, 25]) {
      expect(within(table).getByRole('cell', { name: String(count) })).toBeInTheDocument()
    }
  })

  it('displays the complete stored curve when follow-up exceeds 120 months', () => {
    const longRow = {
      ...row,
      maximum_followup_months: 167,
      curve_months: [0, 60, 120, 167],
      curve_survival_probs: [1, 0.7, 0.5, 0.4],
    }
    const { container } = render(<SurvivalChart locale="en" row={longRow} />)

    expect(container.querySelector('[data-testid="survival-path"]')).toHaveAttribute(
      'data-maximum-month',
      '167',
    )
    expect(container.querySelector('[data-testid="survival-path"]')?.getAttribute('d')).toContain(
      'H 924',
    )
    expect(within(screen.getByRole('img', { name: 'Kaplan-Meier overall survival curve' })).getByText('167')).toBeInTheDocument()
  })

  it('does not extend a shorter stored curve to 60 months', () => {
    const { container } = render(<SurvivalChart locale="en" row={row} />)

    expect(container.querySelector('[data-testid="survival-path"]')).toHaveAttribute(
      'data-maximum-month',
      '34',
    )
  })

  it('marks only the 12-month tick as secondary and exposes a readable mobile font contract', () => {
    const longRow = {
      ...row,
      maximum_followup_months: 167,
      curve_months: [0, 60, 120, 167],
      curve_survival_probs: [1, 0.7, 0.5, 0.4],
    }
    const { container } = render(<SurvivalChart locale="en" row={longRow} />)

    const svg = screen.getByRole('img', { name: 'Kaplan-Meier overall survival curve' })
    expect(svg).toHaveAttribute('data-mobile-font-size', '32')
    expect(container.querySelector('[data-mobile-secondary="true"]')).toHaveTextContent('12')
    for (const requiredTick of ['0', '36', '60', '167']) {
      const tick = Array.from(container.querySelectorAll('.survival-chart__x-tick-label')).find(
        (element) => element.textContent === requiredTick,
      )
      expect(tick).not.toHaveAttribute('data-mobile-secondary', 'true')
    }
  })

  it('localizes chart and risk-table labels in Chinese', () => {
    const { container } = render(<SurvivalChart locale="zh" row={row} />)

    const svg = screen.getByRole('img', { name: 'Kaplan-Meier 总生存曲线' })
    expect(within(svg).getByText('总生存率（%）')).toBeInTheDocument()
    expect(within(svg).getByText('随访时间')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '总体生存曲线' })).toBeInTheDocument()
    expect(screen.getByText('纳入患者：42例')).toBeInTheDocument()
    expect(screen.getByText('中位随访时间：28.2个月')).toBeInTheDocument()
    expect(screen.getByText('删失')).toBeInTheDocument()

    const table = screen.getByRole('table', { name: '风险集人数' })
    expect(within(table).getByRole('rowheader', { name: '随访时间（月）' })).toBeInTheDocument()
    expect(within(table).getByRole('rowheader', { name: '风险集人数' })).toBeInTheDocument()
    expect(container.querySelector('[data-testid="survival-path"]')).toHaveAttribute(
      'data-maximum-month',
      '34',
    )
  })

  it('reports an unreached median follow-up without inventing a month value', () => {
    render(<SurvivalChart locale="zh" row={{ ...row, median_followup_months: null }} />)

    expect(screen.getByText('中位随访时间：未达到')).toBeInTheDocument()
  })

  it('keeps the censor legend when no censor marks are stored', () => {
    const { container } = render(
      <SurvivalChart locale="en" row={{ ...row, censor_months: [] }} />,
    )

    expect(container.querySelectorAll('[data-testid="censor-mark"]')).toHaveLength(0)
    expect(screen.getByText('Censored')).toBeInTheDocument()
  })

  it('labels an unreached median overall survival without drawing a false marker', () => {
    const { container } = render(<SurvivalChart locale="zh" row={{ ...row, median_survival_months: null }} />)

    expect(screen.queryByTestId('median-survival-marker')).not.toBeInTheDocument()
    expect(within(screen.getByRole('img', { name: 'Kaplan-Meier 总生存曲线' })).getByText('中位生存期：未达到')).toBeInTheDocument()
    expect(container.querySelectorAll('.survival-chart__median-guide')).toHaveLength(0)
  })
})
