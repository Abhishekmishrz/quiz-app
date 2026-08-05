import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getChaptersForSubject } from '../api/chapters';
import { startQuizAttempt } from '../api/quizAttempts';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import AppHeader from '../components/AppHeader';
import ListRow from '../components/ListRow';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import type { Chapter } from '../types';

export default function ChapterListPage() {
  const { subjectId } = useParams<{ subjectId: string }>();
  const { user } = useUser();
  const navigate = useNavigate();
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingId, setStartingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!user || !subjectId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getChaptersForSubject(subjectId, user.id);
      setChapters([...data].sort((a, b) => a.order - b.order));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to load chapters.');
    } finally {
      setLoading(false);
    }
  }, [user, subjectId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleStartQuiz = async (chapter: Chapter) => {
    if (!user) return;
    setStartingId(chapter.id);
    setError(null);
    try {
      const res = await startQuizAttempt(chapter.id, user.id);
      navigate(`/quiz/${res.attempt_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to start the quiz.');
    } finally {
      setStartingId(null);
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <AppHeader title="Chapters" subtitle="Tap a chapter to start its quiz" onBack={() => navigate(-1)} />
      <main className="scroll-thin flex-1 overflow-y-auto py-4">
        {loading && <LoadingSpinner label="Loading chapters…" />}

        {!loading && error && (
          <div className="px-4">
            <ErrorBanner message={error} onRetry={load} onDismiss={() => setError(null)} />
          </div>
        )}

        {!loading && !error && chapters.length === 0 && (
          <p className="px-4 py-8 text-center text-sm text-gray-500">No chapters available.</p>
        )}

        {!loading && !error && chapters.length > 0 && (
          <div className="overflow-hidden rounded-lg bg-white shadow-sm">
            {chapters.map((chapter) => (
              <ListRow
                key={chapter.id}
                icon="📖"
                title={chapter.name}
                subtitle={startingId === chapter.id ? 'Starting quiz…' : 'Tap to start quiz'}
                onClick={() => handleStartQuiz(chapter)}
                disabled={startingId !== null}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
