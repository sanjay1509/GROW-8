import { expect, test } from "@playwright/test";

async function openLogin(page) {
  await page.goto("/login");
  await page.getByRole("button", { name: "Login", exact: true }).click();
}

test("AUTH-UI-001 @sanity Rejects a successful login for the wrong selected role", async ({ page }) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 200,
      json: {
        access_token: "creator-token",
        user: { user_id: 2, email: "creator@example.test", full_name: "Test Creator", role: "creator" },
      },
    }),
  );
  await openLogin(page);
  await page.getByLabel("Email").fill("creator@example.test");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: "Login", exact: true }).last().click();

  await expect(page.getByRole("alert")).toHaveText(
    "This account is registered as creator. Please select the correct role.",
  );
  await expect(page).toHaveURL(/\/login$/);
  expect(await page.evaluate(() => localStorage.getItem("access_token"))).toBeNull();
});

test("AUTH-UI-002 @sanity Stores a valid creator token and redirects to the creator dashboard", async ({ page }) => {
  await page.route("**/api/v1/auth/login", (route) =>
    route.fulfill({
      status: 200,
      json: {
        access_token: "creator-token",
        user: { user_id: 2, email: "creator@example.test", full_name: "Test Creator", role: "creator" },
      },
    }),
  );
  await openLogin(page);
  await page.getByRole("button", { name: /Creator/ }).click();
  await page.getByLabel("Email").fill("creator@example.test");
  await page.getByLabel("Password", { exact: true }).fill("correct-password");
  await page.getByRole("button", { name: "Login", exact: true }).last().click();

  await expect(page).toHaveURL(/\/creator\/dashboard$/);
  expect(await page.evaluate(() => localStorage.getItem("access_token"))).toBe("creator-token");
});
