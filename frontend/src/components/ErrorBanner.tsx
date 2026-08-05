interface ErrorBannerProps {
  message: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

/**
 * A dismissable, retryable error banner. Shown in place of (or alongside)
 * whatever content failed to load, instead of leaving an infinite spinner
 * or an unhandled rejection. Uses the fixed status-critical color, always
 * paired with an icon + label -- never color alone.
 */
export default function ErrorBanner({ message, onRetry, onDismiss }: ErrorBannerProps) {
  return (
    <div className="mx-auto flex w-full items-start gap-3 rounded-xl border border-status-critical/20 bg-status-critical/[0.06] px-4 py-3 text-sm shadow-sm">
      <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-status-critical/15 text-status-critical">
        !
      </span>
      <div className="flex-1">
        <p className="font-semibold text-status-critical">Something went wrong</p>
        <p className="mt-0.5 text-ink-secondary">{message}</p>
        <div className="mt-2 flex gap-3">
          {onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="rounded-md bg-status-critical/10 px-3 py-1 text-xs font-semibold text-status-critical transition hover:bg-status-critical/15"
            >
              Retry
            </button>
          )}
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="rounded-md px-3 py-1 text-xs font-semibold text-ink-secondary transition hover:bg-black/5"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
