import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const scheme of ["dark", "light"] as const) {
  test.describe(`${scheme} theme`, () => {
    test.use({ colorScheme: scheme });

    const scan = async (page: import("@playwright/test").Page) => {
      const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
      expect(
        results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`),
        "accessibility violations",
      ).toEqual([]);
    };

    test("songbook index has no accessibility violations", async ({ page }) => {
      await page.goto("/");
      await expect(page.getByRole("tablist")).toBeVisible();
      await scan(page);
    });

    test("search results have no accessibility violations", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("searchbox").fill("neon");
      await expect(page.getByRole("status").filter({ hasText: "found" })).toBeVisible();
      await scan(page);
    });

    test("the read-out has no accessibility violations", async ({ page }) => {
      await page.goto("/");
      await page.getByRole("searchbox").fill("neon");
      await page.getByRole("list", { name: "Search results" }).getByRole("button").first().click();
      await expect(page.getByRole("dialog")).toBeVisible();
      await page.waitForTimeout(600); // let the digits finish lighting up before measuring contrast
      await scan(page);
    });

    test("the contact form has no accessibility violations, including with its errors showing", async ({ page }) => {
      await page.goto("/rights");
      await expect(page.getByRole("form", { name: "Contact form" })).toBeVisible();
      await scan(page);
      await page.getByRole("button", { name: "Send message" }).click();
      await expect(page.getByText("Choose what this is about.")).toBeVisible();
      await scan(page);
    });

    test("the static pages have no accessibility violations", async ({ page }) => {
      for (const path of ["/about", "/privacy", "/rights"]) {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
        await scan(page);
      }
    });
  });
}
