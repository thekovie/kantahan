import { useCallback, useEffect, useRef, useState } from "react";
import { type LoadDeps, type LoadFailure, type LoadSource, loadManifestFromAnywhere, loadSongs } from "../lib/loader";
import { readLastCheck, readModel, writeModel } from "../lib/prefs";
import { SongIndex } from "../lib/search";
import { type SyncResult, checkForUpdates } from "../lib/sync";
import { ALL_MODELS, type Manifest, type Song } from "../lib/types";

export type CatalogState =
  | { phase: "manifest-loading" }
  | { phase: "manifest-failed"; kind: LoadFailure; message: string }
  | { phase: "suspended"; manifest: Manifest }
  | { phase: "songs-loading"; manifest: Manifest; slug: string }
  | { phase: "songs-failed"; kind: LoadFailure; message: string; manifest: Manifest; slug: string }
  | {
      phase: "ready";
      manifest: Manifest;
      slug: string;
      index: SongIndex;
      source: LoadSource;
      /** Names of machines that could not be loaded (all-machines view only). */
      missing: readonly string[];
    };

/** The "Check for updates" status line. `done` carries a plain-language result. */
export type UpdateState = { phase: "idle" } | { phase: "checking" } | { phase: "done"; message: string };

/** On open, the catalog is compared with the server when the last comparison is older than this. */
export const STALE_AFTER_MS = 12 * 60 * 60 * 1000;

const describe = (error: unknown): { kind: LoadFailure; message: string } => {
  const kind = (error as { kind?: LoadFailure }).kind ?? "invalid";
  const message = error instanceof Error ? error.message : "Something went wrong while loading the songs.";
  return { kind, message };
};

function sentence(result: SyncResult): string {
  switch (result.status) {
    case "up-to-date":
      return "Up to date.";
    case "updated":
      return `Updated to ${result.manifest.version}.`;
    case "suspended":
      return "The songbook is paused.";
    case "offline":
      return "No connection. Your saved songs still work.";
    case "failed":
      return result.message;
  }
}

/**
 * Loads the catalog (saved copy first, so the app opens offline), then one model's songs, and keeps
 * it current: on open when the last check is old, and whenever the visitor asks. While a model
 * loads there is no index, so songs from another model are never shown under it. A new catalog
 * replaces the index in place; the search box and the open song are untouched.
 */
