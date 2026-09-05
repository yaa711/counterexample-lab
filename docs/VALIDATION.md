# Validation record

Date: 2026-09-05. Local environment: macOS, Python 3.13.1, Node 26.8.1, Chrome headless through Playwright 1.63.0.

## Completed

- **Backend, after Docker installation:** **28 tests passed, zero skipped** using `LAB_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v` (20.6 seconds). Covers the pure engine, API and execution controls, including six real Docker integration tests detailed below.
- **Frontend:** strict TypeScript check and Vite production build passed. Current compiled application is approximately 216 kB JavaScript and 22 kB CSS before compression.
- **Browser:** **4 tests passed**; the complete English workbench flow passed against the real Python service. Verified initial empty state, actual failure/reduction, feedback conditions, 100-input repair verification, JSON export, all task selections, correct-example behavior, disabled custom execution without Docker, and a 390px mobile viewport without horizontal overflow. An additional regression check covers English-only UI, guide and error feedback.
- **Export content:** parsed the actual browser download and verified the reduced sorting witness `[0, 0]`, repair result `100/100`, and zero overlap with discovery/reduction inputs.
- **Visual QA:** inspected generated desktop and mobile screenshots, improved explanatory text contrast, and retained a real desktop screenshot in `docs/images/workbench.png`.
- **Python syntax:** backend, worker, launcher, packager and tests compiled successfully. Compilation does not execute candidate code.

## Real Docker follow-up

Docker Desktop 4.89.0 / Engine 29.7.2 is now installed and running on this host. The runner image was built from Python 3.13-slim. Six integration tests verified:

- Normal results, candidate exceptions and termination of a CPU-bound infinite loop.
- The six-second wall timeout for a sleeping candidate.
- Rejection of an output flood by the host output cap.
- Failure of a 256 MiB allocation under the 128 MiB memory limit.
- Non-root UID, read-only application filesystem, no external route to a TEST-NET address, zero effective capabilities, no-new-privileges and the worker CPU limit.
- Real sorting-code discovery, reduction to `[0, 0]`, and **12/12 held-out repair tests**, with zero overlap.

Each integration test confirms removal of the exact containers it created. An initial assertion incorrectly expected `/sys/class/net` to list only `lo`; inactive virtual interfaces were also visible. The corrected test checks the actual property, an unreachable external route, instead of a platform-specific interface list.

These are verified controls, not proof of a complete public multi-tenant security boundary. Repeat with:

```sh
docker build -t counterexample-lab-runner:1 runner
LAB_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v
```

The checked-in GitHub Actions workflow also includes a Docker stage, but it has not run on GitHub and no remote CI success is claimed.

No real model-repair experiment has been performed. All displayed demo candidates are explicitly hand-authored teaching examples. Correct-example validation proves the application workflow on these tests, not a research finding about model performance.

## Release checks

The release archive includes tracked source plus the compiled frontend. It excludes Git metadata, dependency folders, Python caches and local experiment outputs. Rebuild after source changes before repackaging. Detailed validation of the final archive is recorded in the delivery message.
