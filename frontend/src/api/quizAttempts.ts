import { apiRequest } from './client';
import type {
  CurrentQuestionResponse,
  QuestionOption,
  QuizResult,
  StartQuizAttemptResponse,
  SubmitAnswerRequest,
  SubmitAnswerResponse,
} from '../types';

// Wire shapes actually returned by the backend (see
// backend/app/schemas/quiz_attempt.py and question.py) -- these use `id` /
// `question_index` (0-based), not the `question_id` / `question_number`
// (1-based) naming the rest of the frontend is written against. Mapped to
// the app-facing types right here at the API boundary.

interface QuestionWire {
  id: string;
  chapter_id: string;
  text: string;
  options: QuestionOption[];
  question_index: number;
  total_questions: number;
}

interface AttemptWire {
  id: string;
  total_questions: number;
}

interface StartAttemptWire {
  attempt: AttemptWire;
  current_question: QuestionWire;
}

interface ReviewItemWire {
  id: string;
  text: string;
  options: QuestionOption[];
  correct_option: string;
  selected_option: string | null;
  is_correct: boolean | null;
}

interface QuizResultWire {
  attempt_id: string;
  correct_count: number;
  total_questions: number;
  score_percent: number;
  review: ReviewItemWire[];
}

function toQuestionResponse(q: QuestionWire): CurrentQuestionResponse {
  return {
    question_id: q.id,
    text: q.text,
    options: q.options,
    question_number: q.question_index + 1,
    total_questions: q.total_questions,
  };
}

export async function startQuizAttempt(
  chapterId: string,
  userId: string,
): Promise<StartQuizAttemptResponse> {
  const data = await apiRequest<StartAttemptWire>('/quiz-attempts', {
    method: 'POST',
    body: { chapter_id: chapterId },
    userId,
  });
  return {
    attempt_id: data.attempt.id,
    total_questions: data.attempt.total_questions,
    current_question: toQuestionResponse(data.current_question),
  };
}

export async function getCurrentQuestion(
  attemptId: string,
  userId: string,
): Promise<CurrentQuestionResponse> {
  const data = await apiRequest<QuestionWire>(`/quiz-attempts/${attemptId}/current-question`, {
    userId,
  });
  return toQuestionResponse(data);
}

export function submitAnswer(
  attemptId: string,
  payload: SubmitAnswerRequest,
  userId: string,
): Promise<SubmitAnswerResponse> {
  return apiRequest<SubmitAnswerResponse>(`/quiz-attempts/${attemptId}/answers`, {
    method: 'POST',
    body: payload,
    userId,
  });
}

export async function getQuizResult(attemptId: string, userId: string): Promise<QuizResult> {
  const data = await apiRequest<QuizResultWire>(`/quiz-attempts/${attemptId}/result`, { userId });
  return {
    correct_count: data.correct_count,
    total_questions: data.total_questions,
    score_percent: data.score_percent,
    review: data.review.map((r) => ({
      question_id: r.id,
      text: r.text,
      options: r.options,
      correct_option: r.correct_option,
      selected_option: r.selected_option,
      is_correct: !!r.is_correct,
    })),
  };
}
