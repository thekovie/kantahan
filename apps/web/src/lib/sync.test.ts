import { afterEach, describe, expect, it } from "vitest";
import { MODEL_B_ROWS, fakeFetch, makeBundle, makeManifest, modelEntry, wipeStorage } from "../test-utils";
import { readLastCheck } from "./prefs";
import { loadCatalog, loadManifest, saveCatalog, saveManifest } from "./storage";
import { checkForUpdates } from "./sync";

afterEach(async () => {
  await wipeStorage();
});

const v1 = makeManifest({ version: "v1" });
const a1 = makeBundle();
const a2 = makeBundle([...[["00589", "Hurting Each Other", "Sample Artist A"] as const], ["77777", "Brand New Song", "New Artist"]]);
const b1 = makeBundle(MODEL_B_ROWS, "model-b");

/** Device state after using v1: manifest saved, model A saved. */
async function installV1() {
  await saveManifest(v1);
  await saveCatalog({ slug: "model-a", version: "v1", savedAt: "then", sha256: v1.models[0]!.sha256, bundle: a1 });
}

/** A v2 catalog where model A changed and model B did not. */
function v2Catalog(overrides = {}) {
  const manifest = makeManifest({
    version: "v2",
    models: [modelEntry("model-a", a2, "Model A", "magenta", "v2/model-a.json"), modelEntry("model-b", b1, "Model B", "aqua", "v2/model-b.json")],
    ...overrides,
  });
  return { manifest, routes: { "/catalog/manifest.json": manifest, "/catalog/v2/model-a.json": a2, "/catalog/v2/model-b.json": b1 } };
}

