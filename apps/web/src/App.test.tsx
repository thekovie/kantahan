import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { MODEL_B_ROWS, fakeFetch, wipeStorage, makeBundle, makeManifest, modelEntry } from "./test-utils";

const modelB = makeBundle(MODEL_B_ROWS, "model-b");

function mount(path = "/") {
  const { hook } = memoryLocation({ path });
  return render(
    <Router hook={hook}>
      <App />
    </Router>,
  );
}

function stubRoutes(routes: Record<string, unknown>) {
  const impl = fakeFetch(routes);
  vi.stubGlobal("fetch", impl);
  return impl;
}

function stubNetwork(routes: Record<string, unknown> | "offline") {
  const impl =
    routes === "offline"
      ? vi.fn(async () => {
          throw new TypeError("Failed to fetch");
        })
      : fakeFetch(routes);
  vi.stubGlobal("fetch", impl);
  return impl;
}

const ROUTES = {
  "/catalog/manifest.json": makeManifest(),
  "/catalog/model-a.json": makeBundle(),
  "/catalog/model-b.json": modelB,
};

beforeEach(() => {
  document.documentElement.setAttribute("data-theme", "dark");
});
afterEach(async () => {
  vi.unstubAllGlobals();
  await wipeStorage();
});

describe("songbook", () => {
  it("opens on the first model with the songbook index and names its coverage and source", async () => {
    stubNetwork(ROUTES);
    mount();
    expect(await screen.findByRole("radio", { name: "Model A" })).toBeChecked();
    expect(await screen.findByRole("tab", { name: /^A, 1 song/ })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("Demo", { exact: true })).toBeInTheDocument();
    expect(screen.getByText(/Songs added in earlier volumes are not included/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Synthetic demo data" })).toHaveAttribute("href", "https://example.test/source");
  });

  it("walks the alphabet rail", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("tab", { name: /^D, 2 songs/ }));
    const list = screen.getByRole("list", { name: "Songs starting with D" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getByText("Dahilan")).toBeInTheDocument();
  });

  it("finds a song by title, artist and number, keeping leading zeros", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    const search = await screen.findByRole("searchbox", { name: /Search Model A songs/ });

    await user.type(search, "dahilann");
    expect(await screen.findByText("1 song found.")).toBeInTheDocument();
    expect(screen.getByText("Dahilan")).toBeInTheDocument();

    await user.clear(search);
    await user.type(search, "589");
    const results = await screen.findByRole("list", { name: "Search results" });
    expect(within(results).getAllByRole("img")[0]).toHaveAccessibleName("Song number 0 0 5 8 9");

    await user.clear(search);
    await user.type(search, "sample artist e");
    expect(await screen.findByText(/Café Nights/)).toBeInTheDocument();
  });

  it("tells the visitor when nothing matches, naming the model", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.type(await screen.findByRole("searchbox"), "qqqqqq");
    expect(await screen.findByRole("heading", { name: "No songs found" })).toBeInTheDocument();
    expect(screen.getByText(/in the Model A songbook/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear search" }));
    expect(await screen.findByRole("tablist", { name: "Songs by first letter" })).toBeInTheDocument();
  });

  it("opens a song at full size and closes it again", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.type(await screen.findByRole("searchbox"), "15563");
    await user.click(await screen.findByRole("button", { name: /Dahilan/ }));
    const dialog = await screen.findByRole("dialog", { name: "Dahilan" });
    expect(within(dialog).getByRole("img")).toHaveAccessibleName("Song number 1 5 5 6 3");
    await user.click(within(dialog).getByRole("button", { name: "Done" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("says how many song numbers were left out of a model", async () => {
    const manifest = makeManifest();
    const left = { ...manifest, models: [{ ...manifest.models[0]!, excluded: 205 }, manifest.models[1]!] };
    stubNetwork({ ...ROUTES, "/catalog/manifest.json": left });
    mount();
    expect(await screen.findByText(/205 song numbers are left out/)).toBeInTheDocument();
  });

  it("never shows another model's songs, and remembers the choice", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    const first = mount();
    await user.type(await screen.findByRole("searchbox"), "dahilan");
    await screen.findByText("Dahilan");

    await user.click(screen.getByRole("radio", { name: "Model B" }));
    await user.type(await screen.findByRole("searchbox", { name: /Search Model B songs/ }), "dahilan");
    expect(await screen.findByRole("heading", { name: "No songs found" })).toBeInTheDocument();
    expect(screen.queryByText("Dahilan")).not.toBeInTheDocument();
    expect(localStorage.getItem("kantahan.model")).toBe("model-b");

    first.unmount();
    mount();
    expect(await screen.findByRole("radio", { name: "Model B" })).toBeChecked();
  });

  it("shows songs that were saved on the device when the network is gone", async () => {
    stubNetwork(ROUTES);
    const first = mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    first.unmount();

    stubNetwork("offline");
    mount();
    expect(await screen.findByRole("tab", { name: /^A, 1 song/ })).toBeInTheDocument();
  });

  it("explains being offline with nothing saved, and recovers on retry", async () => {
    stubNetwork("offline");
    const user = userEvent.setup();
    mount();
    expect(await screen.findByRole("heading", { name: "You are offline" })).toBeInTheDocument();
    stubNetwork(ROUTES);
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("radio", { name: "Model A" })).toBeInTheDocument();
  });

  it("reports a broken catalog file instead of crashing", async () => {
    stubNetwork({ ...ROUTES, "/catalog/model-a.json": { schema: 7 } });
    mount();
    expect(await screen.findByRole("heading", { name: "The songs did not load" })).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "Model A" })).toBeInTheDocument();
  });
});

