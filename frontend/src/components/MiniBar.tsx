interface MiniBarProps {
  /** 0-1 fraction already normalized against this column's own range. */
  value: number;
  /** Rendered after the bar, right-aligned (the actual numeric value -- text never wears the data color). */
  label: string;
  width?: number;
}

/**
 * In-table magnitude indicator: sequential single hue, 4px rounded data-end,
 * track is a lighter step of the SAME ramp (per the meter spec). Supplements
 * the numeric label already in the row -- identity is never color-alone.
 */
export default function MiniBar({ value, label, width = 72 }: MiniBarProps) {
  const pct = Math.max(0, Math.min(100, value * 100));
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 shrink-0 overflow-hidden rounded-full bg-seq-100/40" style={{ width }}>
        <div className="h-full rounded-full bg-seq-500" style={{ width: `${pct}%` }} />
      </div>
      <span className="tabular-nums text-ink-secondary">{label}</span>
    </div>
  );
}
