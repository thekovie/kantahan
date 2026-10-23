import type { Manifest, ModelInfo } from "../lib/types";

interface CatalogNoteProps {
  manifest: Manifest;
  model: ModelInfo;
  songCount: number;
}

const dateOf = (iso: string): string => {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : new Intl.DateTimeFormat("en-PH", { dateStyle: "medium" }).format(date);
};

/** What the visitor is looking at: model, volumes covered, size, source. Honest coverage in one place. */
export function CatalogNote({ manifest, model, songCount }: CatalogNoteProps) {
  return (
    <p className="catalog-note">
      {model.name} songbook · {model.coverage} · {songCount.toLocaleString("en-PH")} songs. Songs added in earlier volumes
      are not included. Compiled from{" "}
      <a href={manifest.source.url} rel="noreferrer noopener" target="_blank">
        {manifest.source.label}
      </a>
      . Catalog {manifest.version}, {dateOf(manifest.generatedAt)}.
    </p>
  );
}
