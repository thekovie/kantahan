import { createHash } from "node:crypto";
import { parseBundle, toSongs } from "./lib/catalog";
import type { BundleV1, HueKey, Manifest, ModelInfo, Song } from "./lib/types";

/** Clearly synthetic songs for tests: [number, title, artist]. */
export const SAMPLE: readonly (readonly [string, string, string])[] = [
  ["00589", "Hurting Each Other", "Sample Artist A"],
  ["03150", "Hurting Each Other", "Sample Artist B"],
  ["15562", "Ako'y Para Sa'yo", "Sample Artist C"],
  ["15563", "Dahilan", "Sample Artist D"],
  ["15564", "Dati", "Sample Artist D"],
  ["15589", "Café Nights & Neon", "Sample Artist E"],
  ["15600", "Zebra Crossing", ""],
  ["42236", "24/7, 365", "Sample Artist F"],
];

export const MODEL_B_ROWS: readonly (readonly [string, string, string])[] = [
  ["20001", "Beta Song One", "Beta Artist"],
  ["20002", "Beta Song Two", "Beta Artist"],
];

/** SAMPLE with one title changed to text of the same length, so only the checksum can tell. */
export const TAMPERED_ROWS = SAMPLE.map((row) => (row[0] === "00589" ? ([row[0], "Hurting Eachxother", row[2]] as const) : row));

export const sha256 = (text: string): string => createHash("sha256").update(text).digest("hex");

export function makeBundle(
  rows: readonly (readonly [string, string, string])[] = SAMPLE,
  model = "model-a",
): BundleV1 {
  return parseBundle({
    schema: 1,
    model,
    count: rows.length,
    releases: ["Volume 1"],
    n: rows.map((r) => r[0]),
    t: rows.map((r) => r[1]),
    a: rows.map((r) => r[2]),
    r: rows.map(() => 0),
    u: rows.map((r) => (r[2] === "" ? 1 : 0)),
  });
}

export function makeSongs(rows: readonly (readonly [string, string, string])[] = SAMPLE): Song[] {
  return toSongs(makeBundle(rows));
}

/** A manifest entry that matches the bundle exactly (checksum and size of its JSON text). */
export function modelEntry(slug: string, bundle: BundleV1, name: string, hue: HueKey, file = `${slug}.json`): ModelInfo {
  const text = JSON.stringify(bundle);
  return {
    slug,
    name,
    family: "Demo family",
    hue,
    file,
    sha256: sha256(text),
    bytes: new TextEncoder().encode(text).length,
    songs: bundle.count,
    coverage: "Demo volume 1",
  };
}

export function makeManifest(overrides: Partial<Manifest> = {}): Manifest {
  return {
    schema: 1,
    version: "2026.10.23",
    generatedAt: "2026-10-23T12:00:00Z",
    synthetic: true,
    suspended: false,
    source: { label: "Synthetic demo data", url: "https://example.test/source" },
    models: [
      modelEntry("model-a", makeBundle(), "Model A", "magenta"),
      modelEntry("model-b", makeBundle(MODEL_B_ROWS, "model-b"), "Model B", "aqua"),
    ],
    ...overrides,
  };
}

/** A fetch stand-in that serves JSON by URL suffix and records calls. */
export function fakeFetch(routes: Record<string, unknown>): typeof fetch & { calls: string[] } {
  const calls: string[] = [];
  const impl = async (input: RequestInfo | URL): Promise<Response> => {
    const url = String(input);
    calls.push(url);
    const key = Object.keys(routes).find((suffix) => url.endsWith(suffix));
    if (!key) return new Response("not found", { status: 404 });
    return new Response(JSON.stringify(routes[key]), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  return Object.assign(impl, { calls }) as typeof fetch & { calls: string[] };
}
