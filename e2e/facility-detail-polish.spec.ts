import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("/book/facilities/:id passes axe-core (light)", async ({ page }) => {
  // seed has splash-sports-club facility; assumes migration ran
  await page.goto("/book/facilities/splash-sports-club");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/facilities/:id passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book/facilities/splash-sports-club");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/facilities/:id shows the not-found state for an unknown id", async ({ page }) => {
  await page.goto("/book/facilities/does-not-exist");
  await expect(page.getByText(/not found/i)).toBeVisible();
  await page.getByRole("link", { name: /browse facilities/i }).click();
  await expect(page).toHaveURL(/\/book$/);
});
