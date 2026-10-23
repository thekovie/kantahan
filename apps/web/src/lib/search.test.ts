import { describe, expect, it } from "vitest";
import { makeSongs } from "../test-utils";
import { fold } from "./fold";
import { RESULT_LIMIT, SongIndex, letterOf } from "./search";

const index = new SongIndex(makeSongs());
const numbers = (query: string) => index.search(query).songs.map((s) => s.number);

describe("fold", () => {
  it("ignores case, accents, apostrophes and punctuation", () => {
    expect(fold("Café NIGHTS & Neon")).toBe("cafe nights and neon");
    expect(fold("Ako'y Para Sa’yo")).toBe("akoy para sayo");
    expect(fold("24/7, 365")).toBe("24 7 365");
  });
});

describe("number search", () => {
  it("finds the exact number first and keeps it a string", () => {
    expect(numbers("15563")[0]).toBe("15563");
    expect(index.search("15563").kind).toBe("number");
  });

  it("matches a number typed without its leading zeros", () => {
    expect(numbers("589")[0]).toBe("00589");
    expect(numbers("3150")).toEqual(["03150"]);
  });

  it("treats a prefix as a partial number, nearest first", () => {
    expect(numbers("1556")).toEqual(["15562", "15563", "15564"]);
  });

  it("ignores spaces typed inside a number", () => {
    expect(numbers("155 62")).toEqual(["15562"]);
  });

  it("finds digits inside a number only from three digits up", () => {
    expect(numbers("42")).toContain("42236");
    expect(numbers("236")).toEqual(["42236"]);
    expect(numbers("23")).toEqual([]);
  });

  it("reports no match for a number that does not exist", () => {
    expect(index.search("99999")).toMatchObject({ songs: [], total: 0 });
  });
});

describe("text search", () => {
  it("finds a title by a partial word, ignoring case", () => {
    expect(numbers("DAHI")[0]).toBe("15563");
  });

  it("ranks a word that starts like the query above one that is only close", () => {
    expect(numbers("dahi")).toEqual(["15563", "15564"]);
  });

  it("finds an artist", () => {
    expect(numbers("artist d").sort()).toEqual(["15563", "15564"]);
  });

  it("requires every word typed to match", () => {
    expect(numbers("hurting artist b")).toEqual(["03150"]);
    expect(numbers("hurting zebra")).toEqual([]);
  });

  it("matches without apostrophes or accents", () => {
    expect(numbers("akoy para")).toEqual(["15562"]);
    expect(numbers("cafe neon")).toEqual(["15589"]);
  });

  it("tolerates a small typo in longer words only", () => {
    expect(numbers("dahilann")).toEqual(["15563"]);
    expect(numbers("hurtin eech")).toEqual(["00589", "03150"]);
    expect(numbers("datx")).toEqual(["15564"]);
    expect(numbers("dxt")).toEqual([]); // three letters: no typo tolerance
  });

  it("keeps different numbers for the same title and artist-less songs findable", () => {
    expect(numbers("hurting each other")).toEqual(["00589", "03150"]);
    expect(numbers("zebra")).toEqual(["15600"]);
  });

  it("returns nothing for an empty or symbol-only query", () => {
    expect(index.search("   ").songs).toEqual([]);
    expect(index.search("!!!").songs).toEqual([]);
  });

  it("caps the list but reports the full count", () => {
    const rows = Array.from({ length: 150 }, (_, i) => [String(10000 + i), `Same Title ${i}`, "Artist"] as const);
    const big = new SongIndex(makeSongs(rows));
    const result = big.search("same title");
    expect(result.songs).toHaveLength(RESULT_LIMIT);
    expect(result.total).toBe(150);
  });
});

describe("songbook index", () => {
  it("groups by first letter with digits under #", () => {
    expect(index.letters()).toEqual([
      { letter: "A", count: 1 },
      { letter: "C", count: 1 },
      { letter: "D", count: 2 },
      { letter: "H", count: 2 },
      { letter: "Z", count: 1 },
      { letter: "#", count: 1 },
    ]);
  });

  it("lists a letter alphabetically and tells an unknown letter apart", () => {
    expect(index.songsForLetter("D").map((s) => s.title)).toEqual(["Dahilan", "Dati"]);
    expect(index.songsForLetter("Q")).toEqual([]);
  });

  it("files accented and symbol titles sensibly", () => {
    expect(letterOf("Éxito")).toBe("E");
    expect(letterOf("24/7")).toBe("#");
    expect(letterOf("")).toBe("#");
  });
});
