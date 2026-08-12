import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("admin: register tenant via API then log in via /admin/login", async ({ page, request }) => {
  const slug = `e2e-admin-${Date.now()}`;
  const email = `admin-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

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

  await page.goto("/admin/login");
  await expect(page.getByRole("heading", { name: /admin log in/i })).toBeVisible();

  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: /facilities/i })).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) => v.impact === "critical" || v.impact === "serious"),
  ).toEqual([]);
});

test("customer: log in via /login and reach /book", async ({ page, request }) => {
  const slug = `e2e-cust-${Date.now()}`;
  const email = `cust-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  // Register a tenant + admin via the API
  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Customer Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: email,
      admin_password: password,
      admin_full_name: "E2E Customer",
    },
  });
  expect(reg.status()).toBe(201);

  // The admin who registered has the tenant_admin role. To test the customer
  // path, create a customer user via the admin endpoint first.
  // (Reuse the same password for simplicity.)
  const loginAsAdmin = await request.post("http://127.0.0.1:8765/v1/auth/login", {
    data: { email, password },
  });
  expect(loginAsAdmin.status()).toBe(200);
  const adminAccess = (await loginAsAdmin.json()).access_token;
  const create = await request.post("http://127.0.0.1:8765/v1/auth/users", {
    data: {
      email: `customer-${slug}@example.com`,
      full_name: "E2E Customer",
      password,
      roles: ["customer"],
    },
    headers: { Authorization: `Bearer ${adminAccess}` },
  });
  expect(create.status()).toBe(201);

  // Now log in as the customer via /login
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: /^log in$/i })).toBeVisible();

  await page.getByLabel("Email").fill(`customer-${slug}@example.com`);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  await expect(page).toHaveURL(/\/book$/);
});
