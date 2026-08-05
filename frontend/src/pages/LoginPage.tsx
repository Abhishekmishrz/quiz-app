import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getUsers } from '../api/users';
import { createSession } from '../api/sessions';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import UserAvatarRow from '../components/UserAvatarRow';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import type { User } from '../types';

export default function LoginPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [signingInId, setSigningInId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const { login } = useUser();
  const navigate = useNavigate();

  const loadUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getUsers();
      setUsers(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to load users.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const filteredUsers = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q),
    );
  }, [users, query]);

  const handleSelectUser = async (user: User) => {
    setSigningInId(user.id);
    setError(null);
    try {
      const session = await createSession(user.id);
      login({ id: session.user_id, name: session.name });
      navigate('/exams', { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to sign in.');
    } finally {
      setSigningInId(null);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <header className="shrink-0 bg-gradient-to-b from-wa-teal to-[#064941] px-5 pb-6 pt-8 text-white">
        <div className="flex items-center gap-3">
          <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-white/15 text-2xl">
            💬
          </span>
          <div>
            <h1 className="text-xl font-bold leading-tight">QuizChat</h1>
            <p className="text-[13px] text-white/70">Pick a profile to start chatting with the quiz bot</p>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-2 rounded-full bg-white/15 px-3.5 py-2.5 text-sm text-white placeholder:text-white/60 focus-within:bg-white/20">
          <span className="text-white/70">🔍</span>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search users…"
            className="w-full bg-transparent text-sm text-white placeholder:text-white/60 focus:outline-none"
          />
        </div>
      </header>

      <main className="scroll-thin flex-1 overflow-y-auto pb-4">
        {loading && <LoadingSpinner label="Loading users…" />}

        {!loading && error && (
          <div className="px-4 pt-4">
            <ErrorBanner message={error} onRetry={loadUsers} onDismiss={() => setError(null)} />
          </div>
        )}

        {!loading && !error && filteredUsers.length === 0 && (
          <p className="px-4 py-10 text-center text-sm text-gray-500">
            {users.length === 0 ? 'No users found.' : `No users match "${query}".`}
          </p>
        )}

        {!loading && !error && filteredUsers.length > 0 && (
          <div className="bg-white shadow-sm">
            {filteredUsers.map((user) => (
              <div key={user.id} className="relative">
                <UserAvatarRow
                  name={user.name}
                  subtitle={user.email}
                  seed={user.avatar_seed || user.id}
                  onClick={() => handleSelectUser(user)}
                />
                {signingInId === user.id && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white/80">
                    <span className="flex items-center gap-2 text-xs font-medium text-wa-green-dark">
                      <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-wa-green/30 border-t-wa-green-dark" />
                      Signing in…
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
