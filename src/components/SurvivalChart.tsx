import { t, type Locale } from '../i18n'
import type { LookupRow } from '../types'
import { RiskTable } from './RiskTable'

interface SurvivalChartProps {
  locale: Locale
  row: LookupRow
}

const width = 960
const height = 520
const margin = { top: 40, right: 36, bottom: 78, left: 86 }
const plotWidth = width - margin.left - margin.right
const plotHeight = height - margin.top - margin.bottom

interface CurvePoint {
  month: number
  survival: number
}

interface CensorPoint extends CurvePoint {}

function supportedPoints(row: LookupRow): CurvePoint[] {
  const count = Math.min(row.curve_months.length, row.curve_survival_probs.length)
  return Array.from({ length: count }, (_, index) => ({
    month: row.curve_months[index],
    survival: row.curve_survival_probs[index],
  })).filter((point) => point.month <= row.maximum_followup_months)
}

function supportedCensorPoints(row: LookupRow, points: CurvePoint[]): CensorPoint[] {
  let curveIndex = 0

  return row.censor_months
    .filter((month) => month <= row.maximum_followup_months)
    .map((month) => {
      while (
        curveIndex + 1 < points.length
        && points[curveIndex + 1].month <= month
      ) {
        curveIndex += 1
      }
      return { month, survival: points[curveIndex]?.survival ?? 1 }
    })
}

function stepPath(
  points: CurvePoint[],
  x: (month: number) => number,
  y: (probability: number) => number,
): string {
  if (points.length === 0) return ''
  const commands = [`M ${x(points[0].month)} ${y(points[0].survival)}`]
  for (let index = 1; index < points.length; index += 1) {
    commands.push(`H ${x(points[index].month)}`)
    commands.push(`V ${y(points[index].survival)}`)
  }
  return commands.join(' ')
}

