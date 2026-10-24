import type { ModelInfo } from "../lib/types";

interface LineSignProps {
  model: ModelInfo;
  /** Square top corners, for use as the header of a sheet. */
  top?: boolean;
}

/** A mark that tells machines apart: a short last word ("Model A" gives "A"), otherwise the first letter. */
export function lineBadge(name: string): string {
  const last = name.trim().split(/\s+/).at(-1) ?? "";
  const mark = [...last].length <= 2 ? last : [...name.trim()][0];
  return (mark ?? "").toUpperCase();
}

/**
 * The selected machine drawn as a metro line header: a round badge with the model's initial, its name and
 * the volumes covered, on the model's line colour. The name is always written out, so colour is never the
 * only way to tell the machines apart.
 */
export function LineSign({ model, top = false }: LineSignProps) {
  return (
    <div className={`line hue-${model.hue}${top ? " line--top" : ""}`}>
      <span className="line__badge" aria-hidden="true">
        {lineBadge(model.name)}
      </span>
      <span className="line__name">{model.name}</span>
      <span className="line__detail">{model.coverage}</span>
    </div>
  );
}
