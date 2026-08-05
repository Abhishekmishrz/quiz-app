interface QuestionBubbleProps {
  text: string;
  questionNumber?: number;
}

/**
 * Renders the current quiz question as a left-aligned "incoming message"
 * chat bubble, WhatsApp-style (white bubble, tail on the left).
 */
export default function QuestionBubble({ text, questionNumber }: QuestionBubbleProps) {
  return (
    <div className="flex w-full justify-start px-3 pt-3 animate-bubble-in">
      <div className="relative max-w-[85%] rounded-lg rounded-tl-none bg-white px-3.5 py-2.5 text-[15px] leading-relaxed text-gray-900 shadow-sm bubble-tail-left">
        {typeof questionNumber === 'number' && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-wa-green-dark">
            Question {questionNumber}
          </p>
        )}
        <p className="whitespace-pre-wrap">{text}</p>
        <span className="mt-1 block text-right text-[11px] text-gray-400">Quiz Bot</span>
      </div>
    </div>
  );
}
