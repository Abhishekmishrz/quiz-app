import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getChapterMastery,
  getFatigue,
  getLearningVelocity,
  getQuestionDifficulty,
} from '../api/analytics';
import { ApiError } from '../api/client';
import { useUser } from '../context/UserContext';
import AppHeader from '../components/AppHeader';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorBanner from '../components/ErrorBanner';
import StatCard from '../components/StatCard';
import MiniBar from '../components/MiniBar';
import type {
  ChapterMasteryEntry,
  FatigueResponse,
  LearningVelocityEntry,
  QuestionDifficultyEntry,
} from '../types';

function Section<T>({
  title,
  hint,
  loading,
  error,
  onRetry,
  data,
  render,
}: {
  title: string;
  hint?: string;
  loading: boolean;
  error: string | null;
  onRetry: () => void;
  data: T | null;
  render: (data: T) => ReactNode;
}) {
  return (
    <section className="mb-5 overflow-hidden rounded-xl bg-white shadow-sm">
      <div className="flex items-start justify-between gap-2 border-b border-gray-100 px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold text-ink-primary">{title}</h2>
          {hint && <p className="mt-0.5 text-xs text-ink-muted">{hint}</p>}
        </div>
        {!loading && !error && data && (
          <span className="shrink-0 whitespace-nowrap text-[11px] text-ink-muted sm:hidden">
            ↔ swipe for more
          </span>
        )}
      </div>
      <div className="scroll-thin overflow-x-auto">
        {loading && <LoadingSpinner label="Loading…" />}
        {!loading && error && (
          <div className="p-4">
            <ErrorBanner message={error} onRetry={onRetry} />
          </div>
        )}
        {!loading && !error && data && render(data)}
      </div>
    </section>
  );
}

const th = 'px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-ink-muted';
const td = 'px-3 py-2.5 text-ink-primary whitespace-nowrap';

function rankBadge(rank: number): ReactNode {
  const medal = rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : null;
  if (medal) return <span className="text-base">{medal}</span>;
  return <span className="text-ink-muted">#{rank}</span>;
}

