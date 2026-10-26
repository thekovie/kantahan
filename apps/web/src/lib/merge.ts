import { fold } from "./fold";
import type { Song } from "./types";

export interface MachineSongs {
  slug: string;
  songs: readonly Song[];
}

/** Stands in for the artist of a row whose artist is withheld, so it can only meet another withheld row. */
const WITHHELD = "\u0000withheld";

/** Two entries are one row only when title, artist and number are all the same (after folding). */
const keyOf = (song: Song): string =>
  [fold(song.title), song.artistKnown ? fold(song.artist) : WITHHELD, song.number].join("\u0001");

/**
 * The all-machines list: every machine's songs, with entries merged into one row only when they are the
 * same song under the same number. Nothing is dropped: a merged row names every machine that has it, and the
 * same song under different numbers, or the same number for different songs, stay separate rows. The
 * published data is never merged; this is only how the list is shown.
 *
 * Machines come in manifest order, which is also the order machines are listed in a row. Display text comes
 * from the first machine that has the row. A merged row has no volume, because volumes differ per machine.
 * Ids are positions, which the search index relies on.
 */
export function mergeAcrossMachines(machines: readonly MachineSongs[]): Song[] {
  const rows: Song[] = [];
  const at = new Map<string, number>();
  for (const { slug, songs } of machines) {
    for (const song of songs) {
      const key = keyOf(song);
      const position = at.get(key);
      const row = position === undefined ? undefined : rows[position];
      if (position === undefined || row === undefined) {
        at.set(key, rows.length);
        rows.push({ ...song, id: rows.length, models: [slug] });
      } else if (!row.models?.includes(slug)) {
        rows[position] = { ...row, release: "", models: [...(row.models ?? []), slug] };
      }
    }
  }
  return rows;
}
