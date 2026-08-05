interface ProgressIndicatorProps {
  current: number;
  total: number;
}

export default function ProgressIndicator({ current, total }: ProgressIndicatorProps) {
  // `current` is the 1-based question being shown right now, not yet answered --
  // the bar fills with questions *completed* (current - 1), so it never claims
  // 100% while the last question is still unanswered.
  const pct = total > 0 ? Math.min(100, Math.round(((current - 1) / total) * 100)) : 0;
  return (
    <div className="shrink-0 bg-white/70 px-4 py-2 backdrop-blur-sm">
      <div className="mb-1 flex items-center justify-between text-xs font-medium text-ink-secondary">
        <span>
          Question {current} of {total}
        </span>
        <span className="tabular-nums">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-seq-100/40">
        <div
          className="h-full rounded-full bg-gradient-to-r from-wa-green-dark to-wa-green transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
