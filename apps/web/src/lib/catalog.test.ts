import { describe, expect, it } from "vitest";
import { makeBundle, makeManifest } from "../test-utils";
import { CatalogError, parseBundle, parseManifest, toSongs } from "./catalog";

const valid = () => JSON.parse(JSON.stringify(makeBundle()));

describe("parseBundle", () => {
  it("accepts a valid bundle and keeps numbers as text", () => {
    const bundle = parseBundle(valid());
    expect(bundle.n[0]).toBe("00589");
    expect(bundle.count).toBe(bundle.n.length);
  });

  it.each([
    ["wrong schema", (b: Record<string, unknown>) => (b["schema"] = 2)],
    ["not an object", (_b: Record<string, unknown>) => undefined],
    ["column length mismatch", (b: Record<string, unknown>) => (b["t"] = ["only one"])],
    ["a number that is not digits", (b: Record<string, unknown>) => (b["n"] = ["12a45", ...(b["n"] as string[]).slice(1)])],
    ["a number stored as a JSON number", (b: Record<string, unknown>) => (b["n"] = [589, ...(b["n"] as string[]).slice(1)])],
    ["a volume index out of range", (b: Record<string, unknown>) => (b["r"] = (b["r"] as number[]).map(() => 5))],
    ["missing model", (b: Record<string, unknown>) => delete b["model"]],
  ])("rejects %s", (name, mutate) => {
    const raw = valid();
    mutate(raw);
    expect(() => parseBundle(name === "not an object" ? "nope" : raw)).toThrow(CatalogError);
  });
});

describe("toSongs", () => {
  it("marks withheld artists as unknown", () => {
    const songs = toSongs(makeBundle());
    const zebra = songs.find((s) => s.title === "Zebra Crossing");
    expect(zebra?.artistKnown).toBe(false);
    expect(songs[0]?.artistKnown).toBe(true);
    expect(songs[0]?.release).toBe("Volume 1");
  });
});

describe("parseManifest", () => {
  it("accepts a valid manifest", () => {
    expect(parseManifest(makeManifest()).models).toHaveLength(2);
  });

  it("rejects an unknown colour, an unsafe file name and an empty model list", () => {
    const bad = makeManifest();
    expect(() => parseManifest({ ...bad, models: [{ ...bad.models[0], hue: "pink" }] })).toThrow(CatalogError);
    expect(() => parseManifest({ ...bad, models: [{ ...bad.models[0], file: "../secret.json" }] })).toThrow(CatalogError);
    expect(() => parseManifest({ ...bad, models: [] })).toThrow(CatalogError);
    expect(() => parseManifest({ ...bad, version: 3 })).toThrow(CatalogError);
    expect(() => parseManifest(null)).toThrow(CatalogError);
  });

  it("requires a checksum and the suspended flag, and accepts versioned bundle paths", () => {
    const good = makeManifest();
    const versioned = { ...good, models: [{ ...good.models[0], file: "v12/model-a.json" }] };
    expect(parseManifest(versioned).models[0]?.file).toBe("v12/model-a.json");
    expect(() => parseManifest({ ...good, models: [{ ...good.models[0], sha256: "abc" }] })).toThrow(CatalogError);
    expect(() => parseManifest({ ...good, suspended: undefined })).toThrow(CatalogError);
    expect(() => parseManifest({ ...good, notice: 5 })).toThrow(CatalogError);
    for (const file of ["a/b/c.json", "/abs.json", "v1/../x.json", "x.exe", "v1\\x.json", "https://evil.test/x.json"]) {
      expect(() => parseManifest({ ...good, models: [{ ...good.models[0], file }] })).toThrow(CatalogError);
    }
  });

  it("refuses a source link that is not https and sizes that make no sense", () => {
    const good = makeManifest();
    for (const url of ["javascript:alert(1)", "data:text/html,x", "http://insecure.test", "not a url"]) {
      expect(() => parseManifest({ ...good, source: { label: "x", url } })).toThrow(CatalogError);
    }
    for (const patch of [{ bytes: 0 }, { bytes: 26 * 1024 * 1024 }, { bytes: 1.5 }, { songs: 0 }]) {
      expect(() => parseManifest({ ...good, models: [{ ...good.models[0], ...patch }] })).toThrow(CatalogError);
    }
  });

  it("accepts a left-out count and rejects a nonsense one", () => {
    const good = makeManifest();
    const withCount = parseManifest({ ...good, models: [{ ...good.models[0], excluded: 12 }] });
    expect(withCount.models[0]?.excluded).toBe(12);
    expect(parseManifest(good).models[0]?.excluded).toBeUndefined();
    for (const excluded of [-1, 1.5, "3"]) {
      expect(() => parseManifest({ ...good, models: [{ ...good.models[0], excluded }] })).toThrow(CatalogError);
    }
  });

  it("keeps the notice of a suspended catalog", () => {
    const parsed = parseManifest({ ...makeManifest(), suspended: true, notice: "Paused." });
    expect(parsed.suspended).toBe(true);
    expect(parsed.notice).toBe("Paused.");
  });
});
