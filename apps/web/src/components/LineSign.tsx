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

interface SignProps {
  className: string;
  badge: string;
  name: string;
  detail: string;
}

function Sign({ className, badge, name, detail }: SignProps) {
  return (
    <div className={className}>
      <span className={badge.length > 2 ? "line__badge line__badge--word" : "line__badge"} aria-hidden="true">
        {badge}
      </span>
      <span className="line__name">{name}</span>
      <span className="line__detail">{detail}</span>
    </div>
  );
}

/**
 * The selected machine drawn as a metro line header: a round badge with the model's mark, its name and
 * the volumes covered, on the model's line colour. The name is always written out, so colour is never the
 * only way to tell the machines apart.
 */
export function LineSign({ model, top = false }: LineSignProps) {
  return (
    <Sign
      className={`line hue-${model.hue}${top ? " line--top" : ""}`}
      badge={lineBadge(model.name)}
      name={model.name}
      detail={model.coverage}
    />
  );
}

interface AllSignProps {
  detail: string;
  /** Shown instead of "All machines", for example "For 4 machines" in a number sheet. */
  name?: string;
  badge?: string;
  /** Square top corners, for use as the header of a sheet. */
  top?: boolean;
}

/** The sign for the all-machines view: ink, because no single machine's colour applies. */
export function AllSign({ detail, name = "All machines", badge = "All", top = false }: AllSignProps) {
  return <Sign className={`line hue-all${top ? " line--top" : ""}`} badge={badge} name={name} detail={detail} />;
}
