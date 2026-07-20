import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { AppHeader } from './components/AppHeader'
import { CaveatBox } from './components/CaveatBox'
import { FilterPanel, type FilterOptions } from './components/FilterPanel'
import { ResultSummary } from './components/ResultSummary'
import { SurvivalChart } from './components/SurvivalChart'
import { loadCoreData, loadSiteShard } from './data'
import { t, type Locale } from './i18n'
import { resolveLookup, type TNMQuery } from './lookup'
import type { CoreData, LookupArtifact } from './types'
import './styles.css'

function optionsFrom(core: CoreData): FilterOptions {
  const options = core.options as Partial<FilterOptions>
  return {
    sexes: options.sexes ?? [],
    sites: options.sites ?? [],
    histology_groups: options.histology_groups ?? [],
    t_stages: options.t_stages ?? [],
    n_stages: options.n_stages ?? [],
    m_stages: options.m_stages?.filter((stage) => stage !== 'MX') ?? [],
  }
}

function Status({ className, children }: { className?: string; children: ReactNode }) {
  return <div aria-live="polite" className={`status-state ${className ?? ''}`} role="status"><p>{children}</p></div>
}

export default function App() {
  const [locale, setLocale] = useState<Locale>('zh')
  const [core, setCore] = useState<CoreData | null>(null)
  const [coreError, setCoreError] = useState<string | null>(null)
  const [site, setSite] = useState('')
  const [artifact, setArtifact] = useState<LookupArtifact | null>(null)
  const [shardError, setShardError] = useState<string | null>(null)
  const [query, setQuery] = useState<TNMQuery | null>(null)
  const cache = useRef(new Map<string, LookupArtifact>())
  const inFlight = useRef(new Map<string, Promise<LookupArtifact>>())

  useEffect(() => {
    document.documentElement.lang = locale
    document.title = t(locale, 'header.title')
  }, [locale])

  useEffect(() => {
    let active = true
    void loadCoreData().then(
      (next) => { if (active) setCore(next) },
      (error: unknown) => { if (active) setCoreError(error instanceof Error ? error.message : t(locale, 'status.error')) },
    )
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (!core || site === '') {
      setArtifact(null)
      setShardError(null)
      return
    }
    const cached = cache.current.get(site)
    if (cached) {
      setArtifact(cached)
      setShardError(null)
      return
    }
    let active = true
    setArtifact(null)
    setShardError(null)
    let request = inFlight.current.get(site)
    if (!request) {
      request = loadSiteShard(site, core.manifest)
      inFlight.current.set(site, request)
      void request.then(
        () => { if (inFlight.current.get(site) === request) inFlight.current.delete(site) },
        () => { if (inFlight.current.get(site) === request) inFlight.current.delete(site) },
      )
    }
    void request.then(
      (next) => {
        cache.current.set(site, next)
        if (active) setArtifact(next)
      },
      (error: unknown) => { if (active) setShardError(error instanceof Error ? error.message : t(locale, 'status.error')) },
    )
    return () => { active = false }
  }, [core, site])

  const result = useMemo(() => {
    if (!artifact || !query || artifact.site !== query.site) return null
    return resolveLookup(artifact, query)
  }, [artifact, query])

  const hasSelectedSite = site !== ''
  return (
    <div className="app-shell">
      <div className="app-header-band"><div className="page-width"><AppHeader locale={locale} onLocaleChange={setLocale} /></div></div>
      <main className="cohort-panel page-width">
        <section aria-labelledby="method-heading" className="method-note">
          <p className="section-label">{t(locale, 'method.active')}</p>
          <h2 id="method-heading">{t(locale, 'method.tnmTitle')}</h2>
          <p>{t(locale, 'method.tnmDescription')}</p>
        </section>
        {coreError ? <Status className="status-state--error">{coreError}</Status> : null}
        {!core && !coreError ? <Status>{t(locale, 'status.loading')}</Status> : null}
        {core ? (
          <div className="research-workspace">
            <aside aria-label={t(locale, 'filter.region')} className="filter-region">
              <div className="panel-heading"><p className="section-label">{t(locale, 'filter.eyebrow')}</p><h2>{t(locale, 'filter.heading')}</h2></div>
              <FilterPanel locale={locale} onQueryChange={setQuery} onSiteChange={setSite} options={optionsFrom(core)} />
            </aside>
            <section aria-label={t(locale, 'result.region')} className="result-region">
              {shardError ? <Status className="status-state--error">{shardError}</Status> : null}
              {!shardError && hasSelectedSite && !artifact ? <Status>{t(locale, 'status.loading')}</Status> : null}
              {!shardError && artifact && !query ? <div className="result-intro"><p className="section-label">{t(locale, 'intro.eyebrow')}</p><h2>{t(locale, 'intro.title')}</h2><p>{t(locale, 'intro.description')}</p></div> : null}
              {!shardError && artifact && query && !result ? <Status className="status-state--empty">{t(locale, 'status.emptyDetailed')}</Status> : null}
              {result ? <><ResultSummary locale={locale} row={result} /><SurvivalChart locale={locale} row={result} /><CaveatBox locale={locale} /></> : null}
            </section>
          </div>
        ) : null}
      </main>
      <footer className="app-footer"><div className="page-width">{t(locale, 'footer')}</div></footer>
    </div>
  )
}
