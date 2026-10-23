import { Search, X } from "lucide-react";
import { type KeyboardEvent, useRef } from "react";

interface SearchFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** Model name, so the field says what it searches. */
  modelName: string;
}

export function SearchField({ value, onChange, modelName }: SearchFieldProps) {
  const input = useRef<HTMLInputElement>(null);
  const clear = () => {
    onChange("");
    input.current?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape" && value) {
      event.preventDefault();
      onChange("");
    }
  };
  return (
    <div className="search" role="search">
      <label htmlFor="song-search" className="sr-only">
        Search {modelName} songs by title, artist or song number
      </label>
      <Search className="search__icon" size={24} aria-hidden="true" />
      <input
        ref={input}
        id="song-search"
        className="search__input"
        type="search"
        inputMode="search"
        enterKeyHint="search"
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        placeholder="Title, artist or song number"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onKeyDown={onKeyDown}
      />
      {value && (
        <button type="button" className="search__clear" onClick={clear} aria-label="Clear search">
          <X size={22} aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
