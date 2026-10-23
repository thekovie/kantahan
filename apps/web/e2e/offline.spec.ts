import { expect, test } from "@playwright/test";

test("works with no connection after the first visit", async ({ page, context }) => {
  await page.goto("/");
  await expect(page.getByRole("radio", { name: "Model A" })).toBeChecked();
  await expect(page.getByRole("tablist", { name: "Songs by first letter" })).toBeVisible();

  // Wait until the service worker controls the page, so the shell is cached for offline use.
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);

  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole("radio", { name: "Model A" })).toBeChecked();

  await page.getByRole("searchbox").fill("neon");
  await expect(page.getByRole("status").filter({ hasText: /songs? found/ })).toBeVisible();
  await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
});

test("pages other than the songbook also load offline", async ({ page, context }) => {
  await page.goto("/");
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  await context.setOffline(true);
  await page.goto("/about");
  await expect(page.getByRole("heading", { name: "About Kantahan" })).toBeVisible();
});

test("checking for updates with no connection says so and keeps the songs", async ({ page, context }) => {
  await page.goto("/");
  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload();
  await expect.poll(() => page.evaluate(() => navigator.serviceWorker.controller !== null)).toBe(true);
  await context.setOffline(true);
  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(page.getByText("No connection. Your saved songs still work.")).toBeVisible();
  await expect(page.getByRole("tablist", { name: "Songs by first letter" })).toBeVisible();
});
