export type ThemePref = "system" | "dark" | "light";

const MODEL_KEY = "kantahan.model";
const THEME_KEY = "kantahan.theme";

function read(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // storage blocked or unavailable
  }
}

function write(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
  } catch {
    // The choice just is not remembered.
  }
}

export const readModel = (): string | null => read(MODEL_KEY);
export const writeModel = (slug: string): void => write(MODEL_KEY, slug);

export function readTheme(): ThemePref {
  const value = read(THEME_KEY);
  return value === "dark" || value === "light" ? value : "system";
}

export const writeTheme = (theme: ThemePref): void => write(THEME_KEY, theme);

/** The theme to paint: an explicit choice wins, otherwise the system setting, dark when unknown. */
export function resolveTheme(pref: ThemePref): "dark" | "light" {
  if (pref !== "system") return pref;
  try {
    return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
  } catch {
    return "dark";
  }
}
