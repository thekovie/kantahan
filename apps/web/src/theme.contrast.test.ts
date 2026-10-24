import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";

/** Reads the real CSS custom properties, so the palette cannot drift from what is checked here. */
const css = readFileSync(join(process.cwd(), "src", "index.css"), "utf8");

function block(selector: string): Record<string, string> {
  const start = css.indexOf(`${selector} {`);
  const end = css.indexOf("}", start);
  const vars: Record<string, string> = {};
  for (const match of css.slice(start, end).matchAll(/--([\w-]+):\s*(#[0-9a-f]{6})\s*;/gi)) {
    vars[match[1] as string] = match[2] as string;
  }
  return vars;
}

const dark = block(":root");
const light = { ...dark, ...block(':root[data-theme="light"]') };

function luminance(hex: string): number {
  const channel = (offset: number) => {
    const value = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(1) + 0.7152 * channel(3) + 0.0722 * channel(5);
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

const themes = { dark, light } as const;
const HUES = ["magenta", "violet", "aqua", "orange", "lime", "yellow"] as const;

describe.each(Object.entries(themes))("%s theme contrast (WCAG AA)", (_name, t) => {
  const v = (key: string): string => {
    const value = t[key];
    if (!value) throw new Error(`token --${key} is missing`);
    return value;
  };

  it.each([
    ["text", "bg"],
    ["text", "surface"],
    ["text", "surface-2"],
    ["text-muted", "bg"],
    ["text-muted", "surface"],
    ["text-muted", "surface-2"],
    ["on-brand", "brand"],
    ["on-select", "select"],
    ["error", "bg"],
    ["error", "surface"],
    ["error", "surface-2"],
  ])("body text %s on %s is at least 4.5:1", (fg, bg) => {
    expect(ratio(v(fg), v(bg))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(HUES)("lit %s digits on the LED tile are at least 4.5:1", (hue) => {
    expect(ratio(v(`led-${hue}`), v("tile"))).toBeGreaterThanOrEqual(4.5);
  });

  it.each(HUES)("selected %s chip text is at least 4.5:1", (hue) => {
    expect(ratio(v("chip-ink"), v(`led-${hue}`))).toBeGreaterThanOrEqual(4.5);
  });

  it.each([
    ["line-strong", "bg"],
    ["line-strong", "surface"],
    ["focus", "bg"],
    ["focus", "surface"],
    ["error", "bg"],
    ["error", "surface"],
  ])("interface part %s on %s is at least 3:1", (fg, bg) => {
    expect(ratio(v(fg), v(bg))).toBeGreaterThanOrEqual(3);
  });
});
