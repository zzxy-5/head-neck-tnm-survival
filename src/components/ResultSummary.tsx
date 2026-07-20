import { localizeValue, t, type Locale } from '../i18n'
import { formatFixed, formatMedian, matchingLabel } from '../presentation'
import type { LookupRow } from '../types'

interface ResultSummaryProps {
  locale: Locale
  row: LookupRow
}

const qualityCopy = {
  stable: 'quality.stable',
  small_sample: 'quality.small',
  very_small_sample: 'quality.verySmall',
} as const

function Detail({ label, value, detail }: { label: string; value: string | number; detail?: string }) {
  return (
    <div className="result-detail">
      <dt>{label}</dt>
      <dd>{value}</dd>
      {detail ? <dd className="result-detail__interval">{detail}</dd> : null}
    </div>
  )
}

export function ResultSummary({ locale, row }: ResultSummaryProps) {
  const fixed = (['12', '36', '60'] as const).map((month) => ({ month, ...formatFixed(row.fixed_survival[month], locale) }))
  const stage = [row.t_stage, row.n_stage, row.m_stage].map((value) => localizeValue(locale, value)).join(' / ')

  return (
    <section aria-label={t(locale, 'result.region')} className="result-summary">
      <section aria-label={t(locale, 'result.matchedRegion')} className="result-summary__provenance">
        <h2>{t(locale, 'result.matchedTitle')}</h2>
        <dl className="result-grid">
          <Detail label={t(locale, 'result.cohortYears')} value="2010-2017" />
          <Detail label={t(locale, 'result.stageSource')} value={localizeValue(locale, row.stage_source)} />
          <Detail label={t(locale, 'result.matchUsed')} value={matchingLabel(row.matching_level, locale)} />
          <Detail label={t(locale, 'result.sex')} value={localizeValue(locale, row.sex)} />
          <Detail label={t(locale, 'result.site')} value={localizeValue(locale, row.site)} />
          <Detail label={t(locale, 'result.histology')} value={localizeValue(locale, row.histology_group)} />
          <Detail label={t(locale, 'result.ageGroup')} value={localizeValue(locale, row.age_group)} />
          <Detail label={t(locale, 'result.stage')} value={stage} />
        </dl>
      </section>
      <section aria-labelledby="outcome-summary-heading" className="result-summary__outcomes">
        <h2 id="outcome-summary-heading">{t(locale, 'result.outcomes')}</h2>
        <dl className="result-grid result-grid--outcomes">
          <Detail label={t(locale, 'result.referenceGroup')} value={row.sample_size} />
          <Detail label={t(locale, 'result.deaths')} value={row.event_count} />
          <Detail label={t(locale, 'result.censored')} value={row.censor_count} />
            <Detail
              detail={
                row.median_survival_months === null
                  ? t(locale, 'result.medianOsUnreached')
                  : undefined
              }
              label={t(locale, 'result.medianOs')}
              value={formatMedian(row.median_survival_months, locale)}
            />
          <Detail label={t(locale, 'result.medianFollowup')} value={formatMedian(row.median_followup_months, locale)} />
          {fixed.map(({ month, value, interval }) => (
            <Detail key={month} label={locale === 'zh' ? `${Number(month) / 12} 年总生存率` : `${Number(month) / 12}-${t(locale, 'result.yearOsSuffix')}`} value={value} detail={interval} />
          ))}
        </dl>
        <p className={`quality-notice quality-notice--${row.data_quality_flag}`}>{t(locale, qualityCopy[row.data_quality_flag])}</p>
      </section>
    </section>
  )
}
