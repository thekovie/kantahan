// Generates the demo catalog in public/catalog/. Every title and artist is invented from word
// lists; none of it is real song data. Deterministic, so re-running changes nothing.
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "public", "catalog");

const ADJECTIVES = ["Neon", "Velvet", "Paper", "Quiet", "Golden", "Midnight", "Tiny", "Electric", "Lazy", "Crimson", "Salt", "Sunday", "Glass", "Wild", "Soft", "Orange", "Distant", "Borrowed", "Slow", "Bright"];
const NOUNS = ["Harbor", "Static", "Parade", "Lantern", "Weather", "Carousel", "Postcard", "Engine", "Garden", "Skyline", "Echo", "Kite", "Window", "Ribbon", "Season", "Rooftop", "Compass", "Orchard", "Signal", "Tide"];
const ENDINGS = ["", "", "", " (Part Two)", " Again", " Tonight", " In Blue", " Forever"];
const ACTS = ["The Placeholders", "Sample Sisters", "Ana Reyes-Demo", "Mock Orchestra", "Lorem Ipsum Band", "Dummy Duo", "Test Pattern", "Faux Fiesta", "Cebu Sample Club", "Demo Dela Cruz", "The Fictions", "Nena Placeholder"];

function rng(seed) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function makeModel(slug, seed, count, firstNumber, withheldEvery) {
  const next = rng(seed);
  const pick = (list) => list[Math.floor(next() * list.length)];
  const rows = [];
  const seen = new Set();
  while (rows.length < count) {
    const title = `${pick(ADJECTIVES)} ${pick(NOUNS)}${pick(ENDINGS)}`;
    const artist = pick(ACTS);
    const key = `${title}|${artist}`;
    if (seen.has(key)) continue;
    seen.add(key);
    rows.push({ title, artist });
  }
  rows.sort((a, b) => a.title.localeCompare(b.title));
  return {
    schema: 1,
    model: slug,
    count,
    releases: ["Demo volume 1", "Demo volume 2"],
    n: rows.map((_, i) => String(firstNumber + i).padStart(5, "0")),
    t: rows.map((r) => r.title),
    a: rows.map((r, i) => (withheldEvery && i % withheldEvery === 0 ? "" : r.artist)),
    r: rows.map((_, i) => (i < count / 2 ? 0 : 1)),
    u: rows.map((_, i) => (withheldEvery && i % withheldEvery === 0 ? 1 : 0)),
  };
}

const models = [
  { slug: "demo-a", name: "Model A", family: "Demo family one", hue: "magenta", seed: 11, count: 1200, first: 15000, withheld: 0, coverage: "Demo volumes 1 and 2" },
  { slug: "demo-b", name: "Model B", family: "Demo family two", hue: "aqua", seed: 23, count: 420, first: 38000, withheld: 25, coverage: "Demo volumes 1 and 2" },
  { slug: "demo-c", name: "Model C", family: "Demo family three", hue: "lime", seed: 37, count: 160, first: 590, withheld: 0, coverage: "Demo volumes 1 and 2" },
];

mkdirSync(OUT, { recursive: true });
for (const m of models) {
  writeFileSync(join(OUT, `${m.slug}.json`), JSON.stringify(makeModel(m.slug, m.seed, m.count, m.first, m.withheld)));
}
const manifest = {
  schema: 1,
  version: "demo-1",
  generatedAt: "2026-10-23T00:00:00Z",
  synthetic: true,
  source: { label: "Synthetic demo data, not a real catalog", url: "https://github.com/thekovie/kantahan" },
  models: models.map((m) => ({ slug: m.slug, name: m.name, family: m.family, hue: m.hue, file: `${m.slug}.json`, songs: m.count, coverage: m.coverage })),
};
writeFileSync(join(OUT, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`wrote ${models.length} demo bundles and manifest.json to ${OUT}`);
