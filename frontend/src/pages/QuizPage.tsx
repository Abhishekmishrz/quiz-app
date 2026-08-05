import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { useQuizAttempt } from '../hooks/useQuizAttempt';
import QuestionBubble from '../components/QuestionBubble';
import OptionBubble from '../components/OptionBubble';
import ProgressIndicator from '../components/ProgressIndicator';
import TypingIndicator from '../components/TypingIndicator';
import ErrorBanner from '../components/ErrorBanner';

export default function QuizPage() {
  const { attemptId } = useParams<{ attemptId: string }>();
  const { user } = useUser();
  const navigate = useNavigate();

  const {
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
  } = useQuizAttempt(attemptId, user?.id);

  useEffect(() => {
    if (isComplete && attemptId) {
      navigate(`/quiz/${attemptId}/result`, { replace: true });
    }
  }, [isComplete, attemptId, navigate]);

  return (
    <div className="flex h-full flex-col overflow-hidden chat-doodle-bg">
      <header className="z-10 flex shrink-0 items-center gap-3 bg-gradient-to-b from-wa-teal to-[#064941] px-4 py-3.5 text-white shadow-md">
        <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15 text-lg">
          🤖
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-[15px] font-semibold leading-tight">Quiz Bot</h1>
          <p className="truncate text-[11px] text-white/70">No going back — answer to move forward</p>
        </div>
      </header>

      {question && <ProgressIndicator current={question.question_number} total={question.total_questions} />}

      <main className="scroll-thin flex-1 overflow-y-auto pb-4">
        {loading && !question && (
          <div className="pt-3">
            <TypingIndicator />
          </div>
        )}

        {error && (
          <div className="px-4 pt-3">
            <ErrorBanner message={error} onRetry={retry} onDismiss={dismissError} />
          </div>
        )}

        {!loading && !error && isComplete && (
          <div className="pt-3">
            <TypingIndicator />
          </div>
        )}

        {question && (
          <>
            <QuestionBubble text={question.text} questionNumber={question.question_number} />
            <div className="mt-4 flex flex-col gap-2">
              {question.options.map((opt) => (
                <OptionBubble
                  key={opt.key}
                  optionKey={opt.key}
                  text={opt.text}
                  selected={selectedOption === opt.key}
                  disabled={submitting}
                  onSelect={selectOption}
                />
              ))}
            </div>
          </>
        )}
      </main>

      {question && (
        <div className="shrink-0 border-t border-black/5 bg-wa-panel pl-3 pr-5 py-2.5">
          <div className="flex items-center gap-2">
            <div className="flex min-h-[42px] min-w-0 flex-1 items-center rounded-full bg-white px-4 py-2 text-sm text-gray-400 shadow-inner">
              {selectedOption ? (
                <span className="truncate text-gray-800">
                  <span className="mr-1.5 inline-flex h-5 w-5 items-center justify-center rounded-full bg-wa-green/15 text-xs font-bold text-wa-green-dark">
                    {selectedOption}
                  </span>
                  {question.options.find((o) => o.key === selectedOption)?.text}
                </span>
              ) : (
                'Select an answer above…'
              )}
            </div>
            <button
              type="button"
              disabled={!selectedOption || submitting}
              onClick={submitSelected}
              aria-label="Submit answer"
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-wa-green text-white shadow-md transition focus:outline-none focus-visible:ring-2 focus-visible:ring-wa-green-dark disabled:cursor-not-allowed disabled:bg-gray-300 disabled:shadow-none"
            >
              {submitting ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              ) : (
                <span className="text-lg">➤</span>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
