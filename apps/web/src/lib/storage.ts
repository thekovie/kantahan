import { type DBSchema, type IDBPDatabase, openDB } from "idb";
import { parseBundle, parseManifest } from "./catalog";
import type { BundleV1, Manifest } from "./types";

const DB_NAME = "kantahan";
const DB_VERSION = 1;
const MANIFEST_KEY = "manifest";

export interface StoredCatalog {
  slug: string;
  /** Catalog version the bundle belongs to. */
  version: string;
  savedAt: string;
  bundle: BundleV1;
}

interface KantahanDB extends DBSchema {
  catalogs: { key: string; value: StoredCatalog };
  meta: { key: string; value: { key: string; manifest: Manifest } };
}

let opening: Promise<IDBPDatabase<KantahanDB> | null> | null = null;

function open(): Promise<IDBPDatabase<KantahanDB> | null> {
  opening ??= (async () => {
    if (typeof indexedDB === "undefined") return null;
    try {
      return await openDB<KantahanDB>(DB_NAME, DB_VERSION, {
        upgrade(db) {
          db.createObjectStore("catalogs", { keyPath: "slug" });
          db.createObjectStore("meta", { keyPath: "key" });
        },
      });
    } catch {
      return null; // private windows and blocked storage: the app still works from the network
    }
  })();
  return opening;
}

/** Forget the open connection (tests, or after storage was cleared). */
export function resetStorage(): void {
  opening?.then((db) => db?.close()).catch(() => undefined);
  opening = null;
}

export async function saveCatalog(record: StoredCatalog): Promise<boolean> {
  const db = await open();
  if (!db) return false;
  try {
    await db.put("catalogs", record);
    return true;
  } catch {
    return false;
  }
}

/** A stored bundle that no longer validates is deleted and reported as missing. */
export async function loadCatalog(slug: string): Promise<StoredCatalog | null> {
  const db = await open();
  if (!db) return null;
  try {
    const record = await db.get("catalogs", slug);
    if (!record) return null;
    return { ...record, bundle: parseBundle(record.bundle) };
  } catch {
    await db.delete("catalogs", slug).catch(() => undefined);
    return null;
  }
}

export async function saveManifest(manifest: Manifest): Promise<boolean> {
  const db = await open();
  if (!db) return false;
  try {
    await db.put("meta", { key: MANIFEST_KEY, manifest });
    return true;
  } catch {
    return false;
  }
}

export async function loadManifest(): Promise<Manifest | null> {
  const db = await open();
  if (!db) return null;
  try {
    const row = await db.get("meta", MANIFEST_KEY);
    return row ? parseManifest(row.manifest) : null;
  } catch {
    await db.delete("meta", MANIFEST_KEY).catch(() => undefined);
    return null;
  }
}
