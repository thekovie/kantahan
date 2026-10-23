// Stages the real catalog built by `kantahan-catalog build` for local development.
// Copies catalog/work/releases/<model>.json into public/catalog-local/ (gitignored) and writes a
// manifest next to it. Then run: VITE_CATALOG_BASE=/catalog-local npm run dev
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const FROM = join(here, "..", "..", "..", "catalog", "work", "releases");
const TO = join(here, "..", "public", "catalog-local");

// Display details per model slug. Only models with verified data appear here.
const KNOWN = {
  reyna: { name: "Reyna", family: "Reyna series", hue: "magenta" },
};

if (!existsSync(FROM)) {
  console.error(`No built catalog at ${FROM}. Run the catalog pipeline first (see docs/setup-development.md).`);
  process.exit(1);
}

const files = readdirSync(FROM).filter((f) => /^[a-z0-9-]+\.json$/.test(f));
mkdirSync(TO, { recursive: true });
const models = [];
const hash = createHash("sha256");
for (const file of files) {
  const slug = file.replace(/\.json$/, "");
  const known = KNOWN[slug];
  if (!known) {
    console.warn(`skipping ${file}: no display details for model "${slug}" in this script`);
    continue;
  }
  const raw = readFileSync(join(FROM, file));
  const bundle = JSON.parse(raw.toString("utf8"));
  hash.update(raw);
  writeFileSync(join(TO, file), raw);
  // Labels look like "Volume 62" or "Volume 64-65"; show the span they cover.
  const numbers = bundle.releases.flatMap((label) => (String(label).match(/\d+/g) ?? []).map(Number));
  const coverage = numbers.length ? `Volumes ${Math.min(...numbers)} to ${Math.max(...numbers)}` : "Volumes not stated";
  models.push({ slug, ...known, file, songs: bundle.count, coverage });
}
if (models.length === 0) {
  console.error("Nothing staged.");
  process.exit(1);
}
const manifest = {
  schema: 1,
  version: `local-${hash.digest("hex").slice(0, 8)}`,
  generatedAt: new Date().toISOString(),
  synthetic: false,
  source: { label: "Platinum Karaoke song list updates", url: "https://platinumkaraoke.com/pages/songlist-update" },
  models,
};
writeFileSync(join(TO, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n");
console.log(`staged ${models.length} model(s) in ${TO}\nRun: VITE_CATALOG_BASE=/catalog-local npm run dev`);
