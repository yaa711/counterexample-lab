# Counterexample Lab

**Find a failing input. Make it smaller. Understand why the code is wrong.**

An English-language local research workbench for differential testing and counterexample reduction, built with React, TypeScript and Python. It supports a complete manual LLM repair experiment: test a candidate, reduce its failure, generate controlled feedback prompts, validate a repair on held-out inputs, and export the evidence.

![Counterexample Lab workbench](docs/images/workbench.png)

Optional Chinese learning guides: [从这里开始](docs/LEARNING.zh-CN.md) · [面试讲解练习](docs/INTERVIEW.zh-CN.md) · [Experiment protocol](docs/EXPERIMENTS.md) · [Validation record](docs/VALIDATION.md)

## Quick start

Requirements: **Python 3.11+**. To build or develop the frontend, use **Node.js 22.12+ and npm**. Docker is optional for trusted built-in examples and required for all pasted code.

If you downloaded the release ZIP, it includes `frontend/dist`. From the extracted `counterexample-lab` folder:

```sh
python3 -m backend.server
```

Open **http://127.0.0.1:8765**. On Windows, use `python` instead of `python3` if that is your Python command. The backend has no third-party Python dependencies. Stop it with Ctrl+C.

If you cloned the source repository, build the frontend first:

```sh
npm --prefix frontend ci
npm --prefix frontend run build
python3 -m backend.server
```

### Open in Codex

Use the extracted project folder as your local workspace. `AGENTS.md` contains the structure, commands and project invariants so a coding agent can continue from the current implementation. No personal skills, absolute developer paths, API keys or account connections are required.

The local working copy is already a Git repository. The ZIP deliberately omits `.git`; initialize a new repository if you want separate history:

```sh
git init -b main
git add .
git commit -m "Initial counterexample lab project"
```

No GitHub remote is configured and nothing has been published to an account.

## Try the complete workflow

1. Choose **Array sorting**, keep **Built-in demo → Buggy example**, and click **Run experiment**.
2. The real test catches a duplicate-removal bug. The reducer turns the longer failing array into a small witness such as `[0, 0]`.
3. Inspect expected/actual outputs and each accepted shrinking step.
4. Copy one of three feedback prompts into a separate model conversation. This app does not call a model automatically.
5. Use **Correct demo** to exercise held-out validation without Docker. This runs a fixed known function; it is not an AI-generated repair.
6. For your own candidate/repair code, enable the Docker runner below.
7. Click **Export experiment** to save the original source, source hash, seed, tested cases, reduction trajectory, prompts, and current verification result.

Switching task clears its current UI result. Reports are held in memory (latest 24, up to one hour); restart or expiration invalidates repair verification, so export evidence before leaving. Exported JSON is an audit artifact; this version does not import reports.

## Supported Python contracts

| Task | Function | Contract |
| --- | --- | --- |
| Sorting | `solve(numbers)` | Return an ascending integer list preserving duplicates; empty input allowed. |
| First index | `solve(numbers, target)` | Input is sorted; return the first matching index, or `-1`. |
| Maximum subarray | `solve(numbers)` | Return the maximum sum of a **non-empty** contiguous subarray; input is non-empty. |

Inputs use integer arrays of length up to 16, values from -12 through 12, plus specified boundary cases. Output comparisons are exact. Booleans are not accepted as integer results. Inputs are copied before every evaluation. A trusted oracle computes expected values outside the candidate process.

Built-in bugs are hand-authored teaching examples, **not model benchmark results**. They deliberately appear in early boundary cases so the tool can be demonstrated immediately. Do not use their discovery rate as evidence about LLMs.

## Run your own code with Docker

Install/start Docker, then build the local execution image:

```sh
docker build -t counterexample-lab-runner:1 runner
```

In the workbench, choose **Your code**, click **Check again**, and paste a complete Python `solve` implementation. Imports from the Python standard library are available; third-party packages are not included. Candidate function parameters must match the selected contract. Image builds need network access; candidate execution has networking disabled and never pulls an image automatically.

Each candidate evaluation uses a separate container with:

