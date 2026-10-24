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
            </span>
            <span className="song__num">
              <NumberToken number={song.number} />
              {models && <MachineTag model={models.find((m) => m.slug === song.model)} />}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/** The machine a number belongs to, always written out and marked with its line colour. */
function MachineTag({ model }: { model: ModelInfo | undefined }) {
  if (!model) return null;
  return (
    <span className={`song__model hue-${model.hue}`}>
      <span className="song__dot" aria-hidden="true" />
      {model.name}
    </span>
  );
}
