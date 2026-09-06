import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";

// These are real UI captures, refreshed explicitly rather than on every CI run.
test("capture the current README demo", async ({ page }) => {
  test.skip(
    process.env.LAB_REFRESH_DEMOS !== "1",
    "Opt-in documentation capture",
  );
  mkdirSync("../docs/images", { recursive: true });
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Find the input that breaks your code.",
    }),
  ).toBeVisible();
  await page.screenshot({
    path: "../docs/images/workbench.png",
    fullPage: true,
  });

  await page.getByRole("button", { name: "Find a failing case" }).click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel("Repair Python code")).toHaveValue(
    /sorted\(set/,
  );
  await page.getByText("A question to think about", { exact: true }).click();
  await page.getByRole("button", { name: "Show a working example" }).click();
  await page
    .getByRole("button", { name: "Check your fix", exact: true })
    .click();
  await expect(
    page.getByText("Previous failing example: passed", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("Unseen inputs: No errors found in these tests · 100/100"),
  ).toBeVisible();
  await page
    .locator(".results")
    .screenshot({ path: "../docs/images/check-fix.png" });

  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page
    .locator(".results")
    .screenshot({ path: "../docs/images/mobile.png" });
});