export function useCatalog(deps?: LoadDeps) {
  const [state, setState] = useState<CatalogState>({ phase: "manifest-loading" });
  const [update, setUpdate] = useState<UpdateState>({ phase: "idle" });
  const [attempt, setAttempt] = useState(0);
  const [slug, setSlug] = useState<string | null>(null);
  const manifestRef = useRef<Manifest | null>(null);
  const activeRef = useRef<string | null>(null);
  /** Built indexes by "slug:sha256", so a bundle that changed can never be shown from an older index. */
  const indexes = useRef(new Map<string, SongIndex>());
  const ticketRef = useRef(0);
  const depsRef = useRef(deps);
  const autoChecked = useRef(false);

  /**
   * Every machine's songs in one index. Each entry keeps its own machine and number (nothing is merged), so
   * the same number on two machines stays two rows. A machine that fails is named; the rest still show.
   */
  const showAll = useCallback(
    async (manifest: Manifest, quiet: boolean, current: () => boolean) => {
      activeRef.current = ALL_MODELS;
      const key = `${ALL_MODELS}:${manifest.models.map((m) => `${m.slug}:${m.sha256}`).join("|")}`;
      const cached = indexes.current.get(key);
      if (cached) {
        if (current()) setState({ phase: "ready", manifest, slug: ALL_MODELS, index: cached, source: "device", missing: [] });
        return true;
      }
      if (!quiet && current()) setState({ phase: "songs-loading", manifest, slug: ALL_MODELS });
      const results = await Promise.allSettled(manifest.models.map((m) => loadSongs(m, manifest, depsRef.current)));
      const songs: Song[] = [];
      const missing: string[] = [];
      let source: LoadSource = "device";
      let firstError: unknown;
      results.forEach((result, i) => {
        const model = manifest.models[i];
        if (!model) return;
        if (result.status === "rejected") {
          missing.push(model.name);
          firstError ??= result.reason;
          return;
        }
        if (result.value.source === "network") source = "network";
        for (const song of result.value.songs) songs.push({ ...song, id: songs.length, model: model.slug });
      });
      if (songs.length === 0) {
        if (!quiet && current()) setState({ ...describe(firstError), phase: "songs-failed", manifest, slug: ALL_MODELS });
        return false;
      }
      const index = new SongIndex(songs);
      for (const stale of [...indexes.current.keys()]) {
        if (stale.startsWith(`${ALL_MODELS}:`)) indexes.current.delete(stale);
      }
      if (missing.length === 0) indexes.current.set(key, index);
      if (current()) setState({ phase: "ready", manifest, slug: ALL_MODELS, index, source, missing });
      return true;
    },
    [],
  );

  /**
   * Show one model of a manifest. Only the newest request may change the screen: if the visitor
   * picks another model, or another check lands, while this one is loading, its result is dropped.
   * `quiet` keeps what is on screen instead of flashing a loader. Returns false when it failed.
   */
  const show = useCallback(async (manifest: Manifest, wanted: string | null, quiet: boolean, cancelled: () => boolean) => {
    const ticket = ++ticketRef.current;
    const current = () => ticket === ticketRef.current && !cancelled();
    if (manifest.suspended) {
      if (current()) setState({ phase: "suspended", manifest });
      return true;
    }
    if (wanted === ALL_MODELS && manifest.models.length > 1) return showAll(manifest, quiet, current);
    const model = manifest.models.find((m) => m.slug === wanted) ?? manifest.models[0];
    if (!model) return true;
    activeRef.current = model.slug;
    const key = `${model.slug}:${model.sha256}`;
    const cached = indexes.current.get(key);
    if (cached) {
      if (current()) setState({ phase: "ready", manifest, slug: model.slug, index: cached, source: "device", missing: [] });
      return true;
    }
    if (!quiet && current()) setState({ phase: "songs-loading", manifest, slug: model.slug });
    try {
      const { songs, source } = await loadSongs(model, manifest, depsRef.current);
      const index = new SongIndex(songs);
      for (const stale of [...indexes.current.keys()]) {
        if (stale.startsWith(`${model.slug}:`)) indexes.current.delete(stale);
      }
      indexes.current.set(key, index);
      if (current()) setState({ phase: "ready", manifest, slug: model.slug, index, source, missing: [] });
      return true;
    } catch (error) {
      if (!quiet && current()) setState({ ...describe(error), phase: "songs-failed", manifest, slug: model.slug });
      return false;
    }
  }, [showAll]);

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
      // A first visit (nothing chosen yet) starts on every machine; one machine alone falls back to itself.
      await show(manifest, slug ?? readModel() ?? ALL_MODELS, false, () => cancelled);
    })();
    return () => {
      cancelled = true;
    };
  }, [slug, attempt, show]);

  /** Compare with the server and, if there is a newer catalog, swap it in. Overlapping calls share one comparison. */
  const checkNow = useCallback(
    async (background = false) => {
      if (!background) setUpdate({ phase: "checking" });
      const result = await checkForUpdates(depsRef.current);
      let shown = true;
      if ("manifest" in result) {
        manifestRef.current = result.manifest;
        shown = await show(result.manifest, activeRef.current, true, () => false);
      }
      if (!shown) {
        setUpdate({ phase: "done", message: "The catalog was updated, but the new songs could not be opened. Try again." });
        return;
      }
      const worthSaying = !background || result.status === "updated" || result.status === "suspended";
      setUpdate(worthSaying ? { phase: "done", message: sentence(result) } : { phase: "idle" });
    },
    [show],
  );

  // On open: compare with the server when it has been a while (or when the catalog is paused).
  useEffect(() => {
    if ((state.phase !== "ready" && state.phase !== "suspended") || autoChecked.current) return;
    if (navigator.onLine === false) return;
    const last = readLastCheck();
    if (state.phase === "ready" && last !== null && Date.now() - last < STALE_AFTER_MS) {
      autoChecked.current = true;
      return;
    }
    autoChecked.current = true;
    void checkNow(true);
  }, [state.phase, checkNow]);

  const selectModel = useCallback((next: string) => {
    writeModel(next);
    setSlug(next);
  }, []);

  /** Try again after a failure. A failed download can mean the saved catalog is out of date, so look for a newer one first. */
  const retry = useCallback(async () => {
    const result = await checkForUpdates(depsRef.current);
    if ("manifest" in result) manifestRef.current = result.manifest;
    setAttempt((n) => n + 1);
  }, []);

  return { state, selectModel, retry, update, checkNow: () => checkNow(false) };
}
