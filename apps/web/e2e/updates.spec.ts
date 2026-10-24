import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { type Page, expect, test } from "@playwright/test";

// The update routine is app code, so the service worker is blocked here to let the test stand in
// for the server: it answers the manifest and the new bundle itself.
test.use({ colorScheme: "dark", serviceWorkers: "block" });

const CATALOG = join(process.cwd(), "public", "catalog");
const manifest = JSON.parse(
  readFileSync(join(CATALOG, "manifest.json"), "utf8"),
);
const demoA = JSON.parse(
  readFileSync(join(CATALOG, "demo-1", "demo-a.json"), "utf8"),
);

/** Model A with one extra song, published as version "demo-2". */
function version2() {
  const bundle = {
    ...demoA,
    count: demoA.count + 1,
    n: [...demoA.n, "99999"],
    t: [...demoA.t, "Zzz Fresh Arrival"],
    a: [...demoA.a, "Update Test Band"],
    r: [...demoA.r, 1],
    u: [...demoA.u, 0],
  };
  const text = JSON.stringify(bundle);
  const models = manifest.models.map((m: { slug: string }) =>
    m.slug === "demo-a"
      ? {
          ...m,
          file: "demo-2/demo-a.json",
          sha256: createHash("sha256").update(text).digest("hex"),
          bytes: Buffer.byteLength(text),
          songs: bundle.count,
        }
      : m,
  );
  return { text, manifest: { ...manifest, version: "demo-2", models } };
}

/** Serves a published catalog. The answers can be changed later through `state`, so the same mock stays in place. */
async function serve(
  page: Page,
  next: ReturnType<typeof version2>,
  state: { bundle: string; overrides: object } = {
    bundle: next.text,
    overrides: {},
  },
) {
  await page.route("**/catalog/manifest.json", (route) =>
    route.fulfill({ json: { ...next.manifest, ...state.overrides } }),
  );
  await page.route("**/catalog/demo-2/demo-a.json", (route) =>
    route.fulfill({ body: state.bundle, contentType: "application/json" }),
  );
  return state;
}

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("radio", { name: "Model A" })).toBeChecked();
});

test("new songs appear when asked, without losing the search", async ({
  page,
}) => {
  await page.getByRole("searchbox").fill("fresh arrival");
  await expect(
    page.getByRole("heading", { name: "No songs found" }),
  ).toBeVisible();

  await serve(page, version2());
  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(page.getByText("Updated to demo-2.")).toBeVisible();
  await expect(page.getByRole("searchbox")).toHaveValue("fresh arrival");
  await expect(page.getByText("Zzz Fresh Arrival")).toBeVisible();

  // The new catalog is saved on the device: after a reload it works with every catalog request refused.
  await page.unroute("**/catalog/manifest.json");
  await page.unroute("**/catalog/demo-2/demo-a.json");
  await page.route("**/catalog/**", (route) => route.abort());
  await page.reload();
  await page.getByRole("searchbox").fill("fresh arrival");
  await expect(page.getByText("Zzz Fresh Arrival")).toBeVisible();
});

test("a corrupt download is refused and the saved songs stay", async ({
  page,
}) => {
  const next = version2();
  await serve(page, next, {
    bundle: next.text.replace("Zzz Fresh Arrival", "Zzz Tampered Song"),
    overrides: {},
  });
  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(page.getByText(/did not match their checksum/)).toBeVisible();
  await page.getByRole("searchbox").fill("tampered");
  await expect(
    page.getByRole("heading", { name: "No songs found" }),
  ).toBeVisible();
  await expect(page.getByText(/Catalog demo-1/)).toBeVisible();
});

test("a paused catalog hides the songs with its notice, and resuming brings them back", async ({
  page,
}) => {
  const state = await serve(page, version2(), {
    bundle: version2().text,
    overrides: {
      suspended: true,
      notice: "Paused while a request is reviewed.",
    },
  });
  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(
    page.getByRole("heading", { name: "The songbook is paused" }),
  ).toBeVisible();
  await expect(
    page.getByText("Paused while a request is reviewed."),
  ).toBeVisible();
  await expect(page.getByRole("tablist")).toHaveCount(0);

  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"])
    .analyze();
  expect(results.violations.map((v) => v.id)).toEqual([]);

  await page.reload(); // still paused from the saved manifest, even before the network answers
  await expect(
    page.getByRole("heading", { name: "The songbook is paused" }),
  ).toBeVisible();
  // The app checks again on open while paused; wait for that to settle before the server resumes.
  await expect(page.getByRole("button", { name: "Check again" })).toBeEnabled();

  state.overrides = {}; // the owner resumes the catalog
  await page.getByRole("button", { name: "Check again" }).click();
  await expect(
    page.getByRole("tablist", { name: "Songs by first letter" }),
  ).toBeVisible();
});
