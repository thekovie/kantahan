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
});
