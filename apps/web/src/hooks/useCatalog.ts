import { useCallback, useEffect, useRef, useState } from "react";
import { type LoadDeps, type LoadFailure, type LoadSource, loadManifestFromAnywhere, loadSongs } from "../lib/loader";
import { readModel, writeModel } from "../lib/prefs";
import { SongIndex } from "../lib/search";
import type { Manifest } from "../lib/types";

export type CatalogState =
  | { phase: "manifest-loading" }
  | { phase: "manifest-failed"; kind: LoadFailure; message: string }
  | { phase: "songs-loading"; manifest: Manifest; slug: string }
  | { phase: "songs-failed"; kind: LoadFailure; message: string; manifest: Manifest; slug: string }
  | { phase: "ready"; manifest: Manifest; slug: string; index: SongIndex; source: LoadSource };

const describe = (error: unknown): { kind: LoadFailure; message: string } => {
  const kind = (error as { kind?: LoadFailure }).kind ?? "invalid";
  const message = error instanceof Error ? error.message : "Something went wrong while loading the songs.";
  return { kind, message };
};

/**
 * Loads the catalog (saved copy first, so the app opens offline), then one model's songs.
 * While a model loads there is no index: songs from another model are never shown under it.
 */
export function useCatalog(deps?: LoadDeps) {
  const [state, setState] = useState<CatalogState>({ phase: "manifest-loading" });
  const [attempt, setAttempt] = useState(0);
  const [slug, setSlug] = useState<string | null>(null);
  const manifestRef = useRef<Manifest | null>(null);
  const indexes = useRef(new Map<string, SongIndex>());
  const depsRef = useRef(deps);

  useEffect(() => {
    let cancelled = false;
    if (!manifestRef.current) setState({ phase: "manifest-loading" });
    (async () => {
      let manifest = manifestRef.current;
      if (!manifest) {
        try {
          manifest = (await loadManifestFromAnywhere(depsRef.current)).manifest;
        } catch (error) {
          if (!cancelled) setState({ ...describe(error), phase: "manifest-failed" });
          return;
        }
        manifestRef.current = manifest;
      }
      const remembered = readModel();
      const wanted = slug ?? remembered;
      const model = manifest.models.find((m) => m.slug === wanted) ?? manifest.models[0];
      if (!model) return;
      const cached = indexes.current.get(model.slug);
      if (cached) {
        if (!cancelled) setState({ phase: "ready", manifest, slug: model.slug, index: cached, source: "device" });
        return;
      }
      if (!cancelled) setState({ phase: "songs-loading", manifest, slug: model.slug });
      try {
        const { songs, source } = await loadSongs(model, manifest, depsRef.current);
        const index = new SongIndex(songs);
        indexes.current.set(model.slug, index);
        if (!cancelled) setState({ phase: "ready", manifest, slug: model.slug, index, source });
      } catch (error) {
        if (!cancelled) setState({ ...describe(error), phase: "songs-failed", manifest, slug: model.slug });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [slug, attempt]);

  const selectModel = useCallback((next: string) => {
    writeModel(next);
    setSlug(next);
  }, []);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  return { state, selectModel, retry };
}
