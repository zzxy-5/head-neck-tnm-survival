import type { CoreData, LookupArtifact, SiteManifest } from './types'
import productionMetadata from '../public/data/metadata.json'

const DATA_VERSION = encodeURIComponent(productionMetadata.generated_at)

const dataPath = (filename: string) =>
  `${import.meta.env.BASE_URL}data/${filename}?v=${DATA_VERSION}`

async function loadJson<T>(filename: string, fetcher: typeof fetch): Promise<T> {
  const response = await fetcher(dataPath(filename))

  if (!response.ok) {
    throw new Error(`Unable to load ${filename} (${response.status})`)
  }

  return (await response.json()) as T
}

export async function loadCoreData(fetcher: typeof fetch = fetch): Promise<CoreData> {
  const [metadata, options, manifest] = await Promise.all([
    loadJson<Record<string, unknown>>('metadata.json', fetcher),
    loadJson<Record<string, unknown>>('options.json', fetcher),
    loadJson<SiteManifest>('site_manifest.json', fetcher),
  ])

  return { metadata, options, manifest }
}

export async function loadSiteShard(
  site: string,
  manifest: SiteManifest,
  fetcher: typeof fetch = fetch,
): Promise<LookupArtifact> {
  const shard = manifest.sites[site]
  if (shard === undefined) {
    throw new Error(`No lookup shard configured for ${site}`)
  }

  return loadJson<LookupArtifact>(`lookup/${shard}`, fetcher)
}
