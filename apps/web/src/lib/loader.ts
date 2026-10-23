import { parseBundle, parseManifest, toSongs } from "./catalog";
import { loadCatalog, loadManifest, saveCatalog, saveManifest } from "./storage";
import type { Manifest, ModelInfo, Song } from "./types";

export const CATALOG_BASE: string = (import.meta.env.VITE_CATALOG_BASE ?? "/catalog").replace(/\/$/, "");

export type LoadSource = "device" | "network";
export type LoadFailure = "offline" | "network" | "invalid";

export class LoadError extends Error {
  readonly kind: LoadFailure;
  constructor(kind: LoadFailure, message: string) {
    super(message);
    this.name = "LoadError";
    this.kind = kind;
  }
}

export interface LoadDeps {
  fetchFn?: typeof fetch;
  base?: string;
}

async function fetchJson(url: string, deps: LoadDeps): Promise<unknown> {
  const fetchFn = deps.fetchFn ?? fetch;
  let response: Response;
  try {
    response = await fetchFn(url, { headers: { Accept: "application/json" } });
  } catch {
    throw new LoadError("offline", "No connection, and the songs are not saved on this device yet.");
  }
  if (!response.ok) throw new LoadError("network", `The server answered ${response.status}.`);
  try {
    return await response.json();
  } catch {
    throw new LoadError("invalid", "The catalog file could not be read.");
  }
}

function asInvalid(error: unknown): never {
  if (error instanceof LoadError) throw error;
  throw new LoadError("invalid", error instanceof Error ? error.message : "The catalog file is not valid.");
}

/** The saved manifest when there is one, otherwise the network. Saved data always wins: the app opens at once. */
export async function loadManifestFromAnywhere(
  deps: LoadDeps = {},
): Promise<{ manifest: Manifest; source: LoadSource }> {
  const saved = await loadManifest();
  if (saved) return { manifest: saved, source: "device" };
  try {
    const manifest = parseManifest(await fetchJson(`${deps.base ?? CATALOG_BASE}/manifest.json`, deps));
    await saveManifest(manifest);
    return { manifest, source: "network" };
  } catch (error) {
    return asInvalid(error);
  }
}

/** One model's songs: the saved bundle for this catalog version, otherwise the network (then saved). */
export async function loadSongs(
  model: ModelInfo,
  manifest: Manifest,
  deps: LoadDeps = {},
): Promise<{ songs: Song[]; source: LoadSource }> {
  const saved = await loadCatalog(model.slug);
  if (saved && saved.version === manifest.version) {
    return { songs: toSongs(saved.bundle), source: "device" };
  }
  try {
    const bundle = parseBundle(await fetchJson(`${deps.base ?? CATALOG_BASE}/${model.file}`, deps));
    await saveCatalog({
      slug: model.slug,
      version: manifest.version,
      savedAt: new Date().toISOString(),
      bundle,
    });
    return { songs: toSongs(bundle), source: "network" };
  } catch (error) {
    return asInvalid(error);
  }
}
