import { Check, ChevronDown } from "lucide-react";
import type { KeyboardEvent } from "react";
import { ALL_MODELS, type ModelInfo } from "../lib/types";

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
  const items = [{ slug: ALL_MODELS, name: "All machines", hue: "all" }, ...models.map((m) => ({ slug: m.slug, name: m.name, hue: m.hue }))];

  const move = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const step = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (!step) return;
    event.preventDefault();
    const target = (index + step + items.length) % items.length;
    const next = items[target];
    if (!next) return;
    onChange(next.slug);
    (event.currentTarget.parentElement?.children[target] as HTMLElement | undefined)?.focus();
  };

  return (
    <div className="models" role="radiogroup" aria-label="Machine model">
      {items.map((model, index) => {
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
    <div className="select-wrap">
      <label htmlFor="model-select" className="sr-only">
        Machine model
      </label>
      <select id="model-select" className="select" value={value} onChange={(event) => onChange(event.target.value)}>
        <option value={ALL_MODELS}>All machines</option>
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
      <ChevronDown className="select__icon" size={24} aria-hidden="true" />
    </div>
  );
}
