import { existsSync, readdirSync, readFileSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

const DATA_DIRECTORY = join(process.cwd(), 'public', 'data')
const ADDED_SITE_COUNTS = {
  'Nose, Nasal Cavity and Middle Ear': 4_969,
  Larynx: 21_786,
  Thyroid: 99_715,
} as const

type FixedEstimate = {
  status: 'estimable' | 'not_estimable'
  estimate: number | null
  confidence_interval: [number, number] | null
}

type ArtifactRow = {
  key: string
  maximum_followup_months: number
  m_stage: string
  fixed_survival: Record<'12' | '36' | '60', FixedEstimate>
  curve_months: number[]
}

type LookupShard = {
  site: string
  rows: ArtifactRow[]
  index: Record<string, number>
}

function readJson<T>(relativePath: string): T {
  return JSON.parse(readFileSync(join(DATA_DIRECTORY, relativePath), 'utf8')) as T
}

function jsonFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name)
    if (entry.isDirectory()) return jsonFiles(path)
    return entry.name.endsWith('.json') ? [relative(DATA_DIRECTORY, path)] : []
  })
}

describe('real static TNM artifacts', () => {
  it('contains exactly the 13 site shards and reconciles their cohort counts', () => {
    const metadata = readJson<{
      eligible_record_count: number
      site_record_counts: Record<string, number>
    }>('metadata.json')
    const manifest = readJson<{ sites: Record<string, string> }>('site_manifest.json')

    expect(metadata.eligible_record_count).toBe(211_160)
    expect(Object.keys(manifest.sites)).toHaveLength(13)
    expect(metadata.site_record_counts).toMatchObject(ADDED_SITE_COUNTS)
    expect(Object.values(metadata.site_record_counts).reduce((sum, count) => sum + count, 0)).toBe(211_160)

    const expectedFiles = [
      'metadata.json',
      'options.json',
      'site_manifest.json',
      ...Object.values(manifest.sites).map((filename) => join('lookup', filename)),
    ].sort()
    expect(jsonFiles(DATA_DIRECTORY).sort()).toEqual(expectedFiles)

    for (const [site, filename] of Object.entries(manifest.sites)) {
      const shard = readJson<LookupShard>(join('lookup', filename))
      expect(shard.site).toBe(site)
      expect(shard.rows.length).toBeGreaterThan(0)

      for (const [key, position] of Object.entries(shard.index)) {
        expect(shard.rows[position]?.key).toBe(key)
      }
    }
  })

  it('contains only supported TNM content and consistent survival estimates', () => {
    const manifest = readJson<{ sites: Record<string, string> }>('site_manifest.json')
    const options = readJson<{ m_stages: string[] }>('options.json')
    const payloads = [
      readFileSync(join(DATA_DIRECTORY, 'metadata.json'), 'utf8'),
      readFileSync(join(DATA_DIRECTORY, 'options.json'), 'utf8'),
      readFileSync(join(DATA_DIRECTORY, 'site_manifest.json'), 'utf8'),
    ]

    expect(options.m_stages).toEqual(['M0', 'M1', 'Unknown'])
    expect(existsSync(join(DATA_DIRECTORY, 'tnm_lookup.json'))).toBe(false)

    for (const filename of Object.values(manifest.sites)) {
      const artifactPath = join('lookup', filename)
      const shardText = readFileSync(join(DATA_DIRECTORY, artifactPath), 'utf8')
      const shard = JSON.parse(shardText) as LookupShard
      payloads.push(shardText)

      for (const row of shard.rows) {
        expect(row.m_stage).not.toBe('MX')
        expect(row.curve_months.at(-1)).toBe(row.maximum_followup_months)

        for (const [horizon, estimate] of Object.entries(row.fixed_survival)) {
          const followupSupportsHorizon = row.maximum_followup_months >= Number(horizon)
          if (estimate.status === 'estimable') {
            expect(followupSupportsHorizon).toBe(true)
            expect(estimate.estimate).not.toBeNull()
            expect(estimate.confidence_interval).not.toBeNull()
            const [lower, upper] = estimate.confidence_interval!
            expect(lower).toBeLessThanOrEqual(estimate.estimate!)
            expect(estimate.estimate!).toBeLessThanOrEqual(upper)
          } else {
            expect(followupSupportsHorizon).toBe(false)
            expect(estimate.estimate).toBeNull()
            expect(estimate.confidence_interval).toBeNull()
          }
        }
      }
    }

    const serializedArtifacts = payloads.join('\n').toLowerCase()
    expect(serializedArtifacts).not.toContain('"mx"')
    expect(serializedArtifacts).not.toContain('summary_stage')
    expect(serializedArtifacts).not.toContain('eod')
    expect(serializedArtifacts).not.toContain('curve_ci_lower_probs')
    expect(serializedArtifacts).not.toContain('curve_ci_upper_probs')
  })
})
