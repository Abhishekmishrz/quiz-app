import { apiRequest } from './client';
import type {
  ChapterMasteryEntry,
  FatigueResponse,
  LearningVelocityEntry,
  QuestionDifficultyEntry,
} from '../types';

// Wire shapes actually returned by the backend (see
// backend/app/schemas/analytics.py) -- field names and envelope shape don't
// match the app-facing types 1:1, so they're mapped here at the boundary.

interface PagedResponseWire<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

interface QuestionDifficultyWire {
  question_id: string;
  question_text: string;
  chapter_id: string;
  total_attempts: number;
  raw_accuracy: number;
  shrunk_accuracy: number;
  avg_response_time_ms: number;
  shrunk_time_ms: number;
  qdi: number;
  confidence: string;
  rank: number;
}

interface ChapterMasteryWireEntry {
  chapter_id: string;
  chapter_name: string | null;
  subject_id: string | null;
  total_attempts: number;
  accuracy: number;
  shrunk_accuracy: number;
  avg_response_time_ms: number;
  mastery_score: number;
}

interface SubjectRollupWire {
  subject_id: string;
  subject_name: string | null;
  mastery_score: number;
  total_attempts: number;
}

interface ChapterMasteryUserWire {
  mode: 'user';
  user_id: string;
  chapters: ChapterMasteryWireEntry[];
  subjects: SubjectRollupWire[];
}

export function getLearningVelocity(userId: string): Promise<LearningVelocityEntry[]> {
  return apiRequest<LearningVelocityEntry[]>('/analytics/learning-velocity', { userId });
}

export function getFatigue(userId: string): Promise<FatigueResponse> {
  return apiRequest<FatigueResponse>('/analytics/fatigue', {
    userId,
    query: { user_id: userId },
  });
}

export async function getQuestionDifficulty(
  userId: string,
  limit?: number,
  offset?: number,
): Promise<QuestionDifficultyEntry[]> {
  const page = await apiRequest<PagedResponseWire<QuestionDifficultyWire>>(
    '/analytics/question-difficulty',
    { userId, query: { limit, offset } },
  );
  return page.items.map((r) => ({
    question_id: r.question_id,
    text: r.question_text,
    total_attempts: r.total_attempts,
    accuracy: r.raw_accuracy,
    avg_response_time_ms: r.avg_response_time_ms,
    qdi: r.qdi,
    confidence: r.confidence,
  }));
}

export async function getChapterMastery(userId: string): Promise<ChapterMasteryEntry[]> {
  const data = await apiRequest<ChapterMasteryUserWire>('/analytics/chapter-mastery', {
    userId,
    query: { user_id: userId },
  });
  const subjectNameById = new Map(data.subjects.map((s) => [s.subject_id, s.subject_name]));
  return data.chapters.map((c) => ({
    chapter_id: c.chapter_id,
    chapter_name: c.chapter_name ?? '',
    subject_id: c.subject_id ?? '',
    subject_name: (c.subject_id ? subjectNameById.get(c.subject_id) : null) ?? '',
    mastery_score: c.mastery_score,
    total_attempts: c.total_attempts,
  }));
}
