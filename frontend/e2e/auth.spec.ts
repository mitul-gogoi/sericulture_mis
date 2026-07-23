import { test, expect, Page } from "@playwright/test";

async function login(page: Page, mobile: string, password: string) {
  await page.goto("/login");
  await page.locator('[data-testid="login-mobile"]').fill(mobile);
  await page.locator('[data-testid="login-password"]').fill(password);
  await page.locator('[data-testid="login-submit"]').click();
  await page.waitForURL("**/dashboard", { timeout: 15000 });
}

test.describe("Sericulture MIS — auth + role-aware navigation", () => {
  test("rejects invalid credentials", async ({ page }) => {
    await page.goto("/login");
    await page.locator('[data-testid="login-mobile"]').fill("0000000000");
    await page.locator('[data-testid="login-password"]').fill("wrong");
    await page.locator('[data-testid="login-submit"]').click();
    await page.waitForTimeout(2000);
    await expect(page).toHaveURL(/\/login/);
  });

  test("state admin login → dashboard with all nav items", async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
    await expect(page).toHaveURL(/\/dashboard/);
    const navCount = await page.locator('[data-testid^="nav-"]').count();
    expect(navCount).toBeGreaterThanOrEqual(9);
    // Master Data group — expand and verify sub-items
    await page.locator('[data-testid="nav-group-toggle-master-data"]').click();
    await expect(page.locator('[data-testid="nav-sectors"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-stages"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-districts"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-sericulture-circles"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-caste"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-religion"]')).toBeVisible();
    // Farmers & FIGs group — expand and verify sub-items
    await page.locator('[data-testid="nav-group-toggle-farmers-figs"]').click();
    await expect(page.locator('[data-testid="nav-farmer-management"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-fig-management"]')).toBeVisible();
    // Schemes group — expand and verify sub-items
    await page.locator('[data-testid="nav-group-toggle-schemes"]').click();
    await expect(page.locator('[data-testid="nav-scheme-management"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-allocations"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-beneficiaries"]')).toBeVisible();
    // User Management group — expand and verify sub-items
    await page.locator('[data-testid="nav-group-toggle-user-management"]').click();
    await expect(page.locator('[data-testid="nav-state-admins"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-district-admins"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-fig-presidents"]')).toBeVisible();
  });

  test("district admin sees district-scoped sidebar (no user mgmt)", async ({ page }) => {
    await login(page, "8888888888", "District@123");
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('[data-testid="nav-group-toggle-user-management"]')).toHaveCount(0);
    await expect(page.locator('[data-testid="nav-gps-verification"]')).toBeVisible();
    // Schemes for DA is a collapsible group — expand and verify Beneficiaries sub-item
    await page.locator('[data-testid="nav-group-toggle-schemes"]').click();
    await expect(page.locator('[data-testid="nav-scheme-beneficiaries"]')).toBeVisible();
  });

  test("FIG president sees Monthly Submission menu", async ({ page }) => {
    await login(page, "7777777777", "Fig@123");
    await expect(page).toHaveURL(/\/dashboard/);
    // Monthly Submission is a collapsible group — expand it first
    await page.locator('[data-testid="nav-group-toggle-monthly-submission"]').click();
    await expect(page.locator('[data-testid="nav-submit-monthly-meeting-data"]')).toBeVisible();
  });

  test("logout returns to login", async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
    await page.locator('[data-testid="logout-btn"]').click();
    await page.waitForURL("**/login", { timeout: 8000 });
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe("Sericulture MIS — page navigation as State Admin", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
  });

  test("Farmers, FIGs, Schemes, Reports, Masters all render", async ({ page }) => {
    for (const slug of ["farmers", "figs", "schemes", "reports", "masters"]) {
      await page.goto(`/${slug}`);
      await page.waitForLoadState("domcontentloaded");
      await expect(page.locator("h1").first()).toBeVisible({ timeout: 15000 });
    }
  });

  test("Notifications page shows inbox tab", async ({ page }) => {
    await page.goto("/notifications");
    await expect(page.locator('[data-testid="tab-inbox"]')).toBeVisible();
  });
});

