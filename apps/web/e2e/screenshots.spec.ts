import { mkdirSync } from "node:fs";
import { join } from "node:path";
import { expect, test } from "@playwright/test";

// Design review aid, not a regression test: `SCREENSHOTS=1 npx playwright test e2e/screenshots.spec.ts`
// writes the key screens to .impeccable/review/ at the repository root.
test.skip(!process.env.SCREENSHOTS, "set SCREENSHOTS=1 to capture review screenshots");

const OUT = join(process.cwd(), "..", "..", ".impeccable", "review");
mkdirSync(OUT, { recursive: true });

test.use({ reducedMotion: "reduce" });

for (const scheme of ["dark", "light"] as const) {
  test.describe(scheme, () => {
    test.use({ colorScheme: scheme });

    test(`screens in ${scheme}`, async ({ page }, info) => {
      const name = (state: string) => join(OUT, `${info.project.name}-${scheme}-${state}.png`);
      await page.goto("/");
      await expect(page.getByRole("tablist")).toBeVisible();
      await page.getByRole("tab", { name: /^N, / }).click();
      await page.screenshot({ path: name("index") });

      await page.getByRole("searchbox").fill("neon");
      await expect(page.getByRole("status").filter({ hasText: "found" })).toBeVisible();
      await page.screenshot({ path: name("results") });

      await page.evaluate(() => window.scrollTo(0, 900));
      await page.screenshot({ path: name("scrolled") });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.screenshot({ path: name("readout") });
      await page.keyboard.press("Escape");

      await page.getByRole("searchbox").fill("qqqqqq");
      await expect(page.getByRole("heading", { name: "No songs found" })).toBeVisible();
      await page.screenshot({ path: name("empty") });

      for (const model of ["Model B", "Model C"]) {
        await page.goto("/");
        await page.getByRole("radio", { name: model }).click();
        await expect(page.getByRole("radio", { name: model })).toBeChecked();
        await page.getByRole("searchbox").fill("neon");
        await expect(page.getByRole("status").filter({ hasText: "found" })).toBeVisible();
        const slug = model.replace(" ", "").toLowerCase();
        await page.screenshot({ path: name(`${slug}-results`) });
        await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
        await expect(page.getByRole("dialog")).toBeVisible();
        await page.screenshot({ path: name(`${slug}-readout`) });
        await page.keyboard.press("Escape");
      }

      await page.goto("/about");
      await page.screenshot({ path: name("about"), fullPage: true });
    });
  });
}
