export type QualityFlag = 'stable' | 'small_sample' | 'very_small_sample'
export type EstimateStatus = 'estimable' | 'not_estimable'
export type MStage = 'M0' | 'M1' | 'Unknown'

export interface FixedEstimate {
  estimate: number | null
  confidence_interval: [number, number] | null
  status: EstimateStatus
}

export interface LookupRow {
  key: string
  cohort_type: string
  stage_source: string
  matching_level: string
  sex: string
  site: string
  histology_group: string
  age_group: string
  t_stage: string
  n_stage: string
  m_stage: MStage
  sample_size: number
  event_count: number
  censor_count: number
  median_survival_months: number | null
  median_followup_months: number | null
  maximum_followup_months: number
  fixed_survival: Record<'12' | '36' | '60', FixedEstimate>
  curve_months: number[]
  curve_survival_probs: number[]
  censor_months: number[]
  risk_table_months: number[]
  risk_table_counts: number[]
  data_quality_flag: QualityFlag
}

export interface LookupArtifact {
  site: string
  thresholds: {
    minimum_sample: number
    stable_sample: number
  }
  rows: LookupRow[]
  index: Record<string, number>
}

export interface SiteManifest {
  sites: Record<string, string>
}

export interface CoreData {
  metadata: Record<string, unknown>
  options: Record<string, unknown>
  manifest: SiteManifest
}
