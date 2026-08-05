import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';

interface AppHeaderProps {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  showUserActions?: boolean;
}

/**
 * WhatsApp-style dark-teal top bar shared by the list screens
 * (exams / subjects / chapters / analytics).
 */
export default function AppHeader({ title, subtitle, onBack, showUserActions = true }: AppHeaderProps) {
  const { user, logout } = useUser();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <header className="z-10 flex shrink-0 items-center gap-3 bg-gradient-to-b from-wa-teal to-[#064941] pl-5 pr-5 py-3.5 text-white shadow-md">
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          aria-label="Back"
          className="flex h-8 w-8 items-center justify-center rounded-full text-xl leading-none transition hover:bg-white/10 active:bg-white/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
        >
          ‹
        </button>
      )}
      <div className="min-w-0 flex-1">
        <h1 className="truncate text-[16px] font-semibold leading-tight">{title}</h1>
        {subtitle && <p className="truncate text-[12px] text-white/70">{subtitle}</p>}
      </div>
      {showUserActions && (
        <nav className="flex items-center gap-2 text-sm">
          <Link
            to="/analytics"
            className="rounded-full px-2.5 py-1.5 text-[13px] font-medium text-white/90 transition hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
          >
            📊 Analytics
          </Link>
          {user && (
            <button
              type="button"
              onClick={handleLogout}
              className="rounded-full bg-white/10 px-2.5 py-1.5 text-[12px] font-medium transition hover:bg-white/20 focus:outline-none focus-visible:ring-2 focus-visible:ring-white/60"
            >
              Log out
            </button>
          )}
        </nav>
      )}
    </header>
  );
}
