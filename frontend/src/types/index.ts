// ---------------------------------------------------------------------------
// Shared API types for the Quiz application frontend.
// These mirror the fixed backend REST contract under /api/v1.
// ---------------------------------------------------------------------------

export interface User {
  id: string;
  name: string;
  email: string;
  avatar_seed: string;
}

export interface SessionResponse {
  user_id: string;
  name: string;
}

export interface Exam {
  id: string;
  name: string;
  code: string;
}

export interface Subject {
  id: string;
  name: string;
  code: string;
  order: number;
}

export interface Chapter {
  id: string;
  name: string;
  order: number;
}

export interface QuestionOption {
  key: string;
  text: string;
}

export interface CurrentQuestion {
  question_id: string;
  text: string;
  options: QuestionOption[];
}

export interface StartQuizAttemptResponse {
  attempt_id: string;
  total_questions: number;
  current_question: CurrentQuestion;
}

export interface CurrentQuestionResponse {
  question_id: string;
  text: string;
  options: QuestionOption[];
  question_number: number;
  total_questions: number;
}

export interface SubmitAnswerRequest {
  question_id: string;
  selected_option: string;
}

export interface SubmitAnswerResponse {
  advanced: boolean;
  completed: boolean;
}

export interface ReviewItem {
  question_id: string;
  text: string;
  options: QuestionOption[];
  correct_option: string;
  selected_option: string | null;
  is_correct: boolean;
}

export interface QuizResult {
  correct_count: number;
  total_questions: number;
  score_percent: number;
  review: ReviewItem[];
}

export interface LearningVelocityEntry {
  user_id: string;
  user_name: string;
  accuracy: number;
  avg_response_time_ms: number;
  consistency_score: number;
  lvi: number;
  rank: number;
}

export interface FatigueBucket {
  bucket_label: string;
  accuracy: number;
  avg_response_time_ms: number;
  n_attempts_contributing: number;
}

export interface FatigueResponse {
  buckets: FatigueBucket[];
  accuracy_delta: number;
  time_delta: number;
  accuracy_slope: number;
  time_slope: number;
}

export interface QuestionDifficultyEntry {
  question_id: string;
  text: string;
  total_attempts: number;
  accuracy: number;
  avg_response_time_ms: number;
  qdi: number;
  confidence: string;
}

export interface ChapterMasteryEntry {
  chapter_id: string;
  chapter_name: string;
  subject_id: string;
  subject_name: string;
  mastery_score: number;
  total_attempts: number;
}

// Backend error envelope: {"detail": str, "code": str}
export interface ApiErrorEnvelope {
  detail?: string;
  code?: string;
}
