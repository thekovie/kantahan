import { Check } from "lucide-react";
import type { KeyboardEvent } from "react";
import type { ModelInfo } from "../lib/types";

interface ModelPickerProps {
  models: readonly ModelInfo[];
  value: string;
  onChange: (slug: string) => void;
}

/** Up to this many models are shown as chips; more become a native select grouped by family. */
const MAX_CHIPS = 5;

export function ModelPicker({ models, value, onChange }: ModelPickerProps) {
  if (models.length > MAX_CHIPS) return <ModelSelect models={models} value={value} onChange={onChange} />;
  if (models.length === 1) return null; // nothing to choose; the model is still named in the search and the note

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const next = models[(index + step + models.length) % models.length];
    if (!next) return;
    onChange(next.slug);
    (event.currentTarget.parentElement?.children[(index + step + models.length) % models.length] as HTMLElement | undefined)?.focus();
  };

  return (
    <div className="models" role="radiogroup" aria-label="Machine model">
      {models.map((model, index) => {
        const selected = model.slug === value;
        return (
          <button
            key={model.slug}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            className={`chip hue-${model.hue}`}
            onClick={() => onChange(model.slug)}
            onKeyDown={(event) => move(event, index)}
          >
            {selected ? <Check size={18} strokeWidth={3} aria-hidden="true" /> : <span className="chip__dot" aria-hidden="true" />}
            {model.name}
          </button>
        );
      })}
    </div>
  );
}

function ModelSelect({ models, value, onChange }: ModelPickerProps) {
  const families = [...new Set(models.map((m) => m.family))];
  return (
    <div>
      <label htmlFor="model-select" className="sr-only">
        Machine model
      </label>
      <select id="model-select" className="select" value={value} onChange={(event) => onChange(event.target.value)}>
        {families.map((family) => (
          <optgroup key={family} label={family}>
            {models
              .filter((m) => m.family === family)
              .map((m) => (
                <option key={m.slug} value={m.slug}>
                  {m.name}
                </option>
              ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}
