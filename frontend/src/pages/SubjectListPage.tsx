import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getSubjectsForExam } from '../api/subjects';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import AppHeader from '../components/AppHeader';
import ListRow from '../components/ListRow';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import type { Subject } from '../types';

export default function SubjectListPage() {
  const { examId } = useParams<{ examId: string }>();
  const { user } = useUser();
  const navigate = useNavigate();
  const [subjects, setSubjects] = useState<Subject[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user || !examId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getSubjectsForExam(examId, user.id);
      setSubjects([...data].sort((a, b) => a.order - b.order));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to load subjects.');
    } finally {
      setLoading(false);
    }
  }, [user, examId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <AppHeader title="Subjects" subtitle="Choose a subject" onBack={() => navigate('/exams')} />
      <main className="scroll-thin flex-1 overflow-y-auto py-4">
        {loading && <LoadingSpinner label="Loading subjects…" />}

        {!loading && error && (
          <div className="px-4">
            <ErrorBanner message={error} onRetry={load} onDismiss={() => setError(null)} />
          </div>
        )}

        {!loading && !error && subjects.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-gray-500">No subjects available.</p>
        )}

        {!loading && !error && subjects.length > 0 && (
          <div className="overflow-hidden rounded-lg bg-white shadow-sm">
            {subjects.map((subject) => (
              <ListRow
                key={subject.id}
                icon="📚"
                title={subject.name}
                subtitle={subject.code}
                onClick={() => navigate(`/subjects/${subject.id}/chapters`)}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
