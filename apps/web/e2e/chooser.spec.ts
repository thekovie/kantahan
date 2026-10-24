import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";

// A first visit: nothing saved, so no machine has been chosen and the app opens on All machines.
test.use({ serviceWorkers: "block", storageState: { cookies: [], origins: [] } });

test("a first visit opens on All machines", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("radio", { name: "All machines" })).toBeChecked();
  await expect(page.locator(".line__name")).toHaveText("All machines");
  await page.getByRole("searchbox").fill("neon");
  await expect(page.getByRole("list", { name: "Search results" }).getByRole("button").first()).toContainText("Model");
});

test("with many machines the chooser is a dropdown, opens on All and its arrow has room", async ({ page }) => {
  // Seven machines made from the demo catalog, so the chooser turns into a dropdown.
  const base = await (await page.request.get("/catalog/manifest.json")).json();
  const first = base.models[0];
  const bundle = await (await page.request.get(`/catalog/${first.file}`)).json();
  const files = new Map<string, string>();
  const models = Array.from({ length: 7 }, (_, i) => {
    const slug = `many-${i + 1}`;
    const text = JSON.stringify({ ...bundle, model: slug });
    files.set(`/catalog/${slug}.json`, text);
    return {
      ...first,
      slug,
      name: `Machine ${i + 1}`,
      file: `${slug}.json`,
      sha256: createHash("sha256").update(text).digest("hex"),
      bytes: Buffer.byteLength(text),
    };
  });
  await page.route("**/catalog/manifest.json", (route) => route.fulfill({ json: { ...base, models } }));
  await page.route("**/catalog/many-*.json", (route) =>
    route.fulfill({ body: files.get(new URL(route.request().url()).pathname) ?? "", contentType: "application/json" }),
  );

  await page.goto("/");
  const select = page.getByRole("combobox", { name: "Machine model" });
  await expect(select).toHaveValue("all");

  if (process.env.SCREENSHOTS) await page.screenshot({ path: `../../.impeccable/review/dropdown-${test.info().project.name}.png` });
  const box = await select.boundingBox();
  const icon = await page.locator(".select__icon").boundingBox();
  if (!box || !icon) throw new Error("the dropdown or its arrow is not on the page");
  // The arrow keeps at least 12px between itself and the edge of the field, and stays inside it.
  expect(box.x + box.width - (icon.x + icon.width)).toBeGreaterThanOrEqual(12);
  expect(icon.x).toBeGreaterThan(box.x);
});
