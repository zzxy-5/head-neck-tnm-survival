import { describe, expect, it } from 'vitest'

import { ageGroups, resolveLookup, tnmCandidateKeys } from './lookup'
import type { LookupArtifact, LookupRow } from './types'

const query = {
  sex: 'Male',
  site: 'Tongue',
  histology_group: 'SCC',
  age: 56,
  t_stage: 'T2',
  n_stage: 'N1',
  m_stage: 'M0' as const,
}

function fixtureRow(key: string, sampleSize: number, matchingLevel: string): LookupRow {
  return {
    key,
    cohort_type: 'tnm_2010_2017',
    stage_source: 'fixture',
    matching_level: matchingLevel,
    sex: 'Any',
    site: 'Tongue',
    histology_group: 'SCC',
    age_group: '50-59',
    t_stage: 'T2',
    n_stage: 'N1',
    m_stage: 'M0',
    sample_size: sampleSize,
    event_count: 0,
    censor_count: sampleSize,
    median_survival_months: null,
    median_followup_months: 0,
    maximum_followup_months: 0,
    fixed_survival: {
      '12': { estimate: null, confidence_interval: null, status: 'not_estimable' },
      '36': { estimate: null, confidence_interval: null, status: 'not_estimable' },
      '60': { estimate: null, confidence_interval: null, status: 'not_estimable' },
    },
    curve_months: [0],
    curve_survival_probs: [1],
    censor_months: [],
    risk_table_months: [0],
    risk_table_counts: [sampleSize],
    data_quality_flag: sampleSize >= 50 ? 'stable' : 'small_sample',
  }
}

function fixtureArtifact(rows: LookupRow[]): LookupArtifact {
  return {
    site: 'Tongue',
    thresholds: { minimum_sample: 20, stable_sample: 50 },
    rows,
    index: Object.fromEntries(rows.map((row, index) => [row.key, index])),
  }
}

describe('TNM lookup key resolution', () => {
  it('mirrors the Python 11-level fallback order without MX', () => {
    expect(tnmCandidateKeys(query)).toEqual([
      'full|Male|Tongue|SCC|50-59|T2|N1|M0',
      'no_sex|Any|Tongue|SCC|50-59|T2|N1|M0',
      'site_histology_coarse_age|Any|Tongue|SCC|<60|T2|N1|M0',
      'site_histology_tnm|Any|Tongue|SCC|Any|T2|N1|M0',
      'site_histology_m|Any|Tongue|SCC|Any|Any|Any|M0',
      'site_histology|Any|Tongue|SCC|Any|Any|Any|Any',
      'no_histology|Any|Tongue|Any|50-59|T2|N1|M0',
      'coarse_age|Any|Tongue|Any|<60|T2|N1|M0',
      'site_tnm|Any|Tongue|Any|Any|T2|N1|M0',
      'site_m|Any|Tongue|Any|Any|Any|Any|M0',
      'site_only|Any|Tongue|Any|Any|Any|Any|Any',
    ])
    expect(tnmCandidateKeys(query).every((key) => key.includes('|Tongue|'))).toBe(true)
    expect(tnmCandidateKeys(query).some((key) => key.includes('MX'))).toBe(false)
  })

  it.each(['M1', 'Unknown'] as const)('generates the complete key set for %s', (mStage) => {
    const keys = tnmCandidateKeys({ ...query, m_stage: mStage })

    expect(keys).toHaveLength(11)
    expect(keys[0]).toBe(`full|Male|Tongue|SCC|50-59|T2|N1|${mStage}`)
    expect(keys[4]).toBe(`site_histology_m|Any|Tongue|SCC|Any|Any|Any|${mStage}`)
    expect(keys[9]).toBe(`site_m|Any|Tongue|Any|Any|Any|Any|${mStage}`)
    expect(keys.every((key) => key.endsWith(`|${mStage}`) || key.endsWith('|Any'))).toBe(true)
  })

  it('throws explicitly when runtime input contains unsupported MX', () => {
    const invalidQuery = { ...query, m_stage: 'MX' } as unknown as typeof query

    expect(() => tnmCandidateKeys(invalidQuery)).toThrow('Unsupported M stage: MX')
  })

  it('skips an undersized earlier candidate and returns the first qualifying fallback', () => {
    const keys = tnmCandidateKeys(query)
    const artifact = fixtureArtifact([
      fixtureRow(keys[0], 19, 'full'),
      fixtureRow(keys[6], 31, 'no_histology'),
      fixtureRow(keys[10], 500, 'site_only'),
    ])

    expect(resolveLookup(artifact, query)?.matching_level).toBe('no_histology')
  })

  it('returns null when every candidate is below the public threshold', () => {
    const artifact = fixtureArtifact([fixtureRow(tnmCandidateKeys(query)[10], 19, 'site_only')])

    expect(resolveLookup(artifact, query)).toBeNull()
  })

  it('validates age and maps boundary values', () => {
    expect([0, 39, 40, 49, 50, 59, 60, 69, 70, 79, 80, 120].map(ageGroups)).toEqual([
      { fine: '<40', coarse: '<60' },
      { fine: '<40', coarse: '<60' },
      { fine: '40-49', coarse: '<60' },
      { fine: '40-49', coarse: '<60' },
      { fine: '50-59', coarse: '<60' },
      { fine: '50-59', coarse: '<60' },
      { fine: '60-69', coarse: '60-69' },
      { fine: '60-69', coarse: '60-69' },
      { fine: '70-79', coarse: '70+' },
      { fine: '70-79', coarse: '70+' },
      { fine: '80+', coarse: '70+' },
      { fine: '80+', coarse: '70+' },
    ])
    expect(() => ageGroups(56.5)).toThrow('whole number')
    expect(() => ageGroups(-1)).toThrow('0 to 120')
  })
})
