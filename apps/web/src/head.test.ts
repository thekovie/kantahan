import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

// Link previews (Facebook, Messenger, Telegram, X) read the page as served, without running scripts, so the
// tags have to be in the static index.html with absolute addresses.
const html = new DOMParser().parseFromString(readFileSync("index.html", "utf8"), "text/html");
const meta = (key: string) =>
  html.querySelector(`meta[property="${key}"], meta[name="${key}"]`)?.getAttribute("content") ?? "";

describe("link preview tags", () => {
  it("describes the page for Open Graph", () => {
    expect(meta("og:type")).toBe("website");
    expect(meta("og:site_name")).toBe("Kantahan");
    expect(meta("og:title")).toMatch(/Kantahan/);
    expect(meta("og:description").length).toBeGreaterThan(40);
    expect(meta("og:url")).toBe("https://kantahan.thekovie.com/");
    expect(html.querySelector('link[rel="canonical"]')?.getAttribute("href")).toBe("https://kantahan.thekovie.com/");
  });

  it("points to an absolute share image of the size Facebook recommends", () => {
    expect(meta("og:image")).toBe("https://kantahan.thekovie.com/brand/og.png");
    expect(meta("og:image:width")).toBe("1200");
    expect(meta("og:image:height")).toBe("630");
    expect(meta("og:image:alt").length).toBeGreaterThan(10);
  });

  it("asks for the large image card elsewhere", () => {
    expect(meta("twitter:card")).toBe("summary_large_image");
    expect(meta("twitter:image")).toBe(meta("og:image"));
  });

  it("does not claim a connection to Platinum Karaoke", () => {
    expect(`${meta("og:title")} ${meta("og:description")}`).not.toMatch(/official|endorsed|by platinum/i);
  });
});
