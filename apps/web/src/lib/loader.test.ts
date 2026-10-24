import { afterEach, describe, expect, it } from "vitest";
import { TAMPERED_ROWS, fakeFetch, makeBundle, makeManifest, sha256, wipeStorage } from "../test-utils";
import { LoadError, loadManifestFromAnywhere, loadSongs } from "./loader";
import { loadCatalog, saveCatalog, saveManifest } from "./storage";

afterEach(async () => {
  await wipeStorage();
});

const manifest = makeManifest();
const model = manifest.models[0]!;

describe("loadManifestFromAnywhere", () => {
  it("prefers the copy saved on the device and does not touch the network", async () => {
    await saveManifest(manifest);
    const fetchFn = fakeFetch({});
    const result = await loadManifestFromAnywhere({ fetchFn });
    expect(result.source).toBe("device");
    expect(fetchFn.calls).toEqual([]);
  });

  it("downloads once, then keeps a copy for next time", async () => {
    const fetchFn = fakeFetch({ "/catalog/manifest.json": manifest });
    expect((await loadManifestFromAnywhere({ fetchFn })).source).toBe("network");
    expect((await loadManifestFromAnywhere({ fetchFn })).source).toBe("device");
    expect(fetchFn.calls).toHaveLength(1);
  });

  it("says offline when there is nothing saved and no connection", async () => {
    const fetchFn = (async () => {
      throw new TypeError("Failed to fetch");
    }) as unknown as typeof fetch;
    await expect(loadManifestFromAnywhere({ fetchFn })).rejects.toMatchObject({ kind: "offline" });
  });

  it("reports a server error and an unreadable file differently", async () => {
    await expect(loadManifestFromAnywhere({ fetchFn: fakeFetch({}) })).rejects.toMatchObject({ kind: "network" });
    const broken = (async () => new Response("<html>", { status: 200 })) as unknown as typeof fetch;
    await expect(loadManifestFromAnywhere({ fetchFn: broken })).rejects.toBeInstanceOf(LoadError);
    const wrong = fakeFetch({ "/catalog/manifest.json": { schema: 9 } });
    await expect(loadManifestFromAnywhere({ fetchFn: wrong })).rejects.toMatchObject({ kind: "invalid" });
  });
});

describe("loadSongs", () => {
  it("reads the saved bundle for the same catalog version", async () => {
    await saveCatalog({ slug: model.slug, version: manifest.version, savedAt: "now", sha256: model.sha256, bundle: makeBundle() });
    const fetchFn = fakeFetch({});
    const { songs, source } = await loadSongs(model, manifest, { fetchFn });
    expect(source).toBe("device");
    expect(songs[0]?.number).toBe("00589");
    expect(fetchFn.calls).toEqual([]);
  });

  it("downloads and saves a bundle that is missing or differs from the catalog's", async () => {
    await saveCatalog({ slug: model.slug, version: "old", savedAt: "now", sha256: sha256("older"), bundle: makeBundle() });
    const fetchFn = fakeFetch({ "/catalog/model-a.json": makeBundle() });
    expect((await loadSongs(model, manifest, { fetchFn })).source).toBe("network");
    expect((await loadSongs(model, manifest, { fetchFn })).source).toBe("device");
    expect(fetchFn.calls).toHaveLength(1);
  });

  it("fails clearly when offline with nothing saved", async () => {
    const fetchFn = (async () => {
      throw new TypeError("offline");
    }) as unknown as typeof fetch;
    await expect(loadSongs(model, manifest, { fetchFn })).rejects.toMatchObject({ kind: "offline" });
  });

  it("rejects a bundle that fails validation", async () => {
    const broken = { schema: 1, model: "model-a", n: ["1"], t: [], a: [], r: [], u: [], releases: [] };
    const entry = { ...model, sha256: sha256(JSON.stringify(broken)) };
    const fetchFn = fakeFetch({ "/catalog/model-a.json": broken });
    await expect(loadSongs(entry, manifest, { fetchFn })).rejects.toMatchObject({ kind: "invalid" });
  });

  it("rejects a download whose checksum differs from the manifest and saves nothing", async () => {
    const tampered = makeBundle(TAMPERED_ROWS);
    const fetchFn = fakeFetch({ "/catalog/model-a.json": tampered });
    await expect(loadSongs(model, manifest, { fetchFn })).rejects.toMatchObject({
      kind: "invalid",
      message: expect.stringContaining("checksum"),
    });
    expect(await loadCatalog(model.slug)).toBeNull();
  });

  it("rejects a bundle for another model or with a different song count", async () => {
    const other = { ...model, slug: "model-b" };
    const fetchFn = fakeFetch({ "/catalog/model-a.json": makeBundle() });
    await expect(loadSongs(other, manifest, { fetchFn })).rejects.toMatchObject({ kind: "invalid" });
    const wrongCount = { ...model, songs: model.songs + 1 };
    await expect(loadSongs(wrongCount, manifest, { fetchFn })).rejects.toMatchObject({ kind: "invalid" });
  });
});
