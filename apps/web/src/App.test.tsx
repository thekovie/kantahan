import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Router } from "wouter";
import { memoryLocation } from "wouter/memory-location";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { resetStorage } from "./lib/storage";
import { fakeFetch, makeBundle, makeManifest } from "./test-utils";

const modelB = makeBundle([
  ["20001", "Beta Song One", "Beta Artist"],
  ["20002", "Beta Song Two", "Beta Artist"],
]);

function mount(path = "/") {
  const { hook } = memoryLocation({ path });
  return render(
    <Router hook={hook}>
      <App />
    </Router>,
  );
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
afterEach(() => {
  vi.unstubAllGlobals();
  resetStorage();
  indexedDB.deleteDatabase("kantahan");
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
    await user.click(await screen.findByRole("button", { name: "Switch to the light theme" }));
    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(localStorage.getItem("kantahan.theme")).toBe("light");
    expect(screen.getByRole("button", { name: "Switch to the dark theme" })).toBeInTheDocument();
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

  it("renders the privacy page and a not-found page", () => {
    stubNetwork(ROUTES);
    mount("/privacy");
    expect(screen.getByRole("heading", { name: "Privacy" })).toBeInTheDocument();
    mount("/nope");
    expect(screen.getByRole("heading", { name: "Page not found" })).toBeInTheDocument();
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
