import type { UpdateState } from "../hooks/useCatalog";
import type { Manifest, ModelInfo } from "../lib/types";

interface CatalogNoteProps {
  manifest: Manifest;
  /** The machine shown, or null for the all-machines view. */
  model: ModelInfo | null;
  songCount: number;
  update: UpdateState;
  onCheck: () => void;
}

const dateOf = (iso: string): string => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : new Intl.DateTimeFormat("en-PH", { dateStyle: "medium" }).format(date);
};

/**
 * What the visitor is looking at, kept short: the machine, its volumes and size, where the songs come from,
 * and a way to look for newer ones. The caveats sit behind "About this list" so they are there when wanted
 * and quiet when not. The source credit always stays visible.
 */
export function CatalogNote({ manifest, model, songCount, update, onCheck }: CatalogNoteProps) {
  const checking = update.phase === "checking";
  const count = songCount.toLocaleString("en-PH");
  return (
    <section className="catalog-note" aria-label="About this catalog">
      <p className="catalog-note__summary">
        {model
          ? `${model.name} · ${model.coverage} · ${count} songs`
          : `All machines · ${count} song numbers · ${manifest.models.length} machines`}
      </p>
      <p>
        Source:{" "}
        <a href={manifest.source.url} rel="noreferrer noopener" target="_blank">
          {manifest.source.label}
        </a>{" "}
        · Catalog {manifest.version}, {dateOf(manifest.generatedAt)}
      </p>
      <div className="update-row">
        <button type="button" className="btn btn--quiet" onClick={onCheck} disabled={checking} aria-busy={checking}>
          {checking ? "Checking…" : "Check for updates"}
        </button>
        <span className="status" role="status">
          {update.phase === "done" ? update.message : ""}
        </span>
      </div>
      <details className="catalog-note__more">
        <summary>About this list</summary>
        <p>Songs added in earlier volumes are not included.</p>
        {model?.excluded ? (
          <p>
            {model.excluded.toLocaleString("en-PH")} song numbers are left out because the publisher lists them with
            different titles in different volumes.
          </p>
        ) : null}
        {model ? null : (
          <p>
            A row lists every machine that uses that number for the song. The same number can be another song on
            another machine, and then it has its own row.
          </p>
        )}
      </details>
    </section>
  );
}
