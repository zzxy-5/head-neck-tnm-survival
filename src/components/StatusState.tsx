import { t, type Locale } from '../i18n'

interface StatusStateProps {
  locale: Locale
  state: 'loading' | 'error' | 'empty'
  message?: string
  onRetry?: () => void
}

const defaultMessageKeys = {
  loading: 'status.loading',
  error: 'status.error',
  empty: 'status.empty',
} as const

export function StatusState({ locale, state, message, onRetry }: StatusStateProps) {
  const isError = state === 'error'

  return (
    <div
      aria-live={isError ? 'assertive' : 'polite'}
      className={`status-state status-state--${state}`}
      role={isError ? 'alert' : 'status'}
    >
      <p>{message ?? t(locale, defaultMessageKeys[state])}</p>
      {isError && onRetry ? (
        <button onClick={onRetry} type="button">
          {t(locale, 'status.retry')}
        </button>
      ) : null}
    </div>
  )
}
