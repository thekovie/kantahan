import type { Song } from "../lib/types";
import { NumberToken } from "./NumberToken";

interface SongListProps {
  songs: readonly Song[];
  onOpen: (song: Song) => void;
  /** Accessible name for the list. */
  label: string;
}

/** Song rows: title and artist on the left, the number at the end, like a page number in an index. A row opens the read-out. */
export function SongList({ songs, onOpen, label }: SongListProps) {
  return (
    <ul className="songs" aria-label={label}>
      {songs.map((song) => (
        <li key={song.id}>
          <button type="button" className="song" onClick={() => onOpen(song)}>
            <span>
              <span className="song__title">{song.title}</span>
              {song.artistKnown && <span className="song__artist">{song.artist}</span>}
            </span>
            <NumberToken number={song.number} />
          </button>
        </li>
      ))}
    </ul>
  );
}
