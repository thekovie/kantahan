/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Where catalog files are served from; defaults to /catalog. */
  readonly VITE_CATALOG_BASE?: string;
}
