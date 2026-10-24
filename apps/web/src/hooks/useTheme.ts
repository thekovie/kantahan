import { useCallback, useEffect, useState } from "react";
import { type ThemePref, readTheme, resolveTheme, writeTheme } from "../lib/prefs";

/** Applies the theme to <html> and keeps it in step with the system when no choice was made. */
export function useTheme() {
  const [pref, setPref] = useState<ThemePref>(readTheme);
  const [theme, setTheme] = useState<"dark" | "light">(() => resolveTheme(readTheme()));

  useEffect(() => {
    const apply = () => {
      const next = resolveTheme(pref);
      setTheme(next);
      document.documentElement.setAttribute("data-theme", next);
    };
    apply();
    if (pref !== "system") return;
    const query = window.matchMedia?.("(prefers-color-scheme: dark)");
    query?.addEventListener("change", apply);
    return () => query?.removeEventListener("change", apply);
  }, [pref]);

  const toggle = useCallback(() => {
    const next = theme === "dark" ? "light" : "dark";
    writeTheme(next);
    setPref(next);
  }, [theme]);

  return { theme, toggle };
}