export function SurvivalChart({ locale, row }: SurvivalChartProps) {
  const points = supportedPoints(row)
  const xMaximum = Math.max(12, row.maximum_followup_months)
  const visiblePoints = points.filter((point) => point.month <= xMaximum)
  const censorPoints = supportedCensorPoints(row, visiblePoints)
  const visibleMaximum = visiblePoints.at(-1)?.month ?? 0
  const x = (month: number) => margin.left + (month / xMaximum) * plotWidth
  const y = (probability: number) => margin.top + (1 - probability) * plotHeight
  const survivalPath = stepPath(visiblePoints, x, y)
  const xTicks = Array.from(new Set([0, 12, 36, 60, xMaximum]))
    .filter((month) => month <= xMaximum)
    .sort((a, b) => a - b)
  const patientSummary = locale === 'zh'
    ? `${t(locale, 'chart.includedPatients')}：${row.sample_size}例`
    : `${t(locale, 'chart.includedPatients')}: ${row.sample_size}`
  const followupValue = row.median_followup_months === null
    ? t(locale, 'chart.notReached')
    : locale === 'zh'
      ? `${row.median_followup_months.toFixed(1)}${t(locale, 'chart.monthUnit')}`
      : `${row.median_followup_months.toFixed(1)} ${t(locale, 'chart.monthUnit')}`
  const followupSummary = locale === 'zh'
    ? `${t(locale, 'chart.medianFollowup')}：${followupValue}`
    : `${t(locale, 'chart.medianFollowup')}: ${followupValue}`
  const medianMonth = row.median_survival_months
  const medianIsPlottable = medianMonth !== null && medianMonth >= 0 && medianMonth <= xMaximum
  const medianSummary = medianMonth === null
    ? locale === 'zh'
      ? `${t(locale, 'chart.medianOs')}：${t(locale, 'chart.notReached')}`
      : `${t(locale, 'chart.medianOs')}: ${t(locale, 'chart.notReached')}`
    : locale === 'zh'
      ? `${t(locale, 'chart.medianOs')}：${medianMonth.toFixed(1)}${t(locale, 'chart.monthUnit')}`
      : `${t(locale, 'chart.medianOs')}: ${medianMonth.toFixed(1)} ${t(locale, 'chart.monthUnit')}`
  const medianX = medianIsPlottable ? x(medianMonth) : null
  const medianY = y(0.5)
  const medianLabelAtEnd = medianX !== null && medianX > width - margin.right - 220
  const censorHalfHeight = 7

  return (
    <section aria-label={t(locale, 'chart.region')} className="survival-chart">
      <div className="survival-chart__heading">
        <h2>{t(locale, 'chart.displayTitle')}</h2>
        <p>
          <span>{patientSummary}</span>
          <span>{followupSummary}</span>
        </p>
      </div>
      <div className="survival-chart__legend">
        <svg aria-hidden="true" className="survival-chart__legend-mark" viewBox="0 0 12 18">
          <line
            stroke="var(--primary-dark)"
            strokeWidth="1.35"
            vectorEffect="non-scaling-stroke"
            x1="6"
            x2="6"
            y1="2"
            y2="16"
          />
        </svg>
        <span>{t(locale, 'chart.censored')}</span>
      </div>
      <svg
        aria-describedby="survival-chart-description"
        aria-labelledby="survival-chart-title"
        className="survival-chart__svg"
        data-mobile-font-size="32"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        style={{ aspectRatio: '960 / 520', display: 'block', width: '100%' }}
        viewBox="0 0 960 520"
      >
        <title id="survival-chart-title">{t(locale, 'chart.title')}</title>
        <desc id="survival-chart-description">{t(locale, 'chart.description')}</desc>

        {[0, 0.25, 0.5, 0.75, 1].map((probability) => (
          <g key={probability}>
            <line
              className="survival-chart__grid"
              x1={margin.left}
              x2={width - margin.right}
              y1={y(probability)}
              y2={y(probability)}
            />
            <text textAnchor="end" x={margin.left - 14} y={y(probability) + 5}>
              {probability * 100}
            </text>
          </g>
        ))}

        {xTicks.map((month) => (
          <g key={month}>
            <line
              className="survival-chart__tick"
              x1={x(month)}
              x2={x(month)}
              y1={height - margin.bottom}
              y2={height - margin.bottom + 8}
            />
            <text
              className="survival-chart__x-tick-label"
              data-mobile-secondary={month === 12 && month !== xMaximum ? 'true' : undefined}
              textAnchor="middle"
              x={x(month)}
              y={height - margin.bottom + 20}
            >
              {month}
            </text>
          </g>
        ))}

        <line
          className="survival-chart__axis"
          x1={margin.left}
          x2={width - margin.right}
          y1={height - margin.bottom}
          y2={height - margin.bottom}
        />
        <line
          className="survival-chart__axis"
          x1={margin.left}
          x2={margin.left}
          y1={margin.top}
          y2={height - margin.bottom}
        />

        {survivalPath !== '' && (
          <path
            className="survival-chart__line"
            d={survivalPath}
            data-maximum-month={visibleMaximum}
            data-testid="survival-path"
            fill="none"
            stroke="var(--primary-dark)"
            strokeWidth="2.25"
            vectorEffect="non-scaling-stroke"
          />
        )}

        {censorPoints.map((point) => {
          const centerY = y(point.survival)
          return (
            <line
              className="survival-chart__censor-mark"
              data-censor-month={point.month}
              data-survival-probability={point.survival}
              data-testid="censor-mark"
              key={point.month}
              stroke="var(--primary-dark)"
              strokeWidth="1.35"
              vectorEffect="non-scaling-stroke"
              x1={x(point.month)}
              x2={x(point.month)}
              y1={Math.max(margin.top, centerY - censorHalfHeight)}
              y2={Math.min(height - margin.bottom, centerY + censorHalfHeight)}
            />
          )
        })}

        {medianX !== null ? (
          <g data-median-month={medianMonth} data-testid="median-survival-marker">
            <line
              className="survival-chart__median-guide"
              vectorEffect="non-scaling-stroke"
              x1={margin.left}
              x2={medianX}
              y1={medianY}
              y2={medianY}
            />
            <line
              className="survival-chart__median-guide"
              vectorEffect="non-scaling-stroke"
              x1={medianX}
              x2={medianX}
              y1={medianY}
              y2={height - margin.bottom}
            />
            <circle className="survival-chart__median-point" cx={medianX} cy={medianY} r="5" vectorEffect="non-scaling-stroke" />
            <text
              className="survival-chart__median-label"
              textAnchor={medianLabelAtEnd ? 'end' : 'start'}
              x={medianLabelAtEnd ? medianX - 10 : medianX + 10}
              y={medianY - 13}
            >
              {medianSummary}
            </text>
          </g>
        ) : (
          <text
            className="survival-chart__median-label"
            textAnchor="end"
            x={width - margin.right - 8}
            y={margin.top + 24}
          >
            {medianSummary}
          </text>
        )}

        <text
          className="survival-chart__label"
          textAnchor="middle"
          transform={`rotate(-90 24 ${margin.top + plotHeight / 2})`}
          x={24}
          y={margin.top + plotHeight / 2}
        >
          {t(locale, 'chart.yAxis')}
        </text>
        <text
          className="survival-chart__label"
          textAnchor="middle"
          x={margin.left + plotWidth / 2}
          y={height - 12}
        >
          {t(locale, 'chart.xAxis')}
        </text>
      </svg>
      <RiskTable counts={row.risk_table_counts} locale={locale} months={row.risk_table_months} />
    </section>
  )
}
