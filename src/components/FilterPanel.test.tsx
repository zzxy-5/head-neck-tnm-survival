import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FilterPanel } from './FilterPanel'

afterEach(cleanup)

const options = {
  sexes: ['Female', 'Male'],
  sites: ['Tongue', 'Larynx'],
  histology_groups: ['8050-8089: squamous cell neoplasms'],
  t_stages: ['T0', 'T1', 'T2', 'T3', 'T4', 'Unknown'],
  n_stages: ['N0', 'N1', 'N2', 'N3', 'Unknown'],
  m_stages: ['M0', 'M1', 'Unknown'],
}

describe('FilterPanel', () => {
  it('renders the focused seven fields and never offers Summary stage or MX', () => {
    render(<FilterPanel locale="zh" options={options} onQueryChange={vi.fn()} onSiteChange={vi.fn()} />)

    for (const label of ['性别', '解剖部位', '组织学类型', '诊断年龄', 'T 分期', 'N 分期', 'M 分期']) {
      expect(screen.getByLabelText(label)).toBeInTheDocument()
    }
    expect(screen.queryByLabelText('总体分期')).not.toBeInTheDocument()
    expect(screen.getByLabelText('M 分期')).toHaveTextContent('M0')
    expect(screen.getByLabelText('M 分期')).toHaveTextContent('M1')
    expect(Array.from(screen.getByLabelText('M 分期').querySelectorAll('option')).map((option) => option.getAttribute('value'))).toContain('Unknown')
    expect(screen.getByLabelText('M 分期')).not.toHaveTextContent('MX')
  })

  it('emits a query automatically only after all fields form a valid TNM query', async () => {
    const user = userEvent.setup()
    const onQueryChange = vi.fn()
    const onSiteChange = vi.fn()
    render(<FilterPanel locale="zh" options={options} onQueryChange={onQueryChange} onSiteChange={onSiteChange} />)

    await user.selectOptions(screen.getByLabelText('性别'), 'Female')
    await user.selectOptions(screen.getByLabelText('解剖部位'), 'Tongue')
    await user.selectOptions(screen.getByLabelText('组织学类型'), '8050-8089: squamous cell neoplasms')
    await user.type(screen.getByLabelText('诊断年龄'), '55')
    await user.selectOptions(screen.getByLabelText('T 分期'), 'T2')
    await user.selectOptions(screen.getByLabelText('N 分期'), 'N1')
    await user.selectOptions(screen.getByLabelText('M 分期'), 'M0')

    expect(onSiteChange).toHaveBeenLastCalledWith('Tongue')
    expect(onQueryChange).toHaveBeenLastCalledWith({
      sex: 'Female', site: 'Tongue', histology_group: '8050-8089: squamous cell neoplasms',
      age: 55, t_stage: 'T2', n_stage: 'N1', m_stage: 'M0',
    })
  })

  it('keeps its selected raw values when the interface language changes', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<FilterPanel locale="zh" options={options} onQueryChange={vi.fn()} onSiteChange={vi.fn()} />)
    await user.selectOptions(screen.getByLabelText('性别'), 'Female')
    await user.selectOptions(screen.getByLabelText('解剖部位'), 'Tongue')
    rerender(<FilterPanel locale="en" options={options} onQueryChange={vi.fn()} onSiteChange={vi.fn()} />)

    expect(screen.getByLabelText('Sex')).toHaveValue('Female')
    expect(screen.getByLabelText('Anatomical site')).toHaveValue('Tongue')
  })
})