test.describe("Sericulture MIS — Monthly Submission wizard as FP", () => {
  test("opens 4-step wizard with meeting fields", async ({ page }) => {
    await login(page, "7777777777", "Fig@123");
    await page.goto("/submission");
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[data-testid="meeting-title"]')).toBeVisible();
    await expect(page.locator('[data-testid="meeting-date"]')).toBeVisible();
    await expect(page.locator('[data-testid="wizard-next"]')).toBeVisible();
  });
});

test.describe("Sericulture MIS — Master Data CRUD as State Admin", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
  });

  test("SA can create + deactivate + reactivate a Sector", async ({ page }) => {
    await page.goto("/masters/sectors");
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[data-testid="master-title-sectors"]')).toBeVisible();

    const name = `E2E-Sector-${Date.now()}`;
    await page.locator('[data-testid="master-add-sectors"]').click();
    await page.locator('[data-testid="master-input-sectors-sector_name"]').fill(name);
    await page.locator('[data-testid="master-form-submit-sectors"]').click();

    // Row appears; grab its id via cell text and use the toggle button in that row
    const row = page.locator(`tr:has-text("${name}")`).first();
    await expect(row).toBeVisible({ timeout: 8000 });
    await expect(row.getByText("ACTIVE", { exact: false })).toBeVisible();

    // Deactivate
    await row.getByRole("button", { name: /Deactivate/i }).click();
    await expect(row.getByText("INACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });

    // Reactivate
    await row.getByRole("button", { name: /Activate/i }).click();
    await expect(row.getByText("ACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
  });

  test("SA can create a Stage bound to a Sector", async ({ page }) => {
    await page.goto("/masters/stages");
    await page.waitForLoadState("networkidle");
    await expect(page.locator('[data-testid="master-title-stages"]')).toBeVisible();

    const name = `E2E-Stage-${Date.now()}`;
    await page.locator('[data-testid="master-add-stages"]').click();
    await page.locator('[data-testid="master-input-stages-stage_name"]').fill(name);
    // Pick first available sector
    const sectorSelect = page.locator('[data-testid="master-input-stages-sector_id"]');
    const firstOption = await sectorSelect.locator("option").nth(1).getAttribute("value");
    await sectorSelect.selectOption(firstOption || "");
    await page.locator('[data-testid="master-input-stages-yield_stage_type"]').fill("Cocoon");
    await page.locator('[data-testid="master-input-stages-output_unit"]').fill("kg");
    await page.locator('[data-testid="master-form-submit-stages"]').click();

    await expect(page.locator(`tr:has-text("${name}")`).first()).toBeVisible({ timeout: 8000 });
  });

  test("Non-SA users are blocked from masters CRUD UI", async ({ page }) => {
    // Log out first
    await page.locator('[data-testid="logout-btn"]').click();
    await page.waitForURL("**/login");
    // Sign in as District Admin
    await page.locator('[data-testid="login-mobile"]').fill("8888888888");
    await page.locator('[data-testid="login-password"]').fill("District@123");
    await page.locator('[data-testid="login-submit"]').click();
    await page.waitForURL("**/dashboard");
    // DA has no Masters group in the sidebar
    await expect(page.locator('[data-testid="nav-group-toggle-masters"]')).toHaveCount(0);
  });
});

test.describe("Sericulture MIS — Scheme CRUD as State Admin", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
  });

  test("SA can create + edit + deactivate + reactivate a Scheme", async ({ page }) => {
    await page.goto("/schemes");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Schemes");

    const name = `E2E-Scheme-${Date.now()}`;
    await page.locator('[data-testid="schemes-add"]').click();
    await page.locator('[data-testid="schemes-input-name"]').fill(name);
    await page.locator('[data-testid="schemes-input-budget"]').fill("100000");
    await page.locator('[data-testid="schemes-form-submit"]').click();

    // Find the specific card via testid + text
    const card = page.locator('[data-testid^="schemes-card-"]').filter({ hasText: name }).first();
    await expect(card).toBeVisible({ timeout: 8000 });

    // Edit — bump budget
    await card.locator('[data-testid^="schemes-edit-"]').click();
    await page.locator('[data-testid="schemes-input-budget"]').fill("250000");
    await page.locator('[data-testid="schemes-form-submit"]').click();
    await expect(card.getByText(/250,000/)).toBeVisible({ timeout: 6000 });

    // Deactivate
    await card.locator('[data-testid^="schemes-toggle-"]').click();
    await expect(card.getByText("INACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });

    // Reactivate
    await card.locator('[data-testid^="schemes-toggle-"]').click();
    await expect(card.getByText("ACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
  });

  test("Allocations page renders + shows form for SA", async ({ page }) => {
    await page.goto("/schemes/allocations");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Scheme Allocations");
    await expect(page.locator('[data-testid="schemes-alloc-add"]')).toBeVisible();
  });

  test("Beneficiaries page renders", async ({ page }) => {
    await page.goto("/schemes/beneficiaries");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("Beneficiaries");
    await expect(page.locator('[data-testid="schemes-ben-add"]')).toBeVisible();
  });
});

test.describe("Sericulture MIS — User Management CRUD as State Admin", () => {
  test.beforeEach(async ({ page }) => {
    await login(page, "9999999999", "Admin@123");
  });

  test("SA can view District Admins list and page renders", async ({ page }) => {
    await page.goto("/users");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("District Admins");
    await expect(page.locator('[data-testid="users-da-add"]')).toBeVisible();
  });

  test("SA can view FIG Presidents list and toggle active", async ({ page }) => {
    await page.goto("/users/fig-presidents");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("FIG Presidents");
    // At least the seeded FP account should be listed
    const row = page.locator('[data-testid^="users-fp-row-"]').first();
    await expect(row).toBeVisible({ timeout: 6000 });
    // Deactivate then reactivate
    await row.getByRole("button", { name: /Deactivate/i }).click();
    await expect(row.getByText("INACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
    await row.getByRole("button", { name: /Activate/i }).click();
    await expect(row.getByText("ACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
  });

  test("SA can create + deactivate + reactivate a State Admin, cannot self-deactivate", async ({ page }) => {
    await page.goto("/users/state-admins");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("h1")).toContainText("State Admins");

    // Own account should show "You" badge and disabled deactivate
    const myRow = page.locator('[data-testid^="users-sa-row-"]').filter({ hasText: "You" }).first();
    await expect(myRow).toBeVisible();
    await expect(myRow.locator('[data-testid^="users-sa-toggle-"]')).toBeDisabled();

    // Create a new SA
    const mobile = `9${Date.now().toString().slice(-9)}`;
    await page.locator('[data-testid="users-sa-add"]').click();
    await page.locator('[data-testid="users-sa-input-name"]').fill("E2E SA");
    await page.locator('[data-testid="users-sa-input-mobile"]').fill(mobile);
    await page.locator('[data-testid="users-sa-input-password"]').fill("Test@123");
    await page.locator('[data-testid="users-sa-form-submit"]').click();

    const row = page.locator('[data-testid^="users-sa-row-"]').filter({ hasText: mobile }).first();
    await expect(row).toBeVisible({ timeout: 6000 });
    await row.locator('[data-testid^="users-sa-toggle-"]').click();
    await expect(row.getByText("INACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
    await row.locator('[data-testid^="users-sa-toggle-"]').click();
    await expect(row.getByText("ACTIVE", { exact: false })).toBeVisible({ timeout: 6000 });
  });
});
