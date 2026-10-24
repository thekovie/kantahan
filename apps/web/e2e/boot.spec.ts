import { expect, test } from "@playwright/test";

// A first visit: nothing saved, so no machine chosen yet (the app opens on All machines).
test.use({ serviceWorkers: "block", storageState: { cookies: [], origins: [] } });

// The page's inline boot script starts the manifest download on a first visit so it overlaps with the
// scripts loading; the app must use that download (one request, not two), and a returning visitor,
// who already has the catalog saved, must not trigger any manifest request just by opening the app.
test("a first visit downloads the manifest once, and opening the app again does not", async ({ page }) => {
  const manifestRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/catalog/manifest.json")) manifestRequests.push(request.url());
  });

  await page.goto("/");
  await expect(page.getByRole("radio", { name: "All machines" })).toBeChecked();
  await page.waitForTimeout(500);
  expect(manifestRequests).toHaveLength(1);

  manifestRequests.length = 0;
  await page.reload();
  await expect(page.getByRole("radio", { name: "All machines" })).toBeChecked();
  await page.waitForTimeout(500);
  expect(manifestRequests).toHaveLength(0);

  await page.getByRole("button", { name: "Check for updates" }).click();
  await expect(page.getByText("Up to date.")).toBeVisible();
  expect(manifestRequests).toHaveLength(1); // an explicit check always asks the server
});
