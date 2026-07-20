import { t, type Locale } from '../i18n'

interface AppHeaderProps {
  locale: Locale
  onLocaleChange: (locale: Locale) => void
}

export function AppHeader({ locale, onLocaleChange }: AppHeaderProps) {
  return (
    <header className="app-header">
      <div>
        <p className="app-header__eyebrow">{t(locale, 'header.eyebrow')}</p>
        <h1>{t(locale, 'header.title')}</h1>
      </div>
      <div className="app-header__actions">
        <p className="app-header__notice">{t(locale, 'header.notice')}</p>
        <div aria-label={t(locale, 'language.label')} className="language-switch" role="group">
          {(['zh', 'en'] as const).map((option) => (
            <button
              aria-pressed={locale === option}
              key={option}
              onClick={() => onLocaleChange(option)}
              type="button"
            >
              {option === 'zh' ? '中文' : 'English'}
            </button>
          ))}
        </div>
      </div>
    </header>
  )
}
