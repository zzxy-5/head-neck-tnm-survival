import { RotateCcw } from 'lucide-react'
import { useEffect, useState } from 'react'

import { localizeValue, t, type Locale } from '../i18n'
import type { MStage } from '../types'
import type { TNMQuery } from '../lookup'

export interface FilterOptions {
  sexes: string[]
  sites: string[]
  histology_groups: string[]
  t_stages: string[]
  n_stages: string[]
  m_stages: string[]
}

interface FilterPanelProps {
  locale: Locale
  options: FilterOptions
  onQueryChange: (query: TNMQuery | null) => void
  onSiteChange: (site: string) => void
}

interface FormValues {
  sex: string
  site: string
  histology: string
  age: string
  tStage: string
  nStage: string
  mStage: string
}

const emptyValues: FormValues = {
  sex: '', site: '', histology: '', age: '', tStage: '', nStage: '', mStage: '',
}

function SelectField({
  id, label, locale, options, value, onChange,
}: {
  id: string
  label: string
  locale: Locale
  options: string[]
  value: string
  onChange: (value: string) => void
}) {
  return (
    <div className="filter-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} onChange={(event) => onChange(event.target.value)} value={value}>
        <option value="">{t(locale, 'filter.select')}</option>
        {options.map((option) => (
          <option key={option} value={option}>{localizeValue(locale, option)}</option>
        ))}
      </select>
      <span aria-hidden="true" className="filter-field__message" />
    </div>
  )
}

function asMStage(value: string): MStage | null {
  return value === 'M0' || value === 'M1' || value === 'Unknown' ? value : null
}

export function FilterPanel({ locale, options, onQueryChange, onSiteChange }: FilterPanelProps) {
  const [values, setValues] = useState<FormValues>(emptyValues)
  const ageNumber = Number(values.age)
  const ageInvalid = values.age !== '' && (!Number.isInteger(ageNumber) || ageNumber < 0 || ageNumber > 120)
  const mStage = asMStage(values.mStage)
  const complete = values.sex !== '' && values.site !== '' && values.histology !== '' && values.age !== '' && !ageInvalid && values.tStage !== '' && values.nStage !== '' && mStage !== null

  useEffect(() => {
    onSiteChange(values.site)
  }, [onSiteChange, values.site])

  useEffect(() => {
    if (!complete || mStage === null) {
      onQueryChange(null)
      return
    }
    onQueryChange({
      sex: values.sex,
      site: values.site,
      histology_group: values.histology,
      age: ageNumber,
      t_stage: values.tStage,
      n_stage: values.nStage,
      m_stage: mStage,
    })
  }, [ageNumber, complete, mStage, onQueryChange, values])

  function update(field: keyof FormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  return (
    <form className="filter-panel" noValidate onSubmit={(event) => event.preventDefault()}>
      <div className="filter-panel__fields">
        <SelectField id="tnm-sex" label={t(locale, 'filter.sex')} locale={locale} onChange={(value) => update('sex', value)} options={options.sexes} value={values.sex} />
        <SelectField id="tnm-site" label={t(locale, 'filter.site')} locale={locale} onChange={(value) => update('site', value)} options={options.sites} value={values.site} />
        <SelectField id="tnm-histology" label={t(locale, 'filter.histology')} locale={locale} onChange={(value) => update('histology', value)} options={options.histology_groups} value={values.histology} />
        <div className="filter-field">
          <label htmlFor="tnm-age">{t(locale, 'filter.age')}</label>
          <input aria-describedby="tnm-age-error" aria-invalid={ageInvalid} id="tnm-age" inputMode="numeric" max={120} min={0} onChange={(event) => update('age', event.target.value)} step={1} type="number" value={values.age} />
          <span className="filter-field__message" id="tnm-age-error">{ageInvalid ? t(locale, 'filter.ageError') : ''}</span>
        </div>
        <SelectField id="tnm-t-stage" label={t(locale, 'filter.tStage')} locale={locale} onChange={(value) => update('tStage', value)} options={options.t_stages} value={values.tStage} />
        <SelectField id="tnm-n-stage" label={t(locale, 'filter.nStage')} locale={locale} onChange={(value) => update('nStage', value)} options={options.n_stages} value={values.nStage} />
        <SelectField id="tnm-m-stage" label={t(locale, 'filter.mStage')} locale={locale} onChange={(value) => update('mStage', value)} options={options.m_stages.filter((stage) => stage !== 'MX')} value={values.mStage} />
      </div>
      <div className="filter-panel__actions">
        <button aria-label={t(locale, 'filter.reset')} onClick={() => setValues(emptyValues)} title={t(locale, 'filter.reset')} type="button">
          <RotateCcw aria-hidden="true" size={18} />
        </button>
      </div>
    </form>
  )
}
