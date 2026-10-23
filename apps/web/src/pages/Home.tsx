import { SearchX, TriangleAlert, WifiOff } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { CatalogNote } from "../components/CatalogNote";
import { LetterStrip } from "../components/LetterStrip";
import { ModelPicker } from "../components/ModelPicker";
import { Readout } from "../components/Readout";
import { SearchField } from "../components/SearchField";
import { SongList } from "../components/SongList";
import { BootSkeleton, SongSkeleton, StatePanel } from "../components/StatePanel";
import type { useCatalog } from "../hooks/useCatalog";
import { RESULT_LIMIT, type SongIndex } from "../lib/search";
import type { Manifest, ModelInfo, Song } from "../lib/types";

const PAGE_SIZE = 120;
const PANEL_ID = "letter-panel";

export function Home({ catalog }: { catalog: ReturnType<typeof useCatalog> }) {
  const { state, selectModel, retry } = catalog;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Song | null>(null);

  if (state.phase === "manifest-loading") return <BootSkeleton />;
  if (state.phase === "manifest-failed") return <FailurePanel kind={state.kind} message={state.message} onRetry={retry} />;

  const { manifest, slug: modelSlug } = state;
  const model = manifest.models.find((m) => m.slug === modelSlug) ?? manifest.models[0];
  if (!model) return null;

  return (
    <>
      <ModelPicker models={manifest.models} value={modelSlug} onChange={selectModel} />
      <SearchField value={query} onChange={setQuery} modelName={model.name} />
      <div className={`hue-${model.hue}`}>
        {state.phase === "songs-loading" && <SongSkeleton />}
        {state.phase === "songs-failed" && <FailurePanel kind={state.kind} message={state.message} onRetry={retry} />}
        {state.phase === "ready" && (
          <Songbook
            index={state.index}
            manifest={manifest}
            model={model}
            query={query}
            onOpen={setOpen}
          />
        )}
      </div>
      <Readout song={open} model={model} onClose={() => setOpen(null)} />
    </>
  );
}

interface SongbookProps {
  index: SongIndex;
  manifest: Manifest;
  model: ModelInfo;
  query: string;
  onOpen: (song: Song) => void;
}

function Songbook({ index, manifest, model, query, onOpen }: SongbookProps) {
  const deferred = useDeferredValue(query);
  const searching = deferred.trim() !== "";
  return (
    <>
      {searching ? (
        <Results index={index} model={model} query={deferred} onOpen={onOpen} />
      ) : (
        <Browse index={index} onOpen={onOpen} />
      )}
      <CatalogNote manifest={manifest} model={model} songCount={index.songs.length} />
    </>
  );
}

function Results({ index, model, query, onOpen }: { index: SongIndex; model: ModelInfo; query: string; onOpen: (song: Song) => void }) {
  const result = useMemo(() => index.search(query), [index, query]);
  if (result.total === 0) {
    return (
      <StatePanel icon={<SearchX size={40} />} title="No songs found">
        Nothing in the {model.name} songbook matches “{query.trim()}”. Check the spelling, try fewer words, or type the
        song number.
      </StatePanel>
    );
  }
  const shown = result.songs.length;
  return (
    <>
      <p className="status" role="status">
        {result.total.toLocaleString("en-PH")} {result.total === 1 ? "song" : "songs"} found
        {result.total > shown ? `, showing the first ${RESULT_LIMIT}. Type more to narrow it down.` : "."}
      </p>
      <SongList songs={result.songs} onOpen={onOpen} label="Search results" />
    </>
  );
}

function Browse({ index, onOpen }: { index: SongIndex; onOpen: (song: Song) => void }) {
  const letters = useMemo(() => index.letters(), [index]);
  const first = letters[0]?.letter ?? "A";
  const [letter, setLetter] = useState(first);
  const [limit, setLimit] = useState(PAGE_SIZE);

  useEffect(() => {
    setLetter((current) => (letters.some((l) => l.letter === current) ? current : first));
  }, [letters, first]);
  useEffect(() => setLimit(PAGE_SIZE), [letter, index]);

  const songs = index.songsForLetter(letter);
  const name = letter === "#" ? "Numbers and symbols" : `Songs starting with ${letter}`;
  return (
    <>
      <LetterStrip letters={letters} active={letter} onChange={setLetter} panelId={PANEL_ID} />
      <section id={PANEL_ID} role="tabpanel" aria-labelledby={`letter-${letter === "#" ? "num" : letter}`}>
        <div className="index-head">
          <h2>{name}</h2>
          <span className="status">{songs.length.toLocaleString("en-PH")} songs</span>
        </div>
        <SongList songs={songs.slice(0, limit)} onOpen={onOpen} label={name} />
        {songs.length > limit && (
          <button type="button" className="more" onClick={() => setLimit((n) => n + PAGE_SIZE)}>
            Show more ({(songs.length - limit).toLocaleString("en-PH")} left)
          </button>
        )}
      </section>
    </>
  );
}

function FailurePanel({ kind, message, onRetry }: { kind: "offline" | "network" | "invalid"; message: string; onRetry: () => void }) {
  if (kind === "offline") {
    return (
      <StatePanel icon={<WifiOff size={40} />} title="You are offline" action={{ label: "Try again", onClick: onRetry }}>
        {message} Connect once and the songs will be saved on this phone for next time.
      </StatePanel>
    );
  }
  return (
    <StatePanel icon={<TriangleAlert size={40} />} title="The songs did not load" action={{ label: "Try again", onClick: onRetry }}>
      {message}
    </StatePanel>
  );
}
