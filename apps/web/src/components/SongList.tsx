import type { Song } from "../lib/types";
import { NumberToken } from "./NumberToken";

interface SongListProps {
  songs: readonly Song[];
  onOpen: (song: Song) => void;
  /** Accessible name for the list. */
  label: string;
}

/** Song rows: the number token leads, title and artist follow. A row opens the read-out. */
export function SongList({ songs, onOpen, label }: SongListProps) {
  return (
    <ul className="songs" aria-label={label}>
      {songs.map((song) => (
        <li key={song.id}>
          <button type="button" className="song" onClick={() => onOpen(song)}>
            <NumberToken number={song.number} />
            <span>
              <span className="song__title">{song.title}</span>
              {song.artistKnown && <span className="song__artist">{song.artist}</span>}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}
