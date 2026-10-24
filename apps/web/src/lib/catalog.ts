import type { BundleV1, HueKey, Manifest, ModelInfo, Song } from "./types";

export class CatalogError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CatalogError";
  }
}

const HUES: readonly HueKey[] = ["magenta", "violet", "aqua", "orange", "lime", "yellow"];
const DIGITS = /^\d+$/;
/** No real catalog comes close; a bigger bundle in a manifest is refused before it is downloaded. */
export const MAX_BUNDLE_BYTES = 25 * 1024 * 1024;
const HEX_SHA256 = /^[0-9a-f]{64}$/;
/** "reyna.json" or "v12/reyna.json": at most one folder, no dots-only segments, no escapes. */
const BUNDLE_PATH = /^(?:[A-Za-z0-9-]+\/)?[A-Za-z0-9-]+\.json$/;

function isHttps(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function strings(value: unknown, field: string): string[] {
  if (!Array.isArray(value) || value.some((v) => typeof v !== "string")) {
    throw new CatalogError(`catalog field "${field}" must be a list of text`);
  }
  return value as string[];
}

function ints(value: unknown, field: string): number[] {
  if (!Array.isArray(value) || value.some((v) => !Number.isInteger(v))) {
    throw new CatalogError(`catalog field "${field}" must be a list of whole numbers`);
  }
  return value as number[];
}

/** Check a catalog bundle read from the network or from storage. Throws CatalogError. */
export function parseBundle(raw: unknown): BundleV1 {
  if (!isRecord(raw) || raw["schema"] !== 1) throw new CatalogError("unsupported catalog format");
  const n = strings(raw["n"], "n");
  const t = strings(raw["t"], "t");
  const a = strings(raw["a"], "a");
  const r = ints(raw["r"], "r");
  const u = ints(raw["u"], "u");
  const releases = strings(raw["releases"], "releases");
  if (typeof raw["model"] !== "string") throw new CatalogError('catalog field "model" is missing');
  if (![t, a, r, u].every((column) => column.length === n.length)) {
    throw new CatalogError("catalog columns have different lengths");
  }
  if (n.some((number) => !DIGITS.test(number))) throw new CatalogError("a song number is not digits");
  if (r.some((index) => index < 0 || index >= releases.length)) {
    throw new CatalogError("a song points to a missing volume");
  }
  return { schema: 1, model: raw["model"], count: n.length, releases, n, t, a, r, u };
}

export function toSongs(bundle: BundleV1): Song[] {
  return bundle.n.map((number, id) => {
    const title = bundle.t[id] ?? "";
    const artist = bundle.a[id] ?? "";
    return {
      id,
      number,
      title,
      artist,
      release: bundle.releases[bundle.r[id] ?? 0] ?? "",
      artistKnown: bundle.u[id] === 0 && artist !== "",
    };
  });
}

function parseModel(raw: unknown): ModelInfo {
  if (!isRecord(raw)) throw new CatalogError("a model entry is not an object");
  const { slug, name, family, hue, file, songs, coverage, sha256, bytes, excluded } = raw;
  if (
    typeof slug !== "string" ||
    typeof name !== "string" ||
    typeof family !== "string" ||
    typeof file !== "string" ||
    typeof coverage !== "string" ||
    !Number.isInteger(songs) ||
    !Number.isInteger(bytes) ||
    typeof sha256 !== "string" ||
    !HUES.includes(hue as HueKey)
  ) {
    throw new CatalogError(`model entry "${String(slug)}" is incomplete`);
  }
  if (!BUNDLE_PATH.test(file)) throw new CatalogError("a model file name is unsafe");
  if ((songs as number) < 1 || (bytes as number) < 1 || (bytes as number) > MAX_BUNDLE_BYTES) {
    throw new CatalogError(`model "${slug}" has an unreasonable size`);
  }
  if (excluded !== undefined && (!Number.isInteger(excluded) || (excluded as number) < 0)) {
    throw new CatalogError(`model "${slug}" has an invalid left-out count`);
  }
  if (!HEX_SHA256.test(sha256)) throw new CatalogError(`model "${slug}" has no valid checksum`);
  return { slug, name, family, hue: hue as HueKey, file, sha256, bytes: bytes as number, songs: songs as number, coverage, ...(excluded ? { excluded: excluded as number } : {}) };
}

export function parseManifest(raw: unknown): Manifest {
  if (!isRecord(raw) || raw["schema"] !== 1) throw new CatalogError("unsupported manifest format");
  const source = raw["source"];
  if (
    typeof raw["version"] !== "string" ||
    typeof raw["generatedAt"] !== "string" ||
    typeof raw["synthetic"] !== "boolean" ||
    typeof raw["suspended"] !== "boolean" ||
    (raw["notice"] !== undefined && typeof raw["notice"] !== "string") ||
    !isRecord(source) ||
    typeof source["label"] !== "string" ||
    typeof source["url"] !== "string" ||
    !Array.isArray(raw["models"])
  ) {
    throw new CatalogError("manifest is incomplete");
  }
  if (!isHttps(source["url"])) throw new CatalogError("the catalog source link must be an https address");
  const models = raw["models"].map(parseModel);
  if (models.length === 0) throw new CatalogError("manifest lists no models");
  return {
    schema: 1,
    version: raw["version"],
    generatedAt: raw["generatedAt"],
    synthetic: raw["synthetic"],
    suspended: raw["suspended"],
    ...(typeof raw["notice"] === "string" ? { notice: raw["notice"] } : {}),
    source: { label: source["label"], url: source["url"] },
    models,
  };
}
