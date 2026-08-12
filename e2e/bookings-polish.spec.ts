import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("/book/bookings passes axe-core (light)", async ({ page }) => {
  // assumes a logged-in customer via existing seed; see admin-user-creation.spec.ts
  await page.goto("/book/bookings");
  await expect(page.getByRole("heading", { level: 1, name: /my bookings/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});

test("/book/bookings passes axe-core (dark)", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/book/bookings");
  await expect(page.getByRole("heading", { level: 1, name: /my bookings/i })).toBeVisible();
  const results = await new AxeBuilder({ page }).analyze();
  expect(results.violations).toEqual([]);
});
