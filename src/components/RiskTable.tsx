import { t, type Locale } from '../i18n'
import type { LookupRow } from '../types'

interface RiskTableProps {
  months: LookupRow['risk_table_months']
  counts: LookupRow['risk_table_counts']
  locale: Locale
}

export function RiskTable({ months, counts, locale }: RiskTableProps) {
  return (
    <div className="risk-table-wrap">
      <table aria-label={t(locale, 'risk.label')} className="risk-table">
        <caption>{t(locale, 'risk.label')}</caption>
        <thead>
          <tr>
            <th scope="row">{t(locale, 'risk.month')}</th>
            {months.map((month, index) => (
              <th key={`${month}-${index}`} scope="col">
                {month}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{t(locale, 'risk.atRisk')}</th>
            {counts.map((count, index) => (
              <td key={`${months[index] ?? index}-${index}`}>{count}</td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