function confidenceBadge(confidence: string): ReactNode {
  const styles: Record<string, string> = {
    low: 'bg-gray-100 text-gray-500',
    medium: 'bg-gray-200 text-gray-600',
    high: 'bg-wa-green/10 text-wa-green-dark',
  };
  return (
    <span className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${styles[confidence] ?? styles.low}`}>
      {confidence}
    </span>
  );
}

function fmtDelta(value: number | null | undefined, suffix: string, invert = false): string {
  if (value == null) return '—';
  const good = invert ? value <= 0 : value >= 0;
  const sign = value > 0 ? '+' : '';
  return `${good ? '▲' : '▼'} ${sign}${value.toFixed(suffix === '%' ? 1 : 0)}${suffix}`;
}

export default function AnalyticsPage() {
  const { user } = useUser();
  const navigate = useNavigate();

  const [velocity, setVelocity] = useState<LearningVelocityEntry[] | null>(null);
  const [velocityLoading, setVelocityLoading] = useState(true);
  const [velocityError, setVelocityError] = useState<string | null>(null);

  const [fatigue, setFatigue] = useState<FatigueResponse | null>(null);
  const [fatigueLoading, setFatigueLoading] = useState(true);
  const [fatigueError, setFatigueError] = useState<string | null>(null);

  const [difficulty, setDifficulty] = useState<QuestionDifficultyEntry[] | null>(null);
  const [difficultyLoading, setDifficultyLoading] = useState(true);
  const [difficultyError, setDifficultyError] = useState<string | null>(null);

  const [mastery, setMastery] = useState<ChapterMasteryEntry[] | null>(null);
  const [masteryLoading, setMasteryLoading] = useState(true);
  const [masteryError, setMasteryError] = useState<string | null>(null);

  const loadVelocity = useCallback(async () => {
    if (!user) return;
    setVelocityLoading(true);
    setVelocityError(null);
    try {
      setVelocity(await getLearningVelocity(user.id));
    } catch (err) {
      setVelocityError(err instanceof ApiError ? err.detail : 'Failed to load learning velocity.');
    } finally {
      setVelocityLoading(false);
    }
  }, [user]);

  const loadFatigue = useCallback(async () => {
    if (!user) return;
    setFatigueLoading(true);
    setFatigueError(null);
    try {
      setFatigue(await getFatigue(user.id));
    } catch (err) {
      setFatigueError(err instanceof ApiError ? err.detail : 'Failed to load fatigue data.');
    } finally {
      setFatigueLoading(false);
    }
  }, [user]);

  const loadDifficulty = useCallback(async () => {
    if (!user) return;
    setDifficultyLoading(true);
    setDifficultyError(null);
    try {
      setDifficulty(await getQuestionDifficulty(user.id, 20, 0));
    } catch (err) {
      setDifficultyError(
        err instanceof ApiError ? err.detail : 'Failed to load question difficulty.',
      );
    } finally {
      setDifficultyLoading(false);
    }
  }, [user]);

  const loadMastery = useCallback(async () => {
    if (!user) return;
    setMasteryLoading(true);
    setMasteryError(null);
    try {
      setMastery(await getChapterMastery(user.id));
    } catch (err) {
      setMasteryError(err instanceof ApiError ? err.detail : 'Failed to load chapter mastery.');
    } finally {
      setMasteryLoading(false);
    }
  }, [user]);

  useEffect(() => {
    loadVelocity();
    loadFatigue();
    loadDifficulty();
    loadMastery();
  }, [loadVelocity, loadFatigue, loadDifficulty, loadMastery]);

  const kpis = useMemo(() => {
    const trackedUsers = velocity?.length ?? null;
    const avgAccuracy = velocity?.length
      ? velocity.reduce((sum, r) => sum + r.accuracy, 0) / velocity.length
      : null;
    const avgLvi = velocity?.length ? velocity.reduce((sum, r) => sum + r.lvi, 0) / velocity.length : null;
    const hardestQdi = difficulty?.length ? Math.max(...difficulty.map((r) => r.qdi)) : null;
    return { trackedUsers, avgAccuracy, avgLvi, hardestQdi };
  }, [velocity, difficulty]);

  const maxBucketAccuracy = useMemo(
    () => Math.max(0.01, ...(fatigue?.buckets.map((b) => b.accuracy) ?? [0.01])),
    [fatigue],
  );

  return (
    <div className="flex h-full flex-col overflow-hidden bg-wa-bg">
      <AppHeader title="Analytics" subtitle="Cohort insight from every quiz attempt" onBack={() => navigate(-1)} showUserActions={false} />
      <main className="scroll-thin flex-1 overflow-y-auto px-4 py-4">
        <div className="mb-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <StatCard label="Users tracked" value={kpis.trackedUsers != null ? String(kpis.trackedUsers) : '—'} />
          <StatCard
            label="Avg accuracy"
            value={kpis.avgAccuracy != null ? `${(kpis.avgAccuracy * 100).toFixed(1)}%` : '—'}
          />
          <StatCard label="Avg LVI" value={kpis.avgLvi != null ? kpis.avgLvi.toFixed(1) : '—'} hint="0–100 scale" />
          <StatCard
            label="Hardest QDI seen"
            value={kpis.hardestQdi != null ? kpis.hardestQdi.toFixed(1) : '—'}
            hint="higher = harder"
          />
        </div>

        <Section
          title="Learning Velocity Index"
          hint="Accuracy + speed + consistency, ranked"
          loading={velocityLoading}
          error={velocityError}
          onRetry={loadVelocity}
          data={velocity}
          render={(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className={th}>Rank</th>
                  <th className={th}>User</th>
                  <th className={th}>Accuracy</th>
                  <th className={th}>Avg response</th>
                  <th className={th}>Consistency</th>
                  <th className={th}>LVI</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td className={td} colSpan={6}>
                      No data yet.
                    </td>
                  </tr>
                )}
                {rows.map((row) => (
                  <tr key={row.user_id} className="border-t border-gray-100 hover:bg-gray-50/60">
                    <td className={td}>{rankBadge(row.rank)}</td>
                    <td className={`${td} font-medium`}>{row.user_name}</td>
                    <td className={td}>
                      <MiniBar value={row.accuracy} label={`${(row.accuracy * 100).toFixed(1)}%`} />
                    </td>
                    <td className={`${td} tabular-nums text-ink-secondary`}>
                      {Math.round(row.avg_response_time_ms)}ms
                    </td>
                    <td className={`${td} tabular-nums text-ink-secondary`}>{row.consistency_score.toFixed(2)}</td>
                    <td className={td}>
                      <MiniBar value={row.lvi / 100} label={row.lvi.toFixed(1)} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        />

        <Section
          title="Fatigue Analysis"
          hint="Accuracy / response time in 5-question buckets across the session"
          loading={fatigueLoading}
          error={fatigueError}
          onRetry={loadFatigue}
          data={fatigue}
          render={(data) => (
            <>
              <table className="w-full text-sm">
                <thead>
                  <tr>
                    <th className={th}>Bucket</th>
                    <th className={th}>Accuracy</th>
                    <th className={th}>Avg response</th>
                    <th className={th}>Attempts</th>
                  </tr>
                </thead>
                <tbody>
                  {data.buckets.length === 0 && (
                    <tr>
                      <td className={td} colSpan={4}>
                        No data yet.
                      </td>
                    </tr>
                  )}
                  {data.buckets.map((bucket) => (
                    <tr key={bucket.bucket_label} className="border-t border-gray-100 hover:bg-gray-50/60">
                      <td className={`${td} font-medium`}>{bucket.bucket_label}</td>
                      <td className={td}>
                        <MiniBar
                          value={bucket.accuracy / maxBucketAccuracy}
                          label={`${(bucket.accuracy * 100).toFixed(1)}%`}
                        />
                      </td>
                      <td className={`${td} tabular-nums text-ink-secondary`}>
                        {Math.round(bucket.avg_response_time_ms)}ms
                      </td>
                      <td className={`${td} tabular-nums text-ink-secondary`}>{bucket.n_attempts_contributing}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <div className="flex flex-wrap gap-4 px-3 py-3 text-xs text-ink-secondary">
                <span>
                  Accuracy trend:{' '}
                  <span className="font-semibold">{fmtDelta(data.accuracy_delta != null ? data.accuracy_delta * 100 : null, '%')}</span>
                </span>
                <span>
                  Response-time trend:{' '}
                  <span className="font-semibold">{fmtDelta(data.time_delta, 'ms', true)}</span>
                </span>
              </div>
            </>
          )}
        />

        <Section
          title="Question Difficulty Index"
          hint="Attempts, accuracy & response time, ranked hardest → easiest"
          loading={difficultyLoading}
          error={difficultyError}
          onRetry={loadDifficulty}
          data={difficulty}
          render={(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className={th}>Question</th>
                  <th className={th}>Attempts</th>
                  <th className={th}>Accuracy</th>
                  <th className={th}>Avg response</th>
                  <th className={th}>QDI</th>
                  <th className={th}>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td className={td} colSpan={6}>
                      No data yet.
                    </td>
                  </tr>
                )}
                {rows.map((row) => (
                  <tr key={row.question_id} className="border-t border-gray-100 hover:bg-gray-50/60">
                    <td className={`${td} max-w-xs truncate whitespace-normal text-ink-primary`}>{row.text}</td>
                    <td className={`${td} tabular-nums text-ink-secondary`}>{row.total_attempts}</td>
                    <td className={td}>
                      <MiniBar value={row.accuracy} label={`${(row.accuracy * 100).toFixed(1)}%`} />
                    </td>
                    <td className={`${td} tabular-nums text-ink-secondary`}>
                      {Math.round(row.avg_response_time_ms)}ms
                    </td>
                    <td className={td}>
                      <MiniBar value={row.qdi / 100} label={row.qdi.toFixed(1)} />
                    </td>
                    <td className={td}>{confidenceBadge(row.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        />

        <Section
          title="Chapter Mastery"
          hint="Bayesian-shrunk accuracy + speed, rolled up per chapter"
          loading={masteryLoading}
          error={masteryError}
          onRetry={loadMastery}
          data={mastery}
          render={(rows) => (
            <table className="w-full text-sm">
              <thead>
                <tr>
                  <th className={th}>Subject</th>
                  <th className={th}>Chapter</th>
                  <th className={th}>Mastery</th>
                  <th className={th}>Attempts</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && (
                  <tr>
                    <td className={td} colSpan={4}>
                      No data yet.
                    </td>
                  </tr>
                )}
                {rows.map((row) => (
                  <tr key={row.chapter_id} className="border-t border-gray-100 hover:bg-gray-50/60">
                    <td className={`${td} text-ink-secondary`}>{row.subject_name}</td>
                    <td className={`${td} font-medium`}>{row.chapter_name}</td>
                    <td className={td}>
                      <MiniBar value={row.mastery_score / 100} label={`${row.mastery_score.toFixed(1)}%`} />
                    </td>
                    <td className={`${td} tabular-nums text-ink-secondary`}>{row.total_attempts}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        />
      </main>
    </div>
  );
}
