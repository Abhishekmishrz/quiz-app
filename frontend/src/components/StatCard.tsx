interface StatCardProps {
  label: string;
  value: string;
  hint?: string;
}

/** KPI stat tile: label (sentence case) + value (semibold, proportional figures) + optional hint. */
export default function StatCard({ label, value, hint }: StatCardProps) {
  return (
    <div className="rounded-xl bg-white p-3.5 shadow-sm">
      <p className="text-xs font-medium text-ink-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold text-ink-primary">{value}</p>
      {hint && <p className="mt-0.5 text-[11px] text-ink-muted">{hint}</p>}
    </div>
  );
}
