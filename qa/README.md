# Grow8 Quality Assurance

This folder contains three independent automated testing layers. Application source and Docker Compose files are unchanged.

## Active test suites

- **Frontend:** Playwright UI smoke, sanity, and regression tests under `frontend/tests/`. The UI suites use mocked API responses; full-page screenshots are attached for executed tests.
- **Backend (Playwright):** HTTP smoke, sanity, and regression tests under `backend/tests/{smoke,sanity,regression}/` (run with the Node QA runner).
- **Backend (Python):** A separate **346-case** parametrized Pytest matrix under `backend/tests/qa_matrix/`. It uses fixtures in `grow8-backend/api/tests/conftest.py` and requires the isolated `grow8_test` database. Some scenarios may be intentionally skipped.
- **Database:** Read-only MySQL smoke, sanity, and regression tests under `database/tests/`.

## Install the Node QA runner (PowerShell)

From the repository root:

```powershell
cd .\grow8-
npm ci
cd ..\qa
npm install
npx playwright install chromium
```

Start backend services as needed:

```powershell
cd ..\grow8-backend
docker compose up -d --build
cd ..\qa
```

Run a Playwright suite, for example:

```powershell
npm run test:frontend:smoke
npm run test:frontend:sanity
npm run test:frontend:regression
npm run report:frontend:regression
```

Equivalent commands: `test:backend:<suite>`, `test:database:<suite>`, and `report:<layer>:<suite>`, where `<suite>` is `smoke`, `sanity`, or `regression`. For backend API tests, set `API_URL` to the running service. For database tests, configure `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` for a safe local test environment.

## Run the Python backend matrix with HTML output

**Warning:** The existing `seeded_db` fixture resets `grow8_test`. Verify it is isolated before running; do not point it at a development or shared database.

From `GROW-8\grow8-backend` in PowerShell:

```powershell
docker compose run --rm -u root `
  -v "${PWD}\..\qa\backend\tests\qa_matrix:/app/api/tests/qa_matrix:ro" `
  -v "${PWD}\..\qa\backend\reports:/app/api/tests/reports" `
  api sh -c 'python -m pip install -q pytest-html && python -m pytest tests/qa_matrix -v -ra --tb=short --html=tests/reports/backend-report.html --self-contained-html --junitxml=tests/reports/qa_matrix/junit.xml'
```

Open `GROW-8\qa\backend\reports\backend-report.html`. The HTML contains case IDs, statuses, durations and failure diagnostics. **Passing tests do not currently log full HTTP request/response bodies or a separate Actual Result field**; that would require additional test instrumentation.

The `pytest.ini` that previously lived inside `qa_matrix` was intentionally removed: it prevented discovery of the parent `client` fixture. The suite marks are registered in `grow8-backend/api/pyproject.toml` only if configured there; unknown-mark warnings do not invalidate execution.

## Generated reports and cleanup

The downloaded clean project intentionally **does not include historical reports, Excel result exports, caches or installed dependencies**. New reports are created on execution:

- Playwright: `qa/reports/<layer>/<suite>/<run-id>/html/index.html` (plus artifacts)
- Python Pytest: `qa/backend/reports/backend-report.html` and `qa/backend/reports/qa_matrix/junit.xml`

Reports are execution artifacts, not source code. Back up any report you need before replacing your local project folder. Do not claim a test passed unless an actual execution report shows it.

For frontend specifics see `frontend/NEW_AUTOMATION_README.md`. For Python backend see `backend/README.md`. For database see `database/README.md`.


## Docker: run all QA layers

For copy-paste PowerShell commands covering Docker build, frontend, backend (Playwright and Pytest), database, and HTML reports, see `DOCKER_TESTING.md`.
