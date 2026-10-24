import { type LoadDeps, LoadError, fetchBundle, fetchManifest } from "./loader";
import { writeLastCheck } from "./prefs";
import { type StoredCatalog, commitUpdate, loadCatalog, loadManifest } from "./storage";
import type { Manifest } from "./types";

export type SyncResult =
  | { status: "up-to-date"; manifest: Manifest }
  | { status: "updated"; manifest: Manifest }
  | { status: "suspended"; manifest: Manifest }
  | { status: "offline" }
  | { status: "failed"; message: string };

const sameState = (a: Manifest, b: Manifest): boolean =>
  a.version === b.version && a.suspended === b.suspended && a.notice === b.notice;

/**
 * Look for a newer catalog and, when there is one, make it the saved catalog.
 *
 * Everything is downloaded and checked first (checksum, format, song count). Only then are the
 * new manifest and bundles written in one transaction, so a dropped connection, a corrupt file
 * or a full disk leaves the catalog on the device exactly as it was. Only the models already
 * saved on this device are downloaded; others are fetched when first opened.
 */
export function checkForUpdates(deps: LoadDeps = {}): Promise<SyncResult> {
  // One comparison at a time: a slow older answer must never overwrite a newer one.
  inFlight ??= runCheck(deps).finally(() => {
    inFlight = null;
  });
  return inFlight;
}

let inFlight: Promise<SyncResult> | null = null;

async function runCheck(deps: LoadDeps): Promise<SyncResult> {
  const saved = await loadManifest();
  let fresh: Manifest;
  try {
    fresh = await fetchManifest(deps, { fresh: true });
  } catch (error) {
    return failure(error);
  }

  if (saved && sameState(saved, fresh)) {
    writeLastCheck(Date.now());
    return { status: "up-to-date", manifest: saved };
  }

  const records: StoredCatalog[] = [];
  if (!fresh.suspended) {
    for (const model of fresh.models) {
      const have = await loadCatalog(model.slug);
      if (!have || have.sha256 === model.sha256) continue;
      try {
        const bundle = await fetchBundle(model, deps);
        records.push({
          slug: model.slug,
          version: fresh.version,
          savedAt: new Date().toISOString(),
          sha256: model.sha256,
          bundle,
        });
      } catch (error) {
        return failure(error);
      }
    }
  }

  const gone = (saved?.models ?? []).map((m) => m.slug).filter((s) => !fresh.models.some((m) => m.slug === s));
  if (!(await commitUpdate(fresh, records, gone))) {
    return { status: "failed", message: "The update could not be saved on this device. Your saved songs were kept." };
  }
  writeLastCheck(Date.now());
  if (fresh.suspended) return { status: "suspended", manifest: fresh };
  const changed = !saved || saved.version !== fresh.version || records.length > 0;
  return { status: changed ? "updated" : "up-to-date", manifest: fresh };
}

function failure(error: unknown): SyncResult {
  if (error instanceof LoadError && error.kind === "offline") return { status: "offline" };
  const message = error instanceof Error ? error.message : "The update failed.";
  return { status: "failed", message: `${message} Your saved songs were kept.` };
}
