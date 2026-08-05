import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

export interface CurrentUser {
  id: string;
  name: string;
}

interface UserContextValue {
  user: CurrentUser | null;
  login: (user: CurrentUser) => void;
  logout: () => void;
}

const UserContext = createContext<UserContextValue | undefined>(undefined);

/**
 * Holds the currently logged-in user for the duration of the browser
 * session. Intentionally in-memory only (no localStorage/sessionStorage) --
 * this is dummy auth for a demo app, so a hard refresh is expected to log
 * the user out again.
 */
export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);

  const login = useCallback((nextUser: CurrentUser) => {
    setUser(nextUser);
  }, []);

  const logout = useCallback(() => {
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, login, logout }), [user, login, logout]);

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUser(): UserContextValue {
  const ctx = useContext(UserContext);
  if (!ctx) {
    throw new Error('useUser must be used within a UserProvider');
  }
  return ctx;
}

/**
 * Route guard: redirects to /login when there is no logged-in user.
 * Wrap any route element that requires a session with this component.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { user } = useUser();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
