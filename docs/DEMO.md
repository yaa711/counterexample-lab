# Find My Bug demo

The screenshots in the README come from the current local app. No outputs are mocked. The demo uses built-in functions so it can run without Docker.

## Walk through it

1. Start the app using the [README](../README.md#run-locally). Leave **Array sorting**, **Try an example**, and **Buggy example** selected.
2. Click **Find a failing case**. The example removes repeated numbers, so `[0, 0]` produces `[0]` instead of `[0, 0]`.
3. Open **A question to think about**. Compare the two outputs before looking at the working example.
4. Select **Show a working example** in **Check your fix**, then click **Check your fix**. The built-in `sorted(numbers)` function passes the displayed failure and the separate set of 100 unseen inputs.
5. To try your own change, select **Edit your fix**. Your draft starts from the failed source and requires Docker to run. Switching to the working example does not replace that draft.

The old failure and unseen-input counts are separate. Passing either set is not proof of correctness.

## Refresh the screenshots

Install the frontend dependencies and Playwright Chromium as described in the README, then run from the repository root:

```sh
npm --prefix frontend run build
LAB_REFRESH_DEMOS=1 LAB_TEST_PORT=8876 npm --prefix frontend run test:e2e -- demo-images.spec.ts
```

If using an installed Google Chrome instead of Playwright Chromium, add `LAB_BROWSER_CHANNEL=chrome`. Choose a free port if 8876 is already in use. The capture starts its own local server and stops it afterward.

The command checks actual results before saving:

- `images/workbench.png`: the starting page at desktop width.
- `images/check-fix.png`: the failure and successful working-example check.
- `images/mobile.png`: the same results at a 390-pixel viewport.

Run IDs vary between captures. Review all three images after regeneration. This documentation capture is opt-in; ordinary CI does not overwrite the screenshots.
