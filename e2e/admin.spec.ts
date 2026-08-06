import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("admin: register tenant via API then log in via UI", async ({ page, request }) => {
  const slug = `e2e-admin-${Date.now()}`;
  const email = `admin-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  // Register tenant via backend API
  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Admin Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: email,
      admin_password: password,
      admin_full_name: "E2E Admin",
    },
  });
  expect(reg.status()).toBe(201);

  // Open admin-pwa login page
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /admin log in/i })).toBeVisible();

  // Log in
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  // Land on facilities page
  await expect(page).toHaveURL(/\/admin\/facilities/);
  await expect(page.getByRole("heading", { name: /facilities/i })).toBeVisible();

  // Accessibility scan
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => v.impact === "critical" || v.impact === "serious"),
  ).toEqual([]);
});