describe("shell", () => {
  it("switches and remembers the theme", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Switch to the dark theme" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem("kantahan.theme")).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to the light theme" })).toBeInTheDocument();
  });

  it("reaches the About, Privacy and Rights pages from the menu", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Menu" }));
    await user.click(within(screen.getByRole("navigation", { name: "Site" })).getByRole("link", { name: "About" }));
    expect(await screen.findByRole("heading", { name: "About Kantahan" })).toBeInTheDocument();
    expect(document.title).toBe("About · Kantahan");
    expect(within(screen.getByRole("main")).getByText(/not affiliated with, endorsed by or sponsored by Platinum Karaoke/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Menu" }));
    await user.click(within(screen.getByRole("navigation", { name: "Site" })).getByRole("link", { name: "Rights and removal" }));
    expect(await screen.findByRole("heading", { name: "Rights and removal" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /github.com\/thekovie\/kantahan\/issues/ })).toBeInTheDocument();
  });

  it("renders the privacy page and a not-found page", async () => {
    stubNetwork(ROUTES);
    mount("/privacy");
    expect(await screen.findByRole("heading", { name: "Privacy" })).toBeInTheDocument();
    mount("/nope");
    expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  });

  it("closes the menu with Escape", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await user.click(await screen.findByRole("button", { name: "Menu" }));
    expect(screen.getByRole("navigation", { name: "Site" })).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("navigation", { name: "Site" })).not.toBeInTheDocument();
  });
});

