import { expect, test } from "@playwright/test";

test.use({ colorScheme: "dark", serviceWorkers: "block" });

async function fillForm(page: import("@playwright/test").Page) {
  await page.goto("/rights");
  await page.getByRole("radio", { name: "Correct a number, title or artist" }).check();
  await page.getByLabel("Which machine and song? (optional)").fill("Reyna, 00589");
  await page.getByLabel(/^Message/).fill("Song 00589 lists the wrong artist for this machine.");
  await page.getByLabel(/Your e-mail/).fill("someone@example.org");
}

test("a request is sent as JSON to the contact endpoint and thanked", async ({ page }) => {
  let seen: { method: string; body: Record<string, string> } | null = null;
  await page.route("**/api/contact", async (route) => {
    seen = { method: route.request().method(), body: route.request().postDataJSON() };
    await route.fulfill({ status: 202, json: { ok: true } });
  });
  await fillForm(page);
  await page.getByRole("button", { name: "Send message" }).click();
  await expect(page.getByRole("heading", { name: "Message sent" })).toBeFocused();
  expect(seen).toMatchObject({
    method: "POST",
    body: { type: "correction", reference: "Reyna, 00589", email: "someone@example.org", website: "" },
  });
});

test("a rate limit, an outage and a lost connection each get a plain explanation and keep the message", async ({ page }) => {
  await fillForm(page);
  const send = page.getByRole("button", { name: "Send message" });

  await page.route("**/api/contact", (route) => route.fulfill({ status: 429, headers: { "Retry-After": "600" }, json: { ok: false } }));
  await send.click();
  await expect(page.getByRole("alert")).toContainText("Try again in about 10 minutes");

  await page.unroute("**/api/contact");
  await page.route("**/api/contact", (route) => route.fulfill({ status: 503, json: { ok: false, error: "unavailable" } }));
  await send.click();
  await expect(page.getByRole("alert")).toContainText("could not be sent right now");

  await page.unroute("**/api/contact");
  await page.route("**/api/contact", (route) => route.abort());
  await send.click();
  await expect(page.getByRole("alert")).toContainText("No connection");
  await expect(page.getByLabel(/^Message/)).toHaveValue("Song 00589 lists the wrong artist for this machine.");
});

test("the form works with the keyboard alone", async ({ page }) => {
  await page.route("**/api/contact", (route) => route.fulfill({ status: 202, json: { ok: true } }));
  await page.goto("/rights");
  await page.getByRole("radio", { name: "Remove an entry" }).focus();
  await page.keyboard.press("Space");
  await page.getByLabel(/^Message/).focus();
  await page.keyboard.type("Please remove this entry from the songbook.");
  await page.getByRole("button", { name: "Send message" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Message sent" })).toBeVisible();
});

test("the hidden trap field is not reachable by keyboard", async ({ page }) => {
  await page.goto("/rights");
  const trap = page.locator('input[name="website"]');
  await expect(trap).toHaveAttribute("tabindex", "-1");
  await expect(trap).toBeHidden({ timeout: 100 }).catch(() => undefined);
  const box = await trap.boundingBox();
  expect(box === null || box.x < 0).toBe(true);
});
