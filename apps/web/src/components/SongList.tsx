import type { ModelInfo, Song } from "../lib/types";
import { NumberToken } from "./NumberToken";

interface SongListProps {
  songs: readonly Song[];
  onOpen: (song: Song) => void;
  /** Accessible name for the list. */
  label: string;
  /** When given, each row says which machine its number is for (the all-machines view). */
  models?: readonly ModelInfo[];
}

/** Song rows: title and artist on the left, the number at the end, like a page number in an index. A row opens the read-out. */
export function SongList({ songs, onOpen, label, models }: SongListProps) {
  return (
    <ul className="songs" aria-label={label}>
      {songs.map((song) => (
        <li key={song.id}>
          <button type="button" className="song" onClick={() => onOpen(song)}>
            <span>
              <span className="song__title">{song.title}</span>
              {song.artistKnown && <span className="song__artist">{song.artist}</span>}
              {models && <Machines machines={machinesOf(song, models)} />}
            </span>
            <NumberToken number={song.number} />
          </button>
        </li>
      ))}
    </ul>
  );
}

/** The machines a song's entry belongs to, in the song's own order. */
export function machinesOf(song: Song, models: readonly ModelInfo[]): ModelInfo[] {
  return (song.models ?? []).flatMap((slug) => models.find((m) => m.slug === slug) ?? []);
}

const MAX_NAMED = 2;
const MAX_DOTS = 3;

/**
 * Which machines a number is for, under the artist: a few line-colour dots and the first two names, then how
 * many more. The visible text is short; screen readers get the full list. Colour is never the only cue.
 */
function Machines({ machines }: { machines: readonly ModelInfo[] }) {
  if (machines.length === 0) return null;
  const named = machines.slice(0, MAX_NAMED).map((m) => m.name);
  const rest = machines.length - named.length;
  const text = rest > 0 ? `${named.join(", ")} and ${rest} more` : named.join(", ");
  return (
    <span className="song__machines">
      <span className="song__dots" aria-hidden="true">
        {machines.slice(0, MAX_DOTS).map((m) => (
          <span key={m.slug} className={`song__dot hue-${m.hue}`} />
        ))}
      </span>
      <span aria-hidden="true">{text}</span>
      <span className="sr-only">For {machines.map((m) => m.name).join(", ")}</span>
    </span>
  );
}
