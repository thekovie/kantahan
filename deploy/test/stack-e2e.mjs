// Drives the running production stack in a real browser (see smoke.sh): the strict
// Content-Security-Policy must not block anything the app needs, the seeded catalog must load and
// search, the service worker must register, and a contact request must go all the way to the mail sink.
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const require = createRequire(join(here, "..", "..", "apps", "web", "package.json"));
const { chromium } = require("@playwright/test");
const base = process.argv[2] ?? "http://localhost:18080";

const problems = [];
const expect = (ok, what) => {
  if (ok) console.log(`  ok    ${what}`);
  else {
    console.log(`  FAIL  ${what}`);
    problems.push(what);
  }
};

const browser = await chromium.launch({ channel: "chrome" });
const context = await browser.newContext({ viewport: { width: 420, height: 900 } });
const page = await context.newPage();
const violations = [];
const errors = [];
await page.addInitScript(() => {
  document.addEventListener("securitypolicyviolation", (event) => {
    (window.__csp ??= []).push(`${event.violatedDirective} ${event.blockedURI}`);
  });
});
page.on("console", (message) => {
  if (message.type() === "error") errors.push(message.text());
});
page.on("pageerror", (error) => errors.push(String(error)));

await page.goto(base + "/");
await page.getByRole("searchbox").waitFor({ timeout: 15000 });
await page.getByRole("searchbox").fill("smoke test");
const appears = (locator) => locator.waitFor({ state: "visible", timeout: 10000 }).then(() => true, () => false);
const found = await appears(page.getByText("Smoke Test Song One").first());
expect(found, "the published catalog loads and can be searched");
expect((await page.locator("html").getAttribute("data-theme")) !== null, "the inline theme script ran (data-theme is set)");
const registered = await page
  .evaluate(async () => Boolean(await Promise.race([navigator.serviceWorker.ready, new Promise((r) => setTimeout(() => r(null), 8000))])))
  .catch(() => false);
expect(registered, "the service worker registers under the policy");

await page.goto(base + "/rights");
await page.getByRole("radio", { name: "Remove an entry" }).check();
await page.getByLabel(/^Message/).fill("Please remove song 00001 in this browser smoke test.");
await page.getByRole("button", { name: "Send message" }).click();
const thanked = await appears(page.getByRole("heading", { name: "Message sent" }));
expect(thanked, "a request sent from the page is accepted by the contact service");

violations.push(...(await page.evaluate(() => window.__csp ?? []).catch(() => [])));
expect(violations.length === 0, `no Content-Security-Policy violations${violations.length ? `: ${violations.join("; ")}` : ""}`);
expect(errors.length === 0, `no console errors${errors.length ? `: ${errors.join("; ").slice(0, 300)}` : ""}`);

await browser.close();
process.exit(problems.length === 0 ? 0 : 1);