- No network, no host filesystem mounts, no Docker socket access.
- A read-only filesystem, non-root user, dropped capabilities, no-new-privileges.
- 128 MiB memory, 0.5 CPU, 32 processes, 2 CPU-seconds within the worker and a 6-second host wall timeout.
- Capped standard output/error, a JSON-only protocol, and container cleanup in `finally`.

The Docker adapter uses Unix pipe polling: use macOS, Linux, or WSL2 for custom execution. Trusted demos and the local UI can also run under native Windows Python.

The host never evaluates pasted source. If Docker or the image is unavailable, custom execution fails closed; only fixed trusted demo functions remain available. Do not invoke `runner/worker.py` directly on the host with untrusted input.

This is a **personal loopback-only development tool**, not a hardened public multi-tenant code-execution service. Do not expose the API on a public address. Docker shares the host kernel; a future public service needs a stronger isolation and operations design. If the daemon itself becomes unreachable during cleanup, inspect `docker ps -a --filter name=counterexample-` after recovery and remove leftover containers.

## How the engine works

`backend/tasks.py` defines contracts, oracles and a fixed trusted demo registry. `backend/engine.py` generates repeatable tests, compares outputs, and reduces stable wrong answers. Chunk deletion is followed by single-element deletion and value simplification. Every accepted change preserves the contract and strictly reduces `(array length, sum of absolute values + absolute target)`.

The original wrong answer is checked twice more; proposed reductions must fail consistently in two checks. A local fixed point is relative to these supported transformations. It is **not a globally smallest counterexample**. Exhausted budgets, time limits, unstable results and runtime/infrastructure failures are reported separately. A run has an approximately 50-second orchestration budget; an in-flight container evaluation/cleanup can extend it slightly.

Repair verification uses a derived, distinct seed and excludes all discovery/reduction inputs. It reports actual tested/passed counts and overlap. A second verification on the same run reuses the same held-out set: do not repeatedly tune against it. Passing finite tests is not a correctness proof.

## Development and tests

Two-terminal development:

```sh
# Terminal 1, repository root
python3 -m backend.server
```

```sh
# Terminal 2, repository root
npm --prefix frontend ci
npm --prefix frontend run dev
```

Open http://127.0.0.1:5173. Or run `python3 scripts/dev.py` after installing frontend dependencies to start both services together.

```sh
# Backend tests (requires permission to bind a temporary loopback port)
python3 -m unittest discover -s tests -v

# Type checking + production build
npm --prefix frontend run build

# Browser tests (build first; starts backend if not already running)
cd frontend
npx playwright install chromium
npm run test:e2e
```

If Chrome is already installed, `LAB_BROWSER_CHANNEL=chrome npm run test:e2e` can use it instead. Browser tests launch a separate headless session, not your regular browser profile.

```sh
# Opt-in real Docker integration tests, from repository root
LAB_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v

# Package tracked source + built frontend, omitting Git metadata and dependencies
python3 scripts/package.py
```

The source ZIP is written to `artifacts/counterexample-lab.zip`. The packager refuses a missing frontend build. It includes tracked source only, so commit or stage new source files before packaging.

## Project map

```text
backend/       Contracts, generation, shrinking, provenance, Docker adapter, HTTP API
frontend/      React workbench, types, styles, browser tests, locked dependencies
runner/        Container-only candidate worker and Dockerfile
tests/         Engine, API and execution-boundary regression tests
scripts/       Development launcher and portable release packager
docs/          Learning guide, methodology, design, implementation and validation notes
AGENTS.md      Instructions for continuing the project with a coding agent
```

## What this release does not claim

It does not train a model, automatically repair code, demonstrate a novel research result, prove arbitrary Python code correct, or provide a public sandbox. It provides a working experimental instrument and a clear next research question: **does reduced feedback improve repair on unseen tests compared with full feedback?**

Study multiple independent candidate programs and feedback conditions before making that claim. See `docs/EXPERIMENTS.md` for an honest experimental protocol.

Implementation references: [Vite guide](https://vite.dev/guide/), [Docker execution controls](https://docs.docker.com/engine/containers/run/). React implementation follows the user-selected Vercel React best-practices skill; no runtime dependency on the skill is introduced.
