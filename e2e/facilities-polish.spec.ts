import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("/book passes axe-core (light)", async ({ page }) => {
  await page.goto("/book");
  await expect(page.getByRole("heading", { level: 1, name: /facilities/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book");
  await expect(page.getByRole("heading", { level: 1, name: /facilities/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
