import { expect, test } from "@playwright/test";

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

  // Log in as admin
  await page.goto("/admin/login");
  await page.getByLabel("Email").fill(adminEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();
  await expect(page).toHaveURL(/\/admin$/);

  // Navigate to users page and create a customer
  await page.goto("/admin/users");
  await expect(page.getByRole("heading", { name: /users/i })).toBeVisible();
  await page.getByRole("button", { name: /add user/i }).click();
  await page.getByLabel("Email").fill(customerEmail);
  await page.getByLabel("Full name").fill("E2E Customer");
  await page.getByLabel("Temporary password").fill(password);
  await page.getByLabel("Customer").check();
  await page
    .getByRole("button", { name: /add user/i })
    .last()
    .click();

  // The new user appears in the list
  await expect(page.getByText(customerEmail)).toBeVisible();

  // Log out (best effort) and log in as the customer
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByLabel("Email").fill(customerEmail);
  await page.getByLabel("Password").fill(password);
  await page.getByRole("button", { name: /log in/i }).click();

  // Lands on /book (customer home)
  await expect(page).toHaveURL(/\/book$/);
});