describe("checkForUpdates", () => {
  it("says up to date when the version has not changed, downloading nothing", async () => {
    await installV1();
    const fetchFn = fakeFetch({ "/catalog/manifest.json": v1 });
    const result = await checkForUpdates({ fetchFn });
    expect(result.status).toBe("up-to-date");
    expect(fetchFn.calls).toHaveLength(1);
    expect(readLastCheck()).not.toBeNull();
  });

  it("downloads only the saved model that changed and saves it with the new manifest", async () => {
    await installV1();
    const { manifest, routes } = v2Catalog();
    const fetchFn = fakeFetch(routes);
    const result = await checkForUpdates({ fetchFn });
    expect(result.status).toBe("updated");
    expect((await loadManifest())?.version).toBe("v2");
    expect((await loadCatalog("model-a"))?.bundle.n).toContain("77777");
    expect((await loadCatalog("model-a"))?.sha256).toBe(manifest.models[0]!.sha256);
    expect(await loadCatalog("model-b")).toBeNull(); // never opened on this device, so not downloaded
    expect(fetchFn.calls.some((url) => url.endsWith("model-b.json"))).toBe(false);
  });

  it("keeps the old catalog when a download does not match its checksum", async () => {
    await installV1();
    const { routes } = v2Catalog();
    const tampered = makeBundle([["00589", "Hurting Each Other", "Sample Artist A"], ["77777", "Brand New Sonk", "New Artist"]]);
    const fetchFn = fakeFetch({ ...routes, "/catalog/v2/model-a.json": tampered });
    const result = await checkForUpdates({ fetchFn });
    expect(result).toMatchObject({ status: "failed", message: expect.stringMatching(/checksum.*kept/) });
    expect((await loadManifest())?.version).toBe("v1");
    expect((await loadCatalog("model-a"))?.bundle.n).not.toContain("77777");
  });

  it("keeps the old catalog and says offline when the connection fails", async () => {
    await installV1();
    const fetchFn = (async () => {
      throw new TypeError("offline");
    }) as unknown as typeof fetch;
    expect(await checkForUpdates({ fetchFn })).toEqual({ status: "offline" });
    expect((await loadManifest())?.version).toBe("v1");
  });

  it("changes nothing when a bundle download drops halfway through the update", async () => {
    await installV1();
    const { routes } = v2Catalog();
    const { "/catalog/v2/model-a.json": _unused, ...withoutBundle } = routes;
    const result = await checkForUpdates({ fetchFn: fakeFetch(withoutBundle) });
    expect(result.status).toBe("failed");
    expect((await loadManifest())?.version).toBe("v1");
  });

  it("stores a suspended manifest without downloading songs, and recovers when resumed", async () => {
    await installV1();
    const { manifest, routes } = v2Catalog({ suspended: true, notice: "Paused for review." });
    const fetchFn = fakeFetch(routes);
    const result = await checkForUpdates({ fetchFn });
    expect(result).toMatchObject({ status: "suspended", manifest: { notice: "Paused for review." } });
    expect(fetchFn.calls).toHaveLength(1);
    expect((await loadCatalog("model-a"))?.bundle.n).not.toContain("77777"); // old copy still there, but hidden

    const resumed = { ...manifest, suspended: false, notice: undefined };
    delete (resumed as { notice?: string }).notice;
    const after = await checkForUpdates({ fetchFn: fakeFetch({ ...routes, "/catalog/manifest.json": resumed }) });
    expect(after.status).toBe("updated");
    expect((await loadCatalog("model-a"))?.bundle.n).toContain("77777");
  });

  it("follows a rollback to an older version, not only newer ones", async () => {
    const { manifest, routes } = v2Catalog();
    await saveManifest(manifest);
    await saveCatalog({ slug: "model-a", version: "v2", savedAt: "then", sha256: manifest.models[0]!.sha256, bundle: a2 });
    const back = { ...v1, models: [{ ...v1.models[0]!, file: "v1/model-a.json" }, { ...v1.models[1]!, file: "v1/model-b.json" }] };
    const fetchFn = fakeFetch({ ...routes, "/catalog/manifest.json": back, "/catalog/v1/model-a.json": a1 });
    expect((await checkForUpdates({ fetchFn })).status).toBe("updated");
    expect((await loadManifest())?.version).toBe("v1");
    expect((await loadCatalog("model-a"))?.bundle.n).not.toContain("77777");
  });

  it("removes saved songs of a model that left the catalog", async () => {
    await installV1();
    await saveCatalog({ slug: "model-b", version: "v1", savedAt: "then", sha256: v1.models[1]!.sha256, bundle: b1 });
    const onlyA = makeManifest({ version: "v2", models: [v1.models[0]!] });
    const result = await checkForUpdates({ fetchFn: fakeFetch({ "/catalog/manifest.json": onlyA }) });
    expect(result.status).toBe("updated");
    expect(await loadCatalog("model-b")).toBeNull();
    expect((await loadCatalog("model-a"))?.bundle.count).toBe(a1.count);
  });

  it("reports a server error without touching the saved catalog", async () => {
    await installV1();
    const result = await checkForUpdates({ fetchFn: fakeFetch({}) });
    expect(result).toMatchObject({ status: "failed" });
    expect((await loadManifest())?.version).toBe("v1");
  });

  it("does not accept a manifest from the future format", async () => {
    await installV1();
    const result = await checkForUpdates({ fetchFn: fakeFetch({ "/catalog/manifest.json": { schema: 2 } }) });
    expect(result.status).toBe("failed");
  });
});

describe("checkForUpdates, overlapping calls", () => {
  it("runs one comparison at a time and shares its answer", async () => {
    await installV1();
    const { routes } = v2Catalog();
    const fetchFn = fakeFetch(routes);
    const [first, second] = await Promise.all([checkForUpdates({ fetchFn }), checkForUpdates({ fetchFn })]);
    expect(first).toBe(second);
    expect(fetchFn.calls.filter((url) => url.endsWith("manifest.json"))).toHaveLength(1);
    expect((await checkForUpdates({ fetchFn })).status).toBe("up-to-date");
  });
});

describe("checkForUpdates, size limits", () => {
  it("refuses a download that is not exactly the announced size, without saving it", async () => {
    await installV1();
    const { manifest, routes } = v2Catalog();
    const smaller = { ...manifest, models: manifest.models.map((m, i) => (i === 0 ? { ...m, bytes: m.bytes - 1 } : m)) };
    const result = await checkForUpdates({ fetchFn: fakeFetch({ ...routes, "/catalog/manifest.json": smaller }) });
    expect(result).toMatchObject({ status: "failed", message: expect.stringContaining("larger than the catalog said") });
    expect((await loadManifest())?.version).toBe("v1");
  });
});
