import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { getCurrentQuestion, submitAnswer } from '../api/quizAttempts';
import type { CurrentQuestionResponse } from '../types';

interface UseQuizAttemptResult {
  question: CurrentQuestionResponse | null;
  loading: boolean;
  submitting: boolean;
  error: string | null;
  /** True once the backend reports (directly or via a 409) that the attempt is finished. */
  isComplete: boolean;
  selectedOption: string | null;
  selectOption: (key: string) => void;
  submitSelected: () => Promise<void>;
  retry: () => void;
  dismissError: () => void;
}

/**
 * Encapsulates the quiz-taking state machine for a single attempt:
 *  - fetching the current question
 *  - tracking the user's in-progress selection
 *  - submitting an answer and advancing to the next question
 *  - gracefully handling the two documented 409 cases:
 *      - GET current-question 409s => the attempt is already complete
 *      - POST answers 409s => this question was already answered
 *        (e.g. a duplicate submit / stale client state) -- non-fatal,
 *        we just re-fetch the current question (or land on "complete").
 *
 * The server is the sole source of truth for whether an answer/question
 * transition is valid; this hook never second-guesses it, it only reacts
 * to what comes back.
 */
export function useQuizAttempt(attemptId: string | undefined, userId: string | undefined) {
  const [question, setQuestion] = useState<CurrentQuestionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [selectedOption, setSelectedOption] = useState<string | null>(null);

  // Bump to force a re-fetch from `retry()`.
  const [refreshTick, setRefreshTick] = useState(0);

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const applyReplaceState = useCallback((questionNumber: number) => {
    // Anti-revisit defense-in-depth: replaceState (never pushState) so the
    // browser back button cannot step through previous questions within the
    // quiz flow. The server independently rejects any stale/out-of-order
    // answer submission regardless of what the URL says.
    const url = new URL(window.location.href);
    url.searchParams.set('q', String(questionNumber));
    window.history.replaceState(window.history.state, '', url.toString());
  }, []);

  const fetchCurrentQuestion = useCallback(async () => {
    if (!attemptId || !userId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await getCurrentQuestion(attemptId, userId);
      if (!mountedRef.current) return;
      setQuestion(data);
      setSelectedOption(null);
      applyReplaceState(data.question_number);
    } catch (err) {
      if (!mountedRef.current) return;
      if (err instanceof ApiError && err.status === 409) {
        // Attempt already complete -- no more questions to show.
        setIsComplete(true);
        setQuestion(null);
      } else {
        const message = err instanceof ApiError ? err.detail : 'Failed to load the question.';
        setError(message);
      }
    } finally {
      if (mountedRef.current) setLoading(false);
    }
  }, [attemptId, userId, applyReplaceState]);

  useEffect(() => {
    fetchCurrentQuestion();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId, userId, refreshTick]);

  const selectOption = useCallback((key: string) => {
    setSelectedOption(key);
  }, []);

  const submitSelected = useCallback(async () => {
    if (!attemptId || !userId || !question || !selectedOption) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await submitAnswer(
        attemptId,
        { question_id: question.question_id, selected_option: selectedOption },
        userId,
      );
      if (!mountedRef.current) return;
      if (res.completed) {
        setIsComplete(true);
        setQuestion(null);
      } else if (res.advanced) {
        await fetchCurrentQuestion();
      } else {
        // Not advanced and not completed: nothing changed server-side,
        // just leave the current question in place.
      }
    } catch (err) {
      if (!mountedRef.current) return;
      if (err instanceof ApiError && err.status === 409) {
        // "Already answered" -- non-fatal, proceed to whatever the server
        // now considers current (next question, or attempt complete).
        await fetchCurrentQuestion();
      } else {
        const message = err instanceof ApiError ? err.detail : 'Failed to submit your answer.';
        setError(message);
      }
    } finally {
      if (mountedRef.current) setSubmitting(false);
    }
  }, [attemptId, userId, question, selectedOption, fetchCurrentQuestion]);

  const retry = useCallback(() => {
    setRefreshTick((t) => t + 1);
  }, []);

  const dismissError = useCallback(() => {
    setError(null);
  }, []);

  const result: UseQuizAttemptResult = {
    question,
    loading,
    submitting,
    error,
    isComplete,
    selectedOption,
    selectOption,
    submitSelected,
    retry,
    dismissError,
  };

  return result;
}
