import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";

test("demo, reduction, prompts, repair and export preserve real evidence", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "Find the input that breaks your code.",
    }),
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
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
  ).toBeVisible();
  await expect(page.locator(".failing-example").first()).toContainText(
    "Your output",
  );
  await expect(page.getByLabel("Repair Python code")).toHaveValue(
    /sorted\(set/,
  );
  await expect(page.getByLabel("Reduction strategy")).not.toBeVisible();
  await page
    .getByText("Test details and how the input got smaller", { exact: true })
    .click();
  await expect(page.getByText("12 → 2", { exact: true })).toBeVisible();
  await expect(page.getByText("Local fixed point reached")).toBeVisible();
  await page
    .getByText("Copy feedback for an AI assistant (optional)", { exact: true })
    .click();
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
    .getByLabel("Repair Python code")
    .fill("def solve(numbers):\n    return sorted(numbers)\n");
  await page.getByRole("button", { name: "Show a working example" }).click();
  await page.getByRole("button", { name: "Edit your fix" }).click();
  await expect(page.getByLabel("Repair Python code")).toHaveValue(
    "def solve(numbers):\n    return sorted(numbers)\n",
  );
  await page.getByRole("button", { name: "Show a working example" }).click();
  await page
    .getByRole("button", { name: "Check your fix", exact: true })
    .click();
  await expect(
    page.getByText("No errors found in these tests · 100/100"),
  ).toBeVisible();
  await expect(
    page.getByText("Previous failing example: passed", { exact: true }),
  ).toBeVisible();
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export results" }).click();
  const downloaded = await pending;
  expect(downloaded.suggestedFilename()).toMatch(/^find-my-bug-.*\.json$/);
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
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "03 Maximum subarray" }).click();
  await page
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(page.locator(".failing-example").first()).toContainText(
    "Your output",
  );
  await page.getByLabel("Choose an example").selectOption("correct");
  await page
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("No errors found in these tests", { exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Your code", exact: true }).click();
  await page
    .getByRole("textbox", { name: "Candidate Python code" })
    .fill("def solve(numbers):\n    return 0");
  await expect(
    page.getByRole("button", { name: "Find a failing case", exact: false }),
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
    page.getByRole("heading", {
      name: "Find the input that breaks your code.",
    }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
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
    page.getByRole("heading", {
      name: "Find the input that breaks your code.",
    }),
  ).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
  await page.getByRole("button", { name: "How it works", exact: true }).click();
  await expect(
    page.getByRole("heading", {
      name: "A small input makes a bug easier to see.",
    }),
  ).toBeVisible();
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
  await page.getByRole("button", { name: "Try an example" }).click();
  await page.route("**/api/run", (route) =>
    route.fulfill({
      status: 409,
      json: { error: "An experiment is already running. Try again shortly." },
    }),
  );
  await page.getByRole("button", { name: "Find a failing case" }).click();
  await expect(page.getByRole("alert")).toContainText(
    "An experiment is already running.",
  );
  expect(await page.locator("body").innerText()).not.toMatch(
    /[\p{Script=Han}]/u,
  );
});

test("strategy, generator and rejected attempts match exported evidence", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByText("Advanced settings", { exact: true }).click();
  await page.getByLabel("Reduction strategy").selectOption("single");
  await page.getByLabel("Input generation").selectOption("evaluation");
  await page
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
  ).toBeVisible();
  await page
    .getByText("Test details and how the input got smaller", { exact: true })
    .click();
  await expect(page.getByTestId("recorded-settings")).toContainText(
    "Single deletion",
  );
  await expect(page.getByTestId("recorded-settings")).toContainText(
    "Evaluation",
  );
  await page.getByText(/^All reduction attempts/).click();
  await expect(page.locator(".attempt-list")).toBeVisible();
  await expect(page.locator(".attempt-list")).toContainText("accepted");
  await page.getByLabel("Reduction strategy").selectOption("block");
  await expect(page.getByTestId("recorded-settings")).toContainText(
    "Single deletion",
  );
  const pending = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export results" }).click();
  const download = await pending;
  const stream = await download.createReadStream();
  const chunks = [];
  for await (const chunk of stream!) chunks.push(chunk);
  const report = JSON.parse(Buffer.concat(chunks).toString());
  expect(report.strategy).toBe("single");
  expect(report.profile).toBe("evaluation");
  expect(report.candidate_calls).toBe(report.tested + report.shrink.calls);
  expect(
    report.shrink.attempts.filter(
      (a: { call: number | null }) => a.call !== null,
    ),
  ).toHaveLength(report.shrink.calls);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "../artifacts/comparison-mobile.png",
    fullPage: true,
  });
});

test("zero reduction budget retains original feedback without inventing reduced feedback", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByText("Advanced settings", { exact: true }).click();
  await page.getByLabel("Reduction budget").fill("0");
  await page
    .getByRole("button", { name: "Find a failing case", exact: false })
    .click();
  await expect(
    page.getByText("Found a failing case", { exact: true }),
  ).toBeVisible();
  await page
    .getByText("Copy feedback for an AI assistant (optional)", { exact: true })
    .click();
  await page
    .getByText("Test details and how the input got smaller", { exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Reduced input", exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("textbox", { name: "Repair prompt" }),
  ).toHaveValue(/Expected:/);
  await expect(page.getByText("Reduction not started")).toBeVisible();
});
