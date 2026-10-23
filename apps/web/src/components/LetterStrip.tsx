import { type KeyboardEvent, useEffect, useRef } from "react";
import type { LetterCount } from "../lib/search";

interface LetterStripProps {
  letters: readonly LetterCount[];
  active: string;
  onChange: (letter: string) => void;
  /** Id of the panel the tabs control. */
  panelId: string;
}

/** The songbook's alphabet rail, laid along the top so each letter keeps a full-size touch target. */
export function LetterStrip({ letters, active, onChange, panelId }: LetterStripProps) {
  const strip = useRef<HTMLDivElement>(null);

  // Keep the chosen letter centred in the strip, however it was chosen. This scrolls the strip itself:
  // scrollIntoView would also move the browser's keyboard starting point and skip the page header.
  useEffect(() => {
    const node = strip.current;
    const tab = node?.querySelector<HTMLElement>('[aria-selected="true"]');
    if (!node || !tab) return;
    node.scrollTo?.({ left: tab.offsetLeft - (node.clientWidth - tab.offsetWidth) / 2 });
  }, [active]);

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const last = letters.length - 1;
    const target =
      event.key === "ArrowRight" ? Math.min(index + 1, last) : event.key === "ArrowLeft" ? Math.max(index - 1, 0) : event.key === "Home" ? 0 : event.key === "End" ? last : null;
    if (target === null) return;
    event.preventDefault();
    const next = letters[target];
    if (!next) return;
    onChange(next.letter);
    (event.currentTarget.parentElement?.children[target] as HTMLElement | undefined)?.focus();
  };
  return (
    <div ref={strip} className="letters" role="tablist" aria-label="Songs by first letter">
      {letters.map(({ letter, count }, index) => (
        <button
          key={letter}
          type="button"
          role="tab"
          id={`letter-${letter === "#" ? "num" : letter}`}
          aria-selected={letter === active}
          aria-controls={panelId}
          tabIndex={letter === active ? 0 : -1}
          className="letter"
          aria-label={`${letter === "#" ? "Numbers and symbols" : letter}, ${count} ${count === 1 ? "song" : "songs"}`}
          onClick={() => onChange(letter)}
          onKeyDown={(event) => move(event, index)}
        >
          {letter}
        </button>
      ))}
    </div>
  );
}
