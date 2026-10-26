import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test.use({ colorScheme: "dark" });

test.beforeEach(async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("radio", { name: "Model A" })).toBeChecked();
});

test("opens in the dark theme on a dark system and shows the demo flag", async ({ page }) => {
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(page.getByText("Demo", { exact: true })).toBeVisible();
  await expect(page).toHaveTitle("Kantahan");
});

test("walks the songbook index by letter", async ({ page }) => {
  const tab = page.getByRole("tab", { name: /^N, \d+ songs?/ });
  await tab.click();
  await expect(tab).toHaveAttribute("aria-selected", "true");
  const list = page.getByRole("list", { name: "Songs starting with N" });
  await expect(list.getByRole("listitem").first()).toContainText("Neon");
});

test("finds songs by title and by number, keeping leading zeros", async ({ page }) => {
  const search = page.getByRole("searchbox");
  await search.fill("velvet harbor");
  await expect(page.getByRole("status").filter({ hasText: /\d+ songs? found/ })).toBeVisible();

  await page.getByRole("radio", { name: "Model C" }).click();
  await expect(page.getByRole("radio", { name: "Model C" })).toBeChecked();
  await search.fill("590");
  const first = page.getByRole("list", { name: "Search results" }).getByRole("img").first();
  await expect(first).toHaveAccessibleName("Song number 0 0 5 9 0");
});

test("opens a song at full size, then closes it with Escape", async ({ page }) => {
  await page.getByRole("searchbox").fill("neon");
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("img")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
});

test("does not scroll sideways at any width", async ({ page }) => {
  for (const width of [320, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 800 });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow, `horizontal overflow at ${width}px`).toBeLessThanOrEqual(0);
  }
});

test("remembers the theme and the model across a reload", async ({ page }) => {
  await page.getByRole("button", { name: "Switch to the light theme" }).click();
  await page.getByRole("radio", { name: "Model B" }).click();
  await expect(page.getByRole("radio", { name: "Model B" })).toBeChecked();
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  await expect(page.getByRole("radio", { name: "Model B" })).toBeChecked();
});

test("can be used with the keyboard only", async ({ page }) => {
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: "Skip to content" })).toBeFocused();
  await page.getByRole("searchbox").focus();
  await page.keyboard.type("harbor");
  await expect(page.getByRole("status").filter({ hasText: "found" })).toBeVisible();
  await page.keyboard.press("Tab"); // clear button
  await page.keyboard.press("Tab"); // first result
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("the read-out shows the number at a monumental size", async ({ page }) => {
  await page.getByRole("searchbox").fill("neon");
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const size = await dialog.locator(".num--large").evaluate((el) => Number.parseFloat(getComputedStyle(el).fontSize));
  const viewport = page.viewportSize()?.width ?? 0;
  // Phones fill the dialog (about 55px digits); a desktop dialog is wider and must go much larger.
  expect(size).toBeGreaterThanOrEqual(viewport >= 900 ? 100 : 48);
  const box = await dialog.locator(".num--large").boundingBox();
  const dialogBox = await dialog.boundingBox();
  expect(box && dialogBox && box.x + box.width <= dialogBox.x + dialogBox.width).toBe(true);
});

test("the all-machines view labels every row with its machine, and keeps the choice", async ({ page }) => {
  await page.getByRole("radio", { name: "All machines" }).click();
  await expect(page.getByRole("radio", { name: "All machines" })).toBeChecked();
  await page.getByRole("searchbox").fill("neon");
  const rows = page.getByRole("list", { name: "Search results" }).getByRole("button");
  await expect(rows.first()).toBeVisible();
  // Every row names a machine, and more than one machine appears among the results.
  const names = await rows.evaluateAll((nodes) =>
    nodes.map((node) => node.querySelector(".song__machines > span:nth-child(2)")?.textContent?.trim() ?? ""),
  );
  expect(names.every((name) => name !== "")).toBe(true);
  expect(new Set(names).size).toBeGreaterThan(1);

  await rows.first().click();
  await expect(page.getByRole("dialog").locator(".line__name")).toHaveText(names[0] ?? "");
  await page.keyboard.press("Escape");

  await page.reload();
  await expect(page.getByRole("radio", { name: "All machines" })).toBeChecked();
});

test("the navigation bar and the machine sign stay pinned while the list scrolls", async ({ page }) => {
  await page.getByRole("tab", { name: /^N, \d+ songs?/ }).click();
  await page.evaluate(() => window.scrollTo(0, 1200));
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeGreaterThan(600);
  const header = await page.locator("header.header").boundingBox();
  const sign = await page.locator(".line").first().boundingBox();
  if (!header || !sign) throw new Error("the bar or the sign is not on the page");
  expect(Math.round(header.y)).toBe(0);
  // The machine sign sits directly under the bar (within a pixel), so nothing slides between them.
  expect(Math.abs(sign.y - (header.y + header.height))).toBeLessThanOrEqual(1);
  // Keyboard focus is never hidden under the two pinned bars.
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.getBoundingClientRect().top ?? 0);
  expect(focused).toBeGreaterThanOrEqual(header.height + sign.height - 1);
});

test("a long scroll offers Back to top, which returns to the start", async ({ page }) => {
  await page.getByRole("tab", { name: /^N, \d+ songs?/ }).click();
  await expect(page.getByRole("button", { name: "Back to top" })).toHaveCount(0);
  await page.evaluate(() => window.scrollTo(0, 3000));
  const button = page.getByRole("button", { name: "Back to top" });
  await expect(button).toBeVisible();
  const box = await button.boundingBox();
  const view = page.viewportSize();
  if (!box || !view) throw new Error("no button or viewport");
  expect(box.height).toBeGreaterThanOrEqual(44);
  expect(box.x + box.width).toBeLessThanOrEqual(view.width);
  expect(box.y + box.height).toBeLessThanOrEqual(view.height);
  const scan = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(scan.violations.map((v) => v.id)).toEqual([]);
  await button.click();
  await expect.poll(() => page.evaluate(() => window.scrollY)).toBeLessThan(5);
  await expect(button).toHaveCount(0);
  await expect(page.getByRole("main")).toBeFocused();
});

test("with text at twice the size the wordmark does not run under the header buttons", async ({ page }) => {
  await page.addStyleTag({ content: "html { font-size: 200% !important }" });
  const brand = await page.locator("header .brand").boundingBox();
  const actions = await page.locator("header .header__actions").boundingBox();
  if (!brand || !actions) throw new Error("header parts are not on the page");
  // Side by side or on separate rows, but never on top of each other.
  const apart = brand.x + brand.width <= actions.x + 1 || brand.y + brand.height <= actions.y + 1;
  expect(apart).toBe(true);
  // The pinned machine sign still sits directly under the (now taller) bar.
  const header = await page.locator("header.header").boundingBox();
  const sign = await page.locator(".line").first().boundingBox();
  if (!header || !sign) throw new Error("the bar or the sign is not on the page");
  await page.evaluate(() => window.scrollTo(0, 1500));
  const pinned = await page.locator(".line").first().boundingBox();
  expect(Math.abs((pinned?.y ?? -99) - (header.y + header.height))).toBeLessThanOrEqual(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});
