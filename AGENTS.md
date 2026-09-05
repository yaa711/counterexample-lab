# Counterexample Lab agent instructions

This is an English-only local research workbench, not a public hosted service. Do not add Chinese UI or a language switcher; the user explicitly canceled bilingual UI. Chinese learning documentation may remain. Continue from existing code; preserve the distinction between trusted teaching examples and arbitrary user Python.

## Commands

- Backend: `python3 -m backend.server` (127.0.0.1:8765).
- Install frontend: `npm --prefix frontend ci`.
- Frontend development: `npm --prefix frontend run dev` (127.0.0.1:5173).
- Build/type check: `npm --prefix frontend run build`.
- Backend tests: `python3 -m unittest discover -s tests -v`.
- Browser tests: `cd frontend && npm run test:e2e` after building and installing Playwright Chromium; optionally set `LAB_BROWSER_CHANNEL=chrome`.
- Docker image: `docker build -t counterexample-lab-runner:1 runner`.
- Docker integration: `LAB_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v`.
- Release ZIP: `python3 scripts/package.py` after staging source and building.

## Ownership boundaries

- `backend/tasks.py`: contracts, independent oracles, display source and matching fixed demo functions.
- `backend/engine.py`: deterministic generation, outcome classification, strict decreasing reduction, held-out verification. Keep this independent of HTTP and React.
- `backend/execution.py`: only adapter permitted to run candidate source, exclusively through Docker.
- `runner/worker.py`: container entrypoint; contains exec by design. Never execute it with user input on the host.
- `backend/reports.py`: provenance and feedback prompts. `backend/server.py`: validated HTTP transport and bounded in-memory reports.
- `frontend/src`: display returned evidence; never invent results or mutate past report source.

## Invariants

1. No host eval/exec/subprocess Python fallback for arbitrary candidate code. Docker unavailability is an explicit unavailable state.
2. Fixed demo source is for display; the backend runs only the fixed registry. If demo source changes, update its matching callable and tests.
3. Expected outputs are computed outside the candidate container. Do not give the candidate expected answers.
4. Accepted shrink steps preserve task validity, repeat the wrong answer and strictly reduce the defined measure. Never label the result globally minimal.
5. Runtime failures, bad output and infrastructure failures are distinct from wrong answers. Finite tests passing is not proof.
6. Verification excludes every input exposed during search/reduction and records its independent seed. Never advertise repeated verification as a fresh held-out set.
7. No credentials, dependencies, private paths or fabricated model results in releases. Reports may contain user code; export is explicit and local.
8. React state should retain actual run evidence separately from editable drafts; calculate derived UI state during rendering and use handlers for user actions.

## Validation expectations

Run relevant tests for changed modules and the frontend build when UI/types change. Real Docker checks require an installed daemon/image; report skipped tests honestly, never imply they ran. Inspect desktop/mobile UI when changing layout. Update `docs/VALIDATION.md` with actual evidence and limits, not assumptions.

Use the checked-in lockfile. No external skills are required to run this project. The original design is in `docs/superpowers/specs/`; the approved implementation plan is in `docs/superpowers/plans/`.
