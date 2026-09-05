import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("demo, reduction, prompts, repair and export preserve real evidence", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Make failures explainable." }),
  ).toBeVisible();
  await expect(
    page.getByText("Illustration only · No experiment results yet"),
  ).toBeVisible();
  mkdirSync("../artifacts", { recursive: true });
  await page.screenshot({
    path: "../artifacts/workbench-desktop.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Run experiment", exact: false })
    .click();
  await expect(
    page.getByText("Wrong answer found", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("12 → 2", { exact: true })).toBeVisible();
  await expect(page.getByText("Local fixed point reached")).toBeVisible();
  await page.getByRole("button", { name: "Failure only", exact: true }).click();
  await expect(
    page.getByRole("textbox", { name: "Repair prompt" }),
  ).not.toHaveValue(/Expected:/);
  await page
    .getByRole("button", { name: "Reduced input", exact: true })
    .click();
  await expect(
    page.getByRole("textbox", { name: "Repair prompt" }),
  ).toHaveValue(/Expected:/);
  await page
    .getByRole("button", { name: "Verify repair", exact: true })
    .click();
  await expect(page.getByText("Tests passed · 100/100")).toBeVisible();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export experiment" }).click();
  const downloaded = await pending;
  expect(downloaded.suggestedFilename()).toMatch(/^counterexample-.*\.json$/);
  await downloaded.saveAs("../artifacts/browser-export.json");
  await page.screenshot({
    path: "../artifacts/workbench-results.png",
    fullPage: true,
  });
  expect(errors).toEqual([]);
});

test("other tasks, correct example and unavailable custom runner", async ({
  page,
}) => {
  await page.route("**/api/health", (route) =>
    route.fulfill({
      json: {
        version: "1.0.0",
        runner: {
          available: false,
          reason: "Docker unavailable (test fixture)",
        },
      },
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "02 Binary search" }).click();
  await page
    .getByRole("button", { name: "Run experiment", exact: false })
    .click();
  await expect(
    page.getByText("Wrong answer found", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "03 Maximum subarray" }).click();
  await page
    .getByRole("button", { name: "Run experiment", exact: false })
    .click();
  await expect(page.getByText("8 → 1", { exact: true })).toBeVisible();
  await page.getByLabel("Choose an example").selectOption("correct");
  await page
    .getByRole("button", { name: "Run experiment", exact: false })
    .click();
  await expect(page.getByText("Tests passed", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Your code", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Candidate Python code" })
    .fill("def solve(numbers):\n    return 0");
  await expect(
    page.getByRole("button", { name: "Run experiment", exact: false }),
  ).toBeDisabled();
  await expect(
    page.getByText(
      "Install Docker and build the runner as described in the README. Built-in demos remain available.",
    ),
  ).toBeVisible();
});

test("mobile layout stays within viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Make failures explainable." }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Run experiment", exact: false })
    .click();
  await expect(
    page.getByText("Wrong answer found", { exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/workbench-mobile.png",
    fullPage: true,
  });
});

test("the workbench, guide and errors use English only", async ({ page }) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(
    page.getByRole("heading", { name: "Make failures explainable." }),
  ).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
  await page.getByRole("button", { name: "How it works", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Understand before you trust." }),
  ).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
  await page.getByRole("button", { name: "Start experimenting" }).click();
  await page.route("**/api/run", (route) =>
    route.fulfill({
      status: 409,
      json: { error: "An experiment is already running. Try again shortly." },
    }),
  );
  await page.getByRole("button", { name: "Run experiment" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "An experiment is already running.",
  );
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
});
