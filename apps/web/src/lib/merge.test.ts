import { describe, expect, it } from "vitest";
import { mergeAcrossMachines } from "./merge";
import type { Song } from "./types";

let next = 0;
function song(number: string, title: string, artist: string, release = "Volume 1"): Song {
  return { id: next++, number, title, artist, release, artistKnown: artist !== "" };
}

describe("mergeAcrossMachines", () => {
  it("shows one row when machines use the same number for the same song, in manifest order", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("15560", "Neon Carousel", "Lorem Ipsum Band")] },
      { slug: "b", songs: [song("15560", "Neon Carousel", "Lorem Ipsum Band")] },
      { slug: "c", songs: [song("15560", "Neon Carousel", "Lorem Ipsum Band")] },
    ]);
    expect(merged).toHaveLength(1);
    expect(merged[0]?.models).toEqual(["a", "b", "c"]);
    expect(merged[0]?.number).toBe("15560");
  });

  it("matches across case, accents, apostrophes and punctuation", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("00589", "Café Nights & Neon", "Sample Artist")] },
      { slug: "b", songs: [song("00589", "cafe nights and neon!", "SAMPLE ARTIST.")] },
    ]);
    expect(merged).toHaveLength(1);
    expect(merged[0]?.models).toEqual(["a", "b"]);
    expect(merged[0]?.title).toBe("Café Nights & Neon"); // the first machine's spelling is shown
  });

  it("keeps the same song with different numbers as separate rows", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("14649", "Fix You", "Coldplay")] },
      { slug: "b", songs: [song("45095", "Fix You", "Coldplay")] },
    ]);
    expect(merged.map((s) => [s.number, s.models])).toEqual([
      ["14649", ["a"]],
      ["45095", ["b"]],
    ]);
  });

  it("never merges two different songs that share a number", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("15563", "Dahilan", "Sample Artist D")] },
      { slug: "b", songs: [song("15563", "Beta Clash", "Beta Artist")] },
    ]);
    expect(merged).toHaveLength(2);
    expect(merged.map((s) => s.models)).toEqual([["a"], ["b"]]);
  });

  it("keeps leading zeros and does not treat 00589 and 589 as the same number", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("00589", "Hurting Each Other", "Carpenters")] },
      { slug: "b", songs: [song("589", "Hurting Each Other", "Carpenters")] },
    ]);
    expect(merged).toHaveLength(2);
  });

  it("merges a withheld artist only with another withheld artist for the same title and number", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("20001", "Zebra Crossing", "")] },
      { slug: "b", songs: [song("20001", "Zebra Crossing", "")] },
      { slug: "c", songs: [song("20001", "Zebra Crossing", "Known Artist")] },
    ]);
    expect(merged.map((s) => s.models)).toEqual([["a", "b"], ["c"]]);
  });

  it("leaves a single machine's songs as they are, each tagged with its machine", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("10001", "One", "X"), song("10002", "Two", "Y")] },
    ]);
    expect(merged.map((s) => [s.number, s.title, s.release, s.models])).toEqual([
      ["10001", "One", "Volume 1", ["a"]],
      ["10002", "Two", "Volume 1", ["a"]],
    ]);
  });

  it("drops the volume of a merged row (volumes differ per machine) but keeps it for a single machine", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("10001", "One", "X", "Volume 3"), song("10002", "Two", "Y", "Volume 3")] },
      { slug: "b", songs: [song("10001", "One", "X", "Volume 9")] },
    ]);
    expect(merged.find((s) => s.number === "10001")?.release).toBe("");
    expect(merged.find((s) => s.number === "10002")?.release).toBe("Volume 3");
  });

  it("assigns ids equal to positions, which the search index relies on", () => {
    const merged = mergeAcrossMachines([
      { slug: "a", songs: [song("1", "A", "x"), song("2", "B", "y")] },
      { slug: "b", songs: [song("2", "B", "y"), song("3", "C", "z")] },
    ]);
    expect(merged.map((s) => s.id)).toEqual([0, 1, 2]);
  });

  it("loses nothing: every machine's entry appears in exactly one row", () => {
    const groups = [
      { slug: "a", songs: [song("1", "A", "x"), song("2", "B", "y"), song("3", "C", "z")] },
      { slug: "b", songs: [song("2", "B", "y"), song("3", "Other", "z"), song("4", "D", "w")] },
      { slug: "c", songs: [song("1", "A", "x"), song("4", "D", "w")] },
    ];
    const merged = mergeAcrossMachines(groups);
    const entries = groups.reduce((n, g) => n + g.songs.length, 0);
    expect(merged.reduce((n, s) => n + (s.models?.length ?? 0), 0)).toBe(entries);
    for (const g of groups) {
      for (const s of g.songs) {
        expect(merged.some((m) => m.number === s.number && m.models?.includes(g.slug))).toBe(true);
      }
    }
  });

  it("lists a machine once even if it lists the same song and number twice", () => {
    const merged = mergeAcrossMachines([{ slug: "a", songs: [song("1", "A", "x"), song("1", "A", "x")] }]);
    expect(merged).toHaveLength(1);
    expect(merged[0]?.models).toEqual(["a"]);
  });
});
