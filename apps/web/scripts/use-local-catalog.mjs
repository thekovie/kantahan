// Stages the catalog published by `kantahan-catalog publish` (or `run`) for local development.
// Copies catalog/work/publish/manifest.json and the live version's bundles into
// public/catalog-local/ (gitignored). Then run: VITE_CATALOG_BASE=/catalog-local npm run dev
import { cpSync, existsSync, mkdirSync, readFileSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const FROM = join(here, "..", "..", "..", "catalog", "work", "publish");
const TO = join(here, "..", "public", "catalog-local");

if (!existsSync(join(FROM, "manifest.json"))) {
  console.error(`No published catalog at ${FROM}. Run \`kantahan-catalog publish\` first (see docs/setup-development.md).`);
  process.exit(1);
}
const manifest = JSON.parse(readFileSync(join(FROM, "manifest.json"), "utf8"));
rmSync(TO, { recursive: true, force: true });
mkdirSync(TO, { recursive: true });
cpSync(join(FROM, manifest.version), join(TO, manifest.version), { recursive: true });
cpSync(join(FROM, "manifest.json"), join(TO, "manifest.json"));
console.log(`staged catalog ${manifest.version} (${manifest.models.length} model(s)) in ${TO}\nRun: VITE_CATALOG_BASE=/catalog-local npm run dev`);
