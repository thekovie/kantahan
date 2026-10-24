import { useEffect, useRef } from "react";
import type { ModelInfo, Song } from "../lib/types";
import { LineSign } from "./LineSign";
import { NumberToken } from "./NumberToken";

interface ReadoutProps {
  song: Song | null;
  model: ModelInfo;
  onClose: () => void;
}

/** A song's number at full size, to read from across the room while keying it into the remote. */
export function Readout({ song, model, onClose }: ReadoutProps) {
  const dialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    if (song && !node.open) node.showModal();
    if (!song && node.open) node.close();
  }, [song]);

  if (!song) return <dialog ref={dialog} className="readout" aria-label="Song number" hidden />;
  return (
    <dialog
      ref={dialog}
      className="readout"
      aria-labelledby="readout-title"
      onClose={onClose}
      onClick={(event) => event.target === dialog.current && dialog.current?.close()}
    >
      <LineSign model={model} top />
      <div className="readout__body">
        <NumberToken number={song.number} large />
        <h2 id="readout-title" className="readout__title">
          {song.title}
        </h2>
        {song.artistKnown && <p className="readout__artist">{song.artist}</p>}
        <p className="readout__meta">
          <span>
            {model.name} · {model.family}
          </span>
          <span>{song.release}</span>
        </p>
        <button type="button" className="btn btn--block" autoFocus onClick={() => dialog.current?.close()}>
          Done
        </button>
      </div>
    </dialog>
  );
}
