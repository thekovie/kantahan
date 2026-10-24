import { parseBundle, parseManifest, toSongs } from "./catalog";
import { sha256Hex } from "./hash";
import { writeLastCheck } from "./prefs";
import { loadCatalog, loadManifest, saveCatalog, saveManifest } from "./storage";
import type { BundleV1, Manifest, ModelInfo, Song } from "./types";

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

const MAX_MANIFEST_BYTES = 1024 * 1024;
const TOO_BIG = "The download was larger than the catalog said it would be, so it was not used.";

/** Fetch bytes, refusing more than `expected` (exactly that many for a bundle) before and after reading. */
async function fetchBytes(
  url: string,
  deps: LoadDeps,
  init: RequestInit = {},
  expected?: { exactly?: number; atMost?: number },
): Promise<ArrayBuffer> {
  const fetchFn = deps.fetchFn ?? fetch;
  let response: Response;
  try {
    response = await fetchFn(url, init);
  } catch {
    throw new LoadError("offline", "No connection, and the songs are not saved on this device yet.");
  }
  if (!response.ok) throw new LoadError("network", `The server answered ${response.status}.`);
  const limit = expected?.exactly ?? expected?.atMost ?? Number.POSITIVE_INFINITY;
  const announced = Number(response.headers.get("Content-Length"));
  if (announced > limit) throw new LoadError("invalid", TOO_BIG);
  let bytes: ArrayBuffer;
  try {
    bytes = await response.arrayBuffer();
  } catch {
    throw new LoadError("offline", "The connection dropped while the songs were downloading.");
  }
  if (bytes.byteLength > limit || (expected?.exactly !== undefined && bytes.byteLength !== expected.exactly)) {
    throw new LoadError("invalid", TOO_BIG);
  }
  return bytes;
}

function parseJson(bytes: ArrayBuffer): unknown {
  try {
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    throw new LoadError("invalid", "The catalog file could not be read.");
  }
}

function asInvalid(error: unknown): never {
  if (error instanceof LoadError) throw error;
  throw new LoadError("invalid", error instanceof Error ? error.message : "The catalog file is not valid.");
}

declare global {
  interface Window {
    /** Set by the inline boot script on a first visit: the manifest download it already started. */
    __kantahanManifest?: Promise<ArrayBuffer>;
  }
}

/** The download the page started on a first visit, once; never used again (so it cannot go stale). */
function takeEarlyManifest(): Promise<ArrayBuffer> | undefined {
  if (typeof window === "undefined") return undefined;
  const early = window.__kantahanManifest;
  delete window.__kantahanManifest;
  return early;
}

/**
 * The manifest from the server. An explicit check (`fresh`) goes to the network and skips every cache, so
 * nothing stale can hide a pause or a rollback. The very first load has nothing saved to go stale: it uses
 * default caching and may take the download the page already started (see takeEarlyManifest).
 */
export async function fetchManifest(deps: LoadDeps = {}, options: { fresh?: boolean } = {}): Promise<Manifest> {
  try {
    const early = deps.fetchFn || options.fresh ? undefined : takeEarlyManifest();
    if (early) {
      try {
        const bytes = await early;
        if (bytes.byteLength <= MAX_MANIFEST_BYTES) return parseManifest(parseJson(bytes));
      } catch {
        /* the early download failed or was not a manifest: fall through to a normal request */
      }
    }
    const bytes = await fetchBytes(
      `${deps.base ?? CATALOG_BASE}/manifest.json`,
      deps,
      { headers: { Accept: "application/json" }, ...(options.fresh ? { cache: "reload" as const } : {}) },
      { atMost: MAX_MANIFEST_BYTES },
    );
    return parseManifest(parseJson(bytes));
  } catch (error) {
    return asInvalid(error);
  }
}

/** Download a bundle and accept it only if it is exactly what the manifest promised. */
export async function fetchBundle(model: ModelInfo, deps: LoadDeps = {}): Promise<BundleV1> {
  try {
    const bytes = await fetchBytes(`${deps.base ?? CATALOG_BASE}/${model.file}`, deps, {}, { exactly: model.bytes });
    if ((await sha256Hex(bytes)) !== model.sha256) {
      throw new LoadError("invalid", "The downloaded songs did not match their checksum, so they were not used.");
    }
    const bundle = parseBundle(parseJson(bytes));
    if (bundle.model !== model.slug || bundle.count !== model.songs) {
      throw new LoadError("invalid", "The downloaded songs do not match the catalog description.");
    }
    return bundle;
  } catch (error) {
    return asInvalid(error);
  }
}

/** The saved manifest when there is one, otherwise the network. Saved data always wins: the app opens at once. */
export async function loadManifestFromAnywhere(
  deps: LoadDeps = {},
): Promise<{ manifest: Manifest; source: LoadSource }> {
  const saved = await loadManifest();
  if (saved) return { manifest: saved, source: "device" };
  const manifest = await fetchManifest(deps);
  await saveManifest(manifest);
  writeLastCheck(Date.now()); // just downloaded: no need to look again on this visit
  return { manifest, source: "network" };
}

/** One model's songs: the saved copy of this exact bundle, otherwise the network (then saved). */
export async function loadSongs(
  model: ModelInfo,
  manifest: Manifest,
  deps: LoadDeps = {},
): Promise<{ songs: Song[]; source: LoadSource }> {
  const saved = await loadCatalog(model.slug);
  if (saved && saved.sha256 === model.sha256) {
    return { songs: toSongs(saved.bundle), source: "device" };
  }
  const bundle = await fetchBundle(model, deps);
  await saveCatalog({
    slug: model.slug,
    version: manifest.version,
    savedAt: new Date().toISOString(),
    sha256: model.sha256,
    bundle,
  });
  return { songs: toSongs(bundle), source: "network" };
}
