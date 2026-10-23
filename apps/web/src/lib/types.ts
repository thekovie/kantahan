/** Colour family a model's number tokens are drawn in (see index.css, `--hue-*`). */
export type HueKey = "magenta" | "violet" | "aqua" | "orange" | "lime" | "yellow";

/** Columnar catalog bundle written by `kantahan-catalog build` (schema 1). */
export interface BundleV1 {
  schema: 1;
  model: string;
  count: number;
  /** Volume labels, indexed by `r`. */
  releases: string[];
  /** Song numbers as text: leading zeros are part of the number. */
  n: string[];
  t: string[];
  /** Empty when the artist is withheld. */
  a: string[];
  r: number[];
  /** 1 when the artist is withheld because the source text was ambiguous. */
  u: number[];
}

export interface Song {
  id: number;
  number: string;
  title: string;
  artist: string;
  release: string;
  /** False when the source could not give a reliable artist. */
  artistKnown: boolean;
}

export interface ModelInfo {
  slug: string;
  name: string;
  /** Machine family, shown next to the name so colour is never the only cue. */
  family: string;
  hue: HueKey;
  /** Bundle file name, relative to the catalog base URL. */
  file: string;
  songs: number;
  /** Plain-language coverage, for example "Volumes 62 to 76". */
  coverage: string;
}

export interface SourceCredit {
  label: string;
  url: string;
}

export interface Manifest {
  schema: 1;
  version: string;
  generatedAt: string;
  /** True for the demo catalog shipped with the app: not real song data. */
  synthetic: boolean;
  source: SourceCredit;
  models: ModelInfo[];
}
