import type { LookupArtifact, LookupRow, MStage } from './types'

export interface TNMQuery {
  sex: string
  site: string
  histology_group: string
  age: number
  t_stage: string
  n_stage: string
  m_stage: MStage
}

export function ageGroups(age: number): { fine: string; coarse: string } {
  if (!Number.isInteger(age) || age < 0 || age > 120) {
    throw new Error('Age must be a whole number from 0 to 120')
  }

  const fine =
    age < 40
      ? '<40'
      : age < 50
        ? '40-49'
        : age < 60
          ? '50-59'
          : age < 70
            ? '60-69'
            : age < 80
              ? '70-79'
              : '80+'
  const coarse = age < 60 ? '<60' : age < 70 ? '60-69' : '70+'
  return { fine, coarse }
}

export function tnmCandidateKeys(query: TNMQuery): string[] {
  const { fine, coarse } = ageGroups(query.age)
  const { sex, site, histology_group: histology, t_stage: tStage, n_stage: nStage, m_stage: mStage } = query

  if (mStage !== 'M0' && mStage !== 'M1' && mStage !== 'Unknown') {
    throw new Error(`Unsupported M stage: ${mStage}`)
  }

  return [
    ['full', sex, site, histology, fine, tStage, nStage, mStage],
    ['no_sex', 'Any', site, histology, fine, tStage, nStage, mStage],
    ['site_histology_coarse_age', 'Any', site, histology, coarse, tStage, nStage, mStage],
    ['site_histology_tnm', 'Any', site, histology, 'Any', tStage, nStage, mStage],
    ['site_histology_m', 'Any', site, histology, 'Any', 'Any', 'Any', mStage],
    ['site_histology', 'Any', site, histology, 'Any', 'Any', 'Any', 'Any'],
    ['no_histology', 'Any', site, 'Any', fine, tStage, nStage, mStage],
    ['coarse_age', 'Any', site, 'Any', coarse, tStage, nStage, mStage],
    ['site_tnm', 'Any', site, 'Any', 'Any', tStage, nStage, mStage],
    ['site_m', 'Any', site, 'Any', 'Any', 'Any', 'Any', mStage],
    ['site_only', 'Any', site, 'Any', 'Any', 'Any', 'Any', 'Any'],
  ].map((segments) => segments.join('|'))
}

export function resolveLookup(
  artifact: LookupArtifact,
  query: TNMQuery,
  minimumSample = artifact.thresholds.minimum_sample,
): LookupRow | null {
  for (const key of tnmCandidateKeys(query)) {
    const position = artifact.index[key]
    if (position === undefined) continue

    const row = artifact.rows[position]
    if (row !== undefined && row.key === key && row.sample_size >= minimumSample) {
      return row
    }
  }

  return null
}
