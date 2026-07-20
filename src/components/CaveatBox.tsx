import { t, type Locale } from '../i18n'

interface CaveatBoxProps {
  locale: Locale
}

export function CaveatBox({ locale }: CaveatBoxProps) {
  return (
    <aside aria-label={t(locale, 'caveat.region')} className="caveat-box">
      <h3>{t(locale, 'caveat.title')}</h3>
      <p>{t(locale, 'caveat.body')}</p>
    </aside>
  )
}
