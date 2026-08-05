import { useCallback, useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { getQuizResult } from '../api/quizAttempts';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import ScoreRing from '../components/ScoreRing';
import type { QuizResult } from '../types';

function scoreMessage(pct: number): string {
  if (pct >= 90) return "Outstanding! 🎉";
  if (pct >= 70) return 'Nice work! 👏';
  if (pct >= 50) return 'Good effort — keep going.';
  return 'Room to grow — try again!';
}

export default function ResultPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const { user } = useUser();
  const navigate = useNavigate();
  const [result, setResult] = useState<QuizResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const load = useCallback(async () => {
    if (!user || !attemptId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getQuizResult(attemptId, user.id);
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : 'Failed to load your result.');
    } finally {
      setLoading(false);
    }
  }, [user, attemptId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <header className="shrink-0 bg-gradient-to-b from-wa-teal to-[#064941] px-4 py-4 text-white">
        <h1 className="text-lg font-semibold">Quiz complete</h1>
      </header>

      <main className="scroll-thin flex-1 overflow-y-auto px-4 py-6">
        {loading && <LoadingSpinner label="Calculating your score…" />}

        {!loading && error && (
          <ErrorBanner message={error} onRetry={load} onDismiss={() => setError(null)} />
        )}

        {!loading && !error && result && (
          <>
            <div className="animate-fade-up rounded-2xl bg-white p-6 text-center shadow-sm">
              <div className="flex justify-center">
                <ScoreRing percent={result.score_percent} />
              </div>
              <p className="mt-3 text-2xl font-bold text-gray-800">
                {result.correct_count}/{result.total_questions}
              </p>
              <p className="mt-1 text-sm font-medium text-ink-secondary">{scoreMessage(result.score_percent)}</p>
            </div>

            <div className="mt-5">
              <button
                type="button"
                onClick={() => setExpanded((v) => !v)}
                className="flex w-full items-center justify-between rounded-lg bg-white px-4 py-3 text-left text-sm font-semibold text-gray-700 shadow-sm transition hover:bg-gray-50"
              >
                <span>Answer review ({result.review.length} questions)</span>
                <span className={`text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}>▾</span>
              </button>

              {expanded && (
                <ul className="mt-3 space-y-2.5">
                  {result.review.map((item, idx) => (
                    <li
                      key={item.question_id}
                      className={`animate-fade-up rounded-lg bg-white p-3 text-sm shadow-sm ring-1 ${
                        item.is_correct ? 'ring-status-good/15' : 'ring-status-critical/15'
                      }`}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="font-medium text-gray-900">
                          {idx + 1}. {item.text}
                        </p>
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                            item.is_correct
                              ? 'bg-status-good/10 text-status-good'
                              : 'bg-status-critical/10 text-status-critical'
                          }`}
                        >
                          {item.is_correct ? '✓ Correct' : '✕ Incorrect'}
                        </span>
                      </div>
                      <p className="mt-1.5 text-ink-secondary">
                        Your answer: <span className="font-medium">{item.selected_option ?? '—'}</span>
                      </p>
                      {!item.is_correct && (
                        <p className="text-ink-secondary">
                          Correct answer:{' '}
                          <span className="font-medium text-status-good">{item.correct_option}</span>
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => navigate('/exams')}
                className="flex-1 rounded-full bg-wa-green py-2.5 text-sm font-semibold text-white shadow transition hover:brightness-105"
              >
                Back to exams
              </button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
