import { getInitials, colorFromSeed } from '../utils/avatar';

interface UserAvatarRowProps {
  name: string;
  subtitle?: string;
  seed: string;
  onClick?: () => void;
}

/**
 * A single row in the WhatsApp-style login picker: avatar circle with
 * initials, name, optional subtitle (email), subtle divider below.
 */
export default function UserAvatarRow({ name, subtitle, seed, onClick }: UserAvatarRowProps) {
  const bg = colorFromSeed(seed);
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full items-center gap-3 border-b border-gray-100 bg-white px-4 py-3 text-left transition hover:bg-wa-green/5 active:bg-wa-green/10"
    >
      <span className="relative shrink-0">
        <span
          className="flex h-12 w-12 items-center justify-center rounded-full text-base font-semibold text-white shadow-sm ring-2 ring-white"
          style={{ backgroundColor: bg }}
        >
          {getInitials(name)}
        </span>
        <span className="absolute -bottom-0.5 -right-0.5 h-3.5 w-3.5 rounded-full border-2 border-white bg-wa-green" />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium text-gray-900">{name}</span>
        {subtitle && <span className="block truncate text-sm text-gray-500">{subtitle}</span>}
      </span>
      <span className="text-gray-300 transition group-hover:translate-x-0.5 group-hover:text-wa-green-dark">
        ›
      </span>
    </button>
  );
}
