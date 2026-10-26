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

/** What the visitor is looking at: model, volumes covered, size, source, and a way to look for newer songs. */
export function CatalogNote({ manifest, model, songCount, update, onCheck }: CatalogNoteProps) {
  const checking = update.phase === "checking";
  return (
    <section className="catalog-note" aria-label="About this catalog">
      <p>
        {model ? (
          <>
            {model.name} songbook · {model.coverage} · {songCount.toLocaleString("en-PH")} songs. Songs added in
            earlier volumes are not included.
            {model.excluded
              ? ` ${model.excluded.toLocaleString("en-PH")} song numbers are left out because the publisher lists them with different titles in different volumes.`
              : ""}
          </>
        ) : (
          <>
            All machines · {songCount.toLocaleString("en-PH")} song numbers from {manifest.models.length} machines.
            A row lists every machine that uses that number for the song; the same number can be another song on
            another machine. Songs added in earlier volumes are not included.
          </>
        )}{" "}
        Compiled from{" "}
        <a href={manifest.source.url} rel="noreferrer noopener" target="_blank">
          {manifest.source.label}
        </a>
        . Catalog {manifest.version}, {dateOf(manifest.generatedAt)}.
      </p>
      <div className="update-row">
        <button type="button" className="btn btn--quiet" onClick={onCheck} disabled={checking} aria-busy={checking}>
          {checking ? "Checking…" : "Check for updates"}
        </button>
        <span className="status" role="status">
          {update.phase === "done" ? update.message : ""}
        </span>
      </div>
    </section>
  );
}
