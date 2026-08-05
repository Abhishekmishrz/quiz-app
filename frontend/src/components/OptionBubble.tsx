interface OptionBubbleProps {
  optionKey: string;
  text: string;
  selected: boolean;
  disabled?: boolean;
  onSelect: (key: string) => void;
}

/**
 * A tappable answer option styled like an outgoing chat bubble / quick-reply
 * chip. Highlights WhatsApp-green when selected.
 */
export default function OptionBubble({
  optionKey,
  text,
  selected,
  disabled,
  onSelect,
}: OptionBubbleProps) {
  return (
    <div className="flex w-full justify-end px-3 animate-bubble-in">
      <button
        type="button"
        disabled={disabled}
        onClick={() => onSelect(optionKey)}
        aria-pressed={selected}
        className={`relative max-w-[85%] rounded-lg rounded-tr-none px-3.5 py-2.5 text-left text-[15px] leading-relaxed shadow-sm transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-wa-green disabled:cursor-not-allowed ${
          selected
            ? 'bg-wa-bubble-out ring-2 ring-wa-green bubble-tail-right animate-pop'
            : 'bg-[#DCF8C6]/50 hover:bg-wa-bubble-out bubble-tail-right'
        }`}
      >
        <span
          className={`mr-2 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-bold transition-colors ${
            selected ? 'bg-wa-green text-white' : 'bg-white text-wa-green-dark'
          }`}
        >
          {selected ? '✓' : optionKey}
        </span>
        {text}
      </button>
    </div>
  );
}
