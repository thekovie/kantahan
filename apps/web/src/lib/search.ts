import MiniSearch from "minisearch";
import { fold } from "./fold";
import type { Song } from "./types";

export const RESULT_LIMIT = 80;
const MIN_FUZZY_LENGTH = 4;
const FUZZY_FRACTION = 0.2;
const MIN_CONTAINS_DIGITS = 3;

export type SearchKind = "number" | "text";

export interface SearchResult {
  kind: SearchKind;
  /** Songs to show, best first, at most `limit`. */
  songs: Song[];
  /** Matches before the limit was applied. */
  total: number;
}

export interface LetterCount {
  letter: string;
  count: number;
}

interface IndexedDoc {
  id: number;
  title: string;
  artist: string;
}

const digitsOnly = (query: string): string | null => {
  const compact = query.replace(/\s+/g, "");
  return /^\d+$/.test(compact) ? compact : null;
};

const stripZeros = (digits: string): string => digits.replace(/^0+(?=\d)/, "");

/** First letter of the title in the songbook index; digits and symbols go under "#". */
export function letterOf(title: string): string {
  const first = fold(title).charAt(0).toUpperCase();
  return /^[A-Z]$/.test(first) ? first : "#";
}

/**
 * In-memory search over one model's songs. Numbers are text: "589" finds "00589", and the
 * exact number always comes first. Text search folds case, accents and apostrophes and
 * tolerates small typos; every word typed must match the title or the artist.
 */
export class SongIndex {
  readonly songs: readonly Song[];
  private readonly mini: MiniSearch<IndexedDoc>;
  private readonly sortedByTitle: Song[];
  private readonly letterMap = new Map<string, Song[]>();
  private readonly titleRank = new Map<number, number>();

  constructor(songs: readonly Song[]) {
    this.songs = songs;
    this.mini = new MiniSearch<IndexedDoc>({
      fields: ["title", "artist"],
      storeFields: [],
      idField: "id",
      searchOptions: {
        prefix: true,
        combineWith: "AND",
        boost: { title: 2 },
        // A word that starts like the typed one beats a word that is merely close to it.
        weights: { prefix: 1, fuzzy: 0.3 },
        fuzzy: (term) => (term.length >= MIN_FUZZY_LENGTH ? FUZZY_FRACTION : false),
      },
    });
    // Fold each title once: with every machine in one index (tens of thousands of songs) folding inside the
    // sort comparison would run it hundreds of thousands of times.
    const folded = new Map<number, string>(songs.map((s) => [s.id, fold(s.title)]));
    this.mini.addAll(songs.map((s) => ({ id: s.id, title: folded.get(s.id) ?? "", artist: fold(s.artist) })));

    this.sortedByTitle = [...songs].sort(
      (a, b) => (folded.get(a.id) ?? "").localeCompare(folded.get(b.id) ?? "") || a.number.localeCompare(b.number),
    );
    this.sortedByTitle.forEach((song, rank) => this.titleRank.set(song.id, rank));
    for (const song of this.sortedByTitle) {
      const letter = letterOf(song.title);
      const bucket = this.letterMap.get(letter);
      if (bucket) bucket.push(song);
      else this.letterMap.set(letter, [song]);
    }
  }

  search(query: string, limit: number = RESULT_LIMIT): SearchResult {
    const trimmed = query.trim();
    if (trimmed === "") return { kind: "text", songs: [], total: 0 };
    const digits = digitsOnly(trimmed);
    return digits === null ? this.searchText(trimmed, limit) : this.searchNumber(digits, limit);
  }

  letters(): LetterCount[] {
    const order = [...this.letterMap.keys()].sort((a, b) => (a === "#" ? 1 : b === "#" ? -1 : a.localeCompare(b)));
    return order.map((letter) => ({ letter, count: this.letterMap.get(letter)?.length ?? 0 }));
  }

  songsForLetter(letter: string): readonly Song[] {
    return this.letterMap.get(letter) ?? [];
  }

  private searchNumber(digits: string, limit: number): SearchResult {
    const key = stripZeros(digits);
    const ranked: { song: Song; rank: number }[] = [];
    for (const song of this.songs) {
      const songKey = stripZeros(song.number);
      let rank = -1;
      if (song.number === digits) rank = 0;
      else if (songKey === key) rank = 1;
      else if (song.number.startsWith(digits)) rank = 2;
      else if (songKey.startsWith(key)) rank = 3;
      else if (digits.length >= MIN_CONTAINS_DIGITS && song.number.includes(digits)) rank = 4;
      if (rank >= 0) ranked.push({ song, rank });
    }
    ranked.sort((a, b) => a.rank - b.rank || a.song.number.localeCompare(b.song.number));
    return { kind: "number", songs: ranked.slice(0, limit).map((r) => r.song), total: ranked.length };
  }

  private searchText(query: string, limit: number): SearchResult {
    const folded = fold(query);
    if (folded === "") return { kind: "text", songs: [], total: 0 };
    const hits = this.mini.search(folded);
    // Equal scores fall back to alphabetical order so results never shuffle between keystrokes.
    hits.sort((a, b) => b.score - a.score || (this.titleRank.get(a.id as number) ?? 0) - (this.titleRank.get(b.id as number) ?? 0));
    const songs: Song[] = [];
    for (const hit of hits.slice(0, limit)) {
      const song = this.songs[hit.id as number];
      if (song) songs.push(song);
    }
    return { kind: "text", songs, total: hits.length };
  }
}
