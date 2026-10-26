import { useEffect, useRef } from "react";
import type { ModelInfo, Song } from "../lib/types";
import { AllSign, LineSign } from "./LineSign";
import { NumberToken } from "./NumberToken";

interface ReadoutProps {
  song: Song | null;
  /** The machines this number is for: one, or several when the song is shown merged in the all view. */
  models: readonly ModelInfo[];
  onClose: () => void;
}

/** A song's number at full size, to read from across the room while keying it into the remote. */
export function Readout({ song, models, onClose }: ReadoutProps) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (song && !node.open) node.showModal();
    if (!song && node.open) node.close();
  }, [song]);

  if (!song) return <dialog ref={dialog} className="readout" aria-label="Song number" hidden />;
  const only = models.length === 1 ? models[0] : undefined;
  return (
    <dialog
      ref={dialog}
      className="readout"
      aria-labelledby="readout-title"
      onClose={onClose}
      onClick={(event) => event.target === dialog.current && dialog.current?.close()}
    >
      {only ? (
        <LineSign model={only} top />
      ) : (
        <AllSign top badge={String(models.length)} name={`For ${models.length} machines`} detail="" />
      )}
      <div className="readout__body">
        <NumberToken number={song.number} large />
        <h2 id="readout-title" className="readout__title">
          {song.title}
        </h2>
        {song.artistKnown && <p className="readout__artist">{song.artist}</p>}
        {only ? (
          <p className="readout__meta">
            <span>
              {only.name} · {only.family}
            </span>
            <span>{song.release}</span>
          </p>
        ) : (
          <ul className="readout__machines" aria-label="Machines">
            {models.map((m) => (
              <li key={m.slug} className={`hue-${m.hue}`}>
                <span className="song__dot" aria-hidden="true" />
                <span>{m.name}</span>
              </li>
            ))}
          </ul>
        )}
        <button type="button" className="btn btn--block" autoFocus onClick={() => dialog.current?.close()}>
          Done
        </button>
      </div>
    </dialog>
  );
}
