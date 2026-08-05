import type { CSSProperties } from 'react';

interface ScoreRingProps {
  /** 0-100 */
  percent: number;
  size?: number;
}

/**
 * Circular meter for "a single ratio against a limit" (score / 100) -- per
 * the data-viz method this is a meter, not a chart: the fill carries the
 * value, the track is a lighter step of the SAME hue (seq-100), and the
 * number is rendered as text (never color-only).
 */
export default function ScoreRing({ percent, size = 152 }: ScoreRingProps) {
  const clamped = Math.max(0, Math.min(100, percent));
  const stroke = 12;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#6ec090"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#187a49"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={
            {
              '--ring-circumference': `${circumference}px`,
              '--ring-offset': `${offset}px`,
            } as CSSProperties
          }
          className="animate-ring-grow"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-extrabold text-ink-primary">{Math.round(clamped)}%</span>
        <span className="text-xs font-medium text-ink-muted">score</span>
      </div>
    </div>
  );
}
