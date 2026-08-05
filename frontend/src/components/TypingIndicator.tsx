/**
 * WhatsApp-style "Quiz Bot is typing…" bubble, shown briefly while the next
 * question is being fetched -- reinforces the chat metaphor instead of a
 * generic spinner.
 */
export default function TypingIndicator() {
  return (
    <div className="flex w-full justify-start px-3 pt-3">
      <div className="relative flex items-center gap-1 rounded-lg rounded-tl-none bg-white px-4 py-3 shadow-sm bubble-tail-left">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="h-2 w-2 rounded-full bg-wa-green-dark/50 animate-typing-bounce"
            style={{ animationDelay: `${i * 0.15}s` }}
          />
        ))}
      </div>
    </div>
  );
}
