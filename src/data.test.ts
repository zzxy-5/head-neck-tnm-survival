import { describe, expect, it, vi } from 'vitest'

import { loadCoreData, loadSiteShard } from './data'
import type { LookupArtifact, SiteManifest } from './types'

const manifest: SiteManifest = { sites: { 'Oral Tongue': 'oral-tongue.json' } }

const coreResponses = {
  'data/metadata.json': { eligible_record_count: 106952 },
  'data/options.json': { sites: ['Oral Tongue'], m_stages: ['M0', 'M1', 'Unknown'] },
  'data/site_manifest.json': manifest,
}

function fetcherFor(responses: Record<string, unknown>) {
  return vi.fn<typeof fetch>(async (input) => {
    const url = String(input)
    const key = Object.keys(responses).find((path) => url.endsWith(path))
    if (key === undefined) return new Response(null, { status: 404 })
    return new Response(JSON.stringify(responses[key]), {
      headers: { 'Content-Type': 'application/json' },
      status: 200,
    })
  })
}

describe('static data loading', () => {
  it('loads the three core files from the Vite base path and never requests retired artifacts', async () => {
    const fetcher = fetcherFor(coreResponses)

    const core = await loadCoreData(fetcher)

    expect(core.metadata).toEqual(coreResponses['data/metadata.json'])
    expect(core.options).toEqual(coreResponses['data/options.json'])
    expect(core.manifest).toEqual(manifest)
    expect(fetcher).toHaveBeenCalledTimes(3)
    const urls = fetcher.mock.calls.map(([url]) => String(url))
    expect(urls).toEqual([
      `${import.meta.env.BASE_URL}data/metadata.json`,
      `${import.meta.env.BASE_URL}data/options.json`,
      `${import.meta.env.BASE_URL}data/site_manifest.json`,
    ])
    expect(urls.join('\n')).not.toMatch(/summary|eod/i)
  })

  it('maps a requested site through the manifest to its lookup shard', async () => {
    const artifact: LookupArtifact = {
      site: 'Oral Tongue',
      thresholds: { minimum_sample: 20, stable_sample: 50 },
      rows: [],
      index: {},
    }
    const fetcher = fetcherFor({ 'data/lookup/oral-tongue.json': artifact })

    await expect(loadSiteShard('Oral Tongue', manifest, fetcher)).resolves.toEqual(artifact)
    expect(fetcher).toHaveBeenCalledWith(`${import.meta.env.BASE_URL}data/lookup/oral-tongue.json`)
  })

  it('names the missing site shard in a readable error', async () => {
    const fetcher = vi.fn().mockResolvedValue({ ok: false, status: 404 })

    await expect(loadSiteShard('Oral Tongue', manifest, fetcher)).rejects.toThrow(
      'oral-tongue.json (404)',
    )
  })
})
