import { afterEach, describe, expect, it, vi } from "vitest";
import { readModel, readTheme, resolveTheme, writeModel, writeTheme } from "./prefs";

afterEach(() => vi.unstubAllGlobals());

const blockStorage = () =>
  vi.stubGlobal("localStorage", {
    getItem: () => {
      throw new Error("blocked");
    },
    setItem: () => {
      throw new Error("blocked");
    },
  });

describe("prefs", () => {
  it("remembers the model and the theme", () => {
    writeModel("model-b");
    writeTheme("light");
    expect(readModel()).toBe("model-b");
    expect(readTheme()).toBe("light");
  });

  it("falls back to the system theme for anything unexpected", () => {
    localStorage.setItem("kantahan.theme", "purple");
    expect(readTheme()).toBe("system");
  });

  it("does not throw when storage is blocked", () => {
    blockStorage();
    expect(() => writeModel("x")).not.toThrow();
    expect(() => writeTheme("dark")).not.toThrow();
    expect(readModel()).toBeNull();
    expect(readTheme()).toBe("system");
  });
});

describe("resolveTheme", () => {
  it("honours an explicit choice", () => {
    expect(resolveTheme("light")).toBe("light");
    expect(resolveTheme("dark")).toBe("dark");
  });

  it("follows the system setting and defaults to dark", () => {
    vi.stubGlobal("matchMedia", () => ({ matches: true }));
    expect(resolveTheme("system")).toBe("light");
    vi.stubGlobal("matchMedia", () => ({ matches: false }));
    expect(resolveTheme("system")).toBe("dark");
    vi.stubGlobal("matchMedia", undefined);
    expect(resolveTheme("system")).toBe("dark");
  });
});
