import { test, expect } from "@playwright/test";

test("admin creates a customer; customer logs in at /login", async ({ page, request }) => {
  const slug = `e2e-create-${Date.now()}`;
  const adminEmail = `admin-${slug}@example.com`;
  const customerEmail = `customer-${slug}@example.com`;
  const password = "CorrectHorseBatteryStaple!9";

  // Register tenant
  const reg = await request.post("http://127.0.0.1:8765/v1/auth/register-tenant", {
    data: {
      tenant_name: "E2E Create User Tenant",
      tenant_slug: slug,
      primary_contact_email: `contact-${slug}@example.com`,
      admin_email: adminEmail,
      admin_password: password,
      admin_full_name: "E2E Admin",
    },
  });
  expect(reg.status()).toBe(201);

  // Log in as admin via API to get the access token
  const loginAsAdmin = await request.post("http://127.0.0.1:8765/v1/auth/login", {
    data: { email: adminEmail, password },
  });
  expect(loginAsAdmin.status()).toBe(200);
  const adminAccess = (await loginAsAdmin.json()).access_token;

  // Create a customer user via API
  const create = await request.post("http://127.0.0.1:8765/v1/auth/users", {
    data: { email: customerEmail, full_name: "E2E Customer", password, roles: ["customer"] },
    headers: { Authorization: `Bearer ${adminAccess}` },
  });
  expect(create.status()).toBe(201);

  // Log in as admin via UI to verify admin flow works
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByRole("heading", { name: /facilities/i })).toBeVisible();

  // Log out and log in as the customer
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").fill(customerEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  // Lands on /book (customer home)
  await expect(page).toHaveURL(/\/book$/);
});