describe("catalog updates", () => {
  const changed = makeBundle([["00589", "Hurting Each Other", "Sample Artist A"], ["77777", "Fresh Arrival", "New Artist"]]);
  const v2 = makeManifest({
    version: "v2",
    models: [modelEntry("model-a", changed, "Model A", "magenta", "v2/model-a.json"), makeManifest().models[1]!],
  });
  const V2_ROUTES = { ...ROUTES, "/catalog/manifest.json": v2, "/catalog/v2/model-a.json": changed };

  it("swaps in new songs when asked, keeping the search box as it was", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    const search = await screen.findByRole("searchbox");
    await user.type(search, "arrival");
    expect(await screen.findByRole("heading", { name: "No songs found" })).toBeInTheDocument();

    stubNetwork(V2_ROUTES);
    await user.click(screen.getByRole("button", { name: "Check for updates" }));
    expect(await screen.findByText("Updated to v2.")).toBeInTheDocument();
    expect(screen.getByRole("searchbox")).toHaveValue("arrival");
    expect(await screen.findByText("Fresh Arrival")).toBeInTheDocument();
  });

  it("keeps the old songs and says so when the download is corrupt", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    stubNetwork({ ...V2_ROUTES, "/catalog/v2/model-a.json": makeBundle([["00589", "Hurting Each Other", "Sample Artist A"], ["77777", "Fresh Arrivbl", "New Artist"]]) });
    await user.click(screen.getByRole("button", { name: "Check for updates" }));
    expect(await screen.findByText(/did not match their checksum.*kept/)).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^A, 1 song/ })).toBeInTheDocument();
    expect(screen.getByText(/Catalog 2026.10.23/)).toBeInTheDocument();
  });

  it("says when there is no connection, and that saved songs still work", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    stubNetwork("offline");
    await user.click(screen.getByRole("button", { name: "Check for updates" }));
    expect(await screen.findByText(/No connection. Your saved songs still work./)).toBeInTheDocument();
  });

  it("shows a paused notice instead of songs, and brings them back when resumed", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    const paused = { ...makeManifest({ version: "v3" }), suspended: true, notice: "Paused while a request is reviewed." };
    stubNetwork({ ...ROUTES, "/catalog/manifest.json": paused });
    await user.click(screen.getByRole("button", { name: "Check for updates" }));
    expect(await screen.findByRole("heading", { name: "The songbook is paused" })).toBeInTheDocument();
    expect(screen.getByText("Paused while a request is reviewed.")).toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: /^A, 1 song/ })).not.toBeInTheDocument();

    stubNetwork({ ...ROUTES, "/catalog/manifest.json": makeManifest({ version: "v3" }) });
    await user.click(screen.getByRole("button", { name: "Check again" }));
    expect(await screen.findByRole("tab", { name: /^A, 1 song/ })).toBeInTheDocument();
  });

  it("shares one comparison between taps made while it is still running", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    const net = stubRoutes(V2_ROUTES);
    const button = screen.getByRole("button", { name: "Check for updates" });
    await Promise.all([user.click(button), user.click(button)]);
    expect(await screen.findByText("Updated to v2.")).toBeInTheDocument();
    expect(net.calls.filter((url) => url.endsWith("/catalog/manifest.json"))).toHaveLength(1);
  });

  it("does not let a slow model load overwrite a model picked afterwards", async () => {
    stubNetwork(ROUTES);
    const user = userEvent.setup();
    const first = mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    first.unmount();
    await wipeStorage(); // start with nothing saved: every bundle comes from the network
    const slow = fakeFetch(ROUTES);
    let releaseA!: () => void;
    const gate = new Promise<void>((resolve) => (releaseA = resolve));
    vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/model-a.json")) await gate;
      return slow(input, init);
    });
    mount();
    await user.click(await screen.findByRole("radio", { name: "Model B" }));
    expect(await screen.findByRole("searchbox", { name: /Search Model B songs/ })).toBeInTheDocument();
    releaseA();
    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(screen.getByRole("radio", { name: "Model B" })).toBeChecked();
    expect(screen.getByRole("searchbox", { name: /Search Model B songs/ })).toBeInTheDocument();
  });

  it("checks on open when the last check is old, and updates quietly", async () => {
    stubNetwork(ROUTES);
    const first = mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    first.unmount();
    localStorage.setItem("kantahan.lastCheck", String(Date.now() - 13 * 3600 * 1000));

    const net = stubRoutes(V2_ROUTES);
    mount();
    expect(await screen.findByText("Updated to v2.")).toBeInTheDocument();
    expect(net.calls.some((url) => url.endsWith("/catalog/manifest.json"))).toBe(true);
  });

  it("does not check on open when it checked recently", async () => {
    stubNetwork(ROUTES);
    const first = mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    first.unmount();

    const net = stubRoutes(V2_ROUTES);
    mount();
    await screen.findByRole("tab", { name: /^A, 1 song/ });
    expect(net.calls).toEqual([]);
  });
});
