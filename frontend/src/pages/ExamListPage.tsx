import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getExams } from '../api/exams';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import AppHeader from '../components/AppHeader';
import ListRow from '../components/ListRow';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import type { Exam } from '../types';

export default function ExamListPage() {
  const { user } = useUser();
  const navigate = useNavigate();
  const [exams, setExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getExams(user.id);
      setExams(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to load exams.');
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <AppHeader title={`Hi, ${user?.name ?? ''}`.trim()} subtitle="Choose an exam to get started" />
      <main className="scroll-thin flex-1 overflow-y-auto py-4">
        <p className="px-4 pb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">
          Exams
        </p>

        {loading && <LoadingSpinner label="Loading exams…" />}

        {!loading && error && (
          <div className="px-4">
            <ErrorBanner message={error} onRetry={load} onDismiss={() => setError(null)} />
          </div>
        )}

        {!loading && !error && exams.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-gray-500">No exams available.</p>
        )}

        {!loading && !error && exams.length > 0 && (
          <div className="overflow-hidden rounded-lg bg-white shadow-sm">
            {exams.map((exam) => (
              <ListRow
                key={exam.id}
                icon="🎓"
                title={exam.name}
                subtitle={exam.code}
                onClick={() => navigate(`/exams/${exam.id}/subjects`)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
