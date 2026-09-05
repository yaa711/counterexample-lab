# Counterexample Lab Implementation Plan

> **For agentic workers:** Use executing-plans to implement this plan task-by-task, with verification checkpoints. The user has authorized implementation; execute in this session.

**Goal:** Deliver a reproducible local counterexample workbench, usable from Codex and distributable as a Git repository and ZIP.

**Architecture:** A React workbench calls a loopback-only Python JSON API. Pure task/generator/reducer modules run trusted demos; a separate Docker adapter handles all pasted code. Reference answers stay outside the runner.

**Tech Stack:** React, TypeScript, Vite, Python 3.11+ standard library, Docker, unittest, Playwright for UI checks.

---

## Task 1: Pure testing engine

Files: backend/tasks.py (contracts/oracles/examples), backend/engine.py (deterministic generation, comparison, reduction, verification), tests/test_engine.py.

- [x] Write and run regression tests before implementing: `python3 -m unittest discover -s tests -v` must initially fail on imports.
- [x] Implement three contracts: sort(numbers), first_index(numbers,target), max_subarray(numbers). Use Python sorted, linear search and brute-force subarray enumeration as independent oracles. The selected slice-and-sum implementation is O(n³), corrected during the interview-comment review.
- [x] Generate bounded inputs with random.Random(seed), include empty/duplicate/negative boundaries, deduplicate cases, preserve task preconditions.
- [x] Differential result types: passed, wrong_answer, exception, timeout, invalid_output, infrastructure_error.
- [x] Shrink only stable wrong answers using chunk deletion then one-item deletion then values toward zero. Each accepted input must lower `(length, sum(abs(values))+abs(target))`. Reject invalid inputs and non-wrong-answer results.
- [x] Record each evaluation, accepted trajectory, budget exhaustion, SHA-256 code digest and independent verification seed.
- [x] Tests must assert replay equality, strictly decreasing trajectory, valid inputs, persistent failures, exact output types, exhausted budgets, correct examples passing, and no overlap between discovery and held-out tests.

## Task 2: Isolated execution and API

Files: backend/execution.py, backend/server.py, runner/worker.py, runner/Dockerfile, tests/test_execution.py, tests/test_api.py.

- [x] Docker command uses `--network none --read-only --cap-drop ALL --security-opt no-new-privileges --pids-limit 32 --memory 128m --cpus 0.5 --user 65534:65534`, no host mounts; stdin JSON protocol.
- [x] Wall timeout and bounded stdout/stderr must kill and remove the unique container in finally. Startup failure is infrastructure_error. Candidate failures never become infrastructure failures by default.
- [x] Without Docker/image, reject custom requests; built-in demos use a fixed callable registry only.
- [x] API routes: GET /api/health, GET /api/tasks, POST /api/run, POST /api/verify. Validate request types/ranges and restrict Host/Origin and body size. Serve built frontend from frontend/dist for one-command production use.
- [x] Hold immutable discovery reports in a bounded, expiring in-memory store; verification references run ID. Never trust client-supplied reports for validation.
- [x] Test malformed JSON, forbidden origins/hosts, disabled custom code, unknown tasks, stale runs, timeout flags and cleanup. Docker integration tests skip explicitly if unavailable.

## Task 3: React workbench

Files: frontend/package.json, frontend/vite.config.ts, frontend/src/{App,Workbench,Results}.tsx, frontend/src/{api,types}.ts, frontend/src/styles.css.

- [x] Build a responsive English-only interface (per final user instruction) with task selection, source editor, seed/budgets, demo/custom mode, run state, original/reduced comparison, trajectory, repair prompts, held-out validation and JSON download.
- [x] Fetch health/tasks together. Use event handlers for user actions; derive display values from reports. Disable duplicate submissions and keep errors actionable.
- [x] Keep candidate drafts separate from immutable run evidence. A run always labels the source it actually executed. Custom mode never runs edited text as a demo.
- [x] Compile with strict TypeScript: `npm --prefix frontend run build`.
- [x] Browser checks: demo → failure → reduction → prompt → export → trusted corrected sample verification; unavailable Docker message; responsive 390px viewport.

## Task 4: Handoff and validation

Files: README.md, AGENTS.md, docs/LEARNING.zh-CN.md, docs/EXPERIMENTS.md, scripts/{dev.py,package.py}, .gitignore, .github/workflows/ci.yml.

- [x] Document Python/Node requirements, `npm --prefix frontend ci`, `npm --prefix frontend run build`, `python3 -m backend.server`; optional Docker build command.
- [x] Explain finite-test limits, deletion minimality vs global minima, manual model experiments, Docker threat boundary and demo provenance.
- [x] Run full unittest suite and production build once; broaden only for failures or changed code.
- [x] Run API/browser verification, inspect screenshot, record actual results and skipped Docker execution.
- [x] Create source ZIP excluding .git, node_modules, bytecode, local outputs and secrets; include lockfile and AGENTS.md. Commit code with a project-local Codex author, no global Git changes and no remote publishing.

## Review

All approved spec sections map to tasks above. No external model credential, public deployment or unapproved account action is required. Local HTTP uses Python standard library to keep backend installation dependency-free. Current host lacks Docker; its integration tests will be delivered but reported as skipped here.

## Completion notes

The user changed UI scope to English only during implementation; this is applied to UI, backend feedback, reduction steps and model prompts. Core tests, production build and browser checks pass. Actual Docker execution is intentionally recorded as unverified on this host, with its opt-in test delivered. No account publishing or remote CI run occurred.

Follow-up: after the user installed Docker, the image was built and all 28 backend tests passed, including six real Docker integration tests. Docker is no longer unverified on this host; see the updated validation record.
