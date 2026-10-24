import { PauseCircle, SearchX, TriangleAlert, WifiOff } from "lucide-react";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { CatalogNote } from "../components/CatalogNote";
import { AllSign, LineSign } from "../components/LineSign";
import { LetterStrip } from "../components/LetterStrip";
import { ModelPicker } from "../components/ModelPicker";
import { Readout } from "../components/Readout";
import { SearchField } from "../components/SearchField";
import { SongList } from "../components/SongList";
import { BootSkeleton, SongSkeleton, StatePanel } from "../components/StatePanel";
import type { UpdateState, useCatalog } from "../hooks/useCatalog";
import { RESULT_LIMIT, type SongIndex } from "../lib/search";
import { ALL_MODELS, type Manifest, type ModelInfo, type Song } from "../lib/types";

const PAGE_SIZE = 120;
const PANEL_ID = "letter-panel";

export function Home({ catalog }: { catalog: ReturnType<typeof useCatalog> }) {
  const { state, selectModel, retry, update, checkNow } = catalog;
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<Song | null>(null);

  if (state.phase === "manifest-loading") return <BootSkeleton />;
  if (state.phase === "manifest-failed") return <FailurePanel kind={state.kind} message={state.message} onRetry={retry} />;
  if (state.phase === "suspended") {
    return (
      <StatePanel
        icon={<PauseCircle size={40} />}
        title="The songbook is paused"
        action={{ label: update.phase === "checking" ? "Checking…" : "Check again", onClick: checkNow, disabled: update.phase === "checking" }}
      >
        {state.manifest.notice ?? "The songs are not available for now. Please check back later."}
        <span className="status" role="status">
          {update.phase === "done" && update.message !== "The songbook is paused." ? ` ${update.message}` : ""}
        </span>
      </StatePanel>
    );
  }

  const { manifest, slug: modelSlug } = state;
  const first = manifest.models[0];
  if (!first) return null;
  const isAll = modelSlug === ALL_MODELS && manifest.models.length > 1;
  const model: ModelInfo | null = isAll ? null : (manifest.models.find((m) => m.slug === modelSlug) ?? first);
  const readoutModel = (open && manifest.models.find((m) => m.slug === open.model)) || model || first;

  return (
    <>
      {model ? (
        <LineSign model={model} />
      ) : (
        <AllSign detail={`${manifest.models.length} machines`} />
      )}
      <ModelPicker models={manifest.models} value={isAll ? ALL_MODELS : (model?.slug ?? first.slug)} onChange={selectModel} />
      <SearchField value={query} onChange={setQuery} modelName={model ? model.name : "all machines"} />
      <div className={model ? `hue-${model.hue}` : "hue-all"}>
        {state.phase === "songs-loading" && <SongSkeleton />}
        {state.phase === "songs-failed" && <FailurePanel kind={state.kind} message={state.message} onRetry={retry} />}
        {state.phase === "ready" && (
          <Songbook
            index={state.index}
            manifest={manifest}
            model={model}
            query={query}
            onOpen={setOpen}
            update={update}
            onCheck={checkNow}
            missing={state.missing}
          />
        )}
      </div>
      <Readout song={open} model={readoutModel} onClose={() => setOpen(null)} />
    </>
  );
}

interface SongbookProps {
  index: SongIndex;
  manifest: Manifest;
  /** The machine shown, or null for the all-machines view. */
  model: ModelInfo | null;
  /** Machines that could not be loaded (all-machines view). */
  missing: readonly string[];
  query: string;
  onOpen: (song: Song) => void;
  update: UpdateState;
  onCheck: () => void;
}

function Songbook({ index, manifest, model, query, onOpen, update, onCheck, missing }: SongbookProps) {
  const deferred = useDeferredValue(query);
  const searching = deferred.trim() !== "";
  const machines = model ? undefined : manifest.models;
  return (
    <>
      {missing.length > 0 && (
        <p className="status" role="status">
          {missing.join(", ")} could not be loaded, so its songs are not shown. Check the connection and try again from
          the note below.
        </p>
      )}
      {searching ? (
        <Results index={index} model={model} query={deferred} onOpen={onOpen} machines={machines} />
      ) : (
        <Browse index={index} onOpen={onOpen} machines={machines} />
      )}
      <CatalogNote manifest={manifest} model={model} songCount={index.songs.length} update={update} onCheck={onCheck} />
    </>
  );
}

function Results({ index, model, query, onOpen, machines }: { index: SongIndex; model: ModelInfo | null; query: string; onOpen: (song: Song) => void; machines?: readonly ModelInfo[] }) {
  const result = useMemo(() => index.search(query), [index, query]);
  if (result.total === 0) {
    return (
      <StatePanel icon={<SearchX size={40} />} title="No songs found">
        Nothing in {model ? `the ${model.name} songbook` : "any machine's songbook"} matches “{query.trim()}”. Check the spelling, try fewer words, or type the
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
      <SongList songs={result.songs} onOpen={onOpen} label="Search results" models={machines} />
    </>
  );
}

function Browse({ index, onOpen, machines }: { index: SongIndex; onOpen: (song: Song) => void; machines?: readonly ModelInfo[] }) {
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
        <SongList songs={songs.slice(0, limit)} onOpen={onOpen} label={name} models={machines} />
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
