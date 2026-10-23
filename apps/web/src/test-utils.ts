import { parseBundle, toSongs } from "./lib/catalog";
import type { BundleV1, Manifest, Song } from "./lib/types";

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

export function makeBundle(rows: readonly (readonly [string, string, string])[] = SAMPLE): BundleV1 {
  return parseBundle({
    schema: 1,
    model: "model-a",
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

export function makeManifest(overrides: Partial<Manifest> = {}): Manifest {
  return {
    schema: 1,
    version: "2026.10.23",
    generatedAt: "2026-10-23T12:00:00Z",
    synthetic: true,
    source: { label: "Synthetic demo data", url: "https://example.test/source" },
    models: [
      { slug: "model-a", name: "Model A", family: "Demo family", hue: "magenta", file: "model-a.json", songs: SAMPLE.length, coverage: "Demo volume 1" },
      { slug: "model-b", name: "Model B", family: "Demo family", hue: "aqua", file: "model-b.json", songs: 2, coverage: "Demo volume 1" },
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
