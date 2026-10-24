import { openDB } from "idb";
import { afterEach, describe, expect, it } from "vitest";
import { makeBundle, makeManifest, wipeStorage } from "../test-utils";
import { loadCatalog, loadManifest, resetStorage, saveCatalog, saveManifest } from "./storage";

afterEach(async () => {
  await wipeStorage();
});

describe("storage", () => {
  it("returns nothing before anything is saved", async () => {
    expect(await loadManifest()).toBeNull();
    expect(await loadCatalog("model-a")).toBeNull();
  });

  it("round-trips a manifest and a bundle, keeping leading zeros", async () => {
    expect(await saveManifest(makeManifest())).toBe(true);
    expect(await saveCatalog({ slug: "model-a", version: "v1", savedAt: "now", bundle: makeBundle() })).toBe(true);
    expect((await loadManifest())?.version).toBe("2026.10.23");
    const stored = await loadCatalog("model-a");
    expect(stored?.version).toBe("v1");
    expect(stored?.bundle.n[0]).toBe("00589");
  });

  it("drops a stored bundle that no longer validates", async () => {
    await saveCatalog({ slug: "model-a", version: "v1", savedAt: "now", bundle: makeBundle() });
    const db = await openDB("kantahan", 1);
    await db.put("catalogs", { slug: "model-a", version: "v1", savedAt: "now", bundle: { schema: 1, broken: true } });
    db.close();
    expect(await loadCatalog("model-a")).toBeNull();
    expect(await loadCatalog("model-a")).toBeNull();
  });

  it("drops a stored manifest that no longer validates", async () => {
    await saveManifest(makeManifest());
    const db = await openDB("kantahan", 1);
    await db.put("meta", { key: "manifest", manifest: { nope: true } });
    db.close();
    expect(await loadManifest()).toBeNull();
  });

  it("keeps working when IndexedDB is unavailable", async () => {
    const original = globalThis.indexedDB;
    resetStorage();
    // @ts-expect-error simulating a browser without IndexedDB
    delete globalThis.indexedDB;
    try {
      expect(await saveManifest(makeManifest())).toBe(false);
      expect(await loadManifest()).toBeNull();
      expect(await saveCatalog({ slug: "x", version: "v", savedAt: "now", bundle: makeBundle() })).toBe(false);
      expect(await loadCatalog("x")).toBeNull();
    } finally {
      globalThis.indexedDB = original;
      resetStorage();
    }
  });
});
