interface ListRowProps {
  icon?: string;
  title: string;
  subtitle?: string;
  badge?: string;
  onClick: () => void;
  disabled?: boolean;
}

/**
 * Shared WhatsApp-chat-list-row styling for exams / subjects / chapters,
 * consistent with the login picker's visual language.
 */
export default function ListRow({ icon = '📘', title, subtitle, badge, onClick, disabled }: ListRowProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="group flex w-full items-center gap-3 border-b border-gray-100 bg-white px-4 py-3.5 text-left transition hover:bg-wa-green/5 active:bg-wa-green/10 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-wa-green-dark/10 text-lg text-wa-green-dark transition group-hover:bg-wa-green-dark/15">
        {icon}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-gray-900">{title}</span>
        {subtitle && <span className="block truncate text-sm text-gray-500">{subtitle}</span>}
      </span>
      {badge && (
        <span className="rounded-full bg-wa-green px-2 py-0.5 text-xs font-semibold text-white">
          {badge}
        </span>
      )}
      <span className="text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-wa-green-dark">
        ›
      </span>
    </button>
  );
}
