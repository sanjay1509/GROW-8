# Grow8 — Frontend & Backend QA Automation

**Project:** Grow8 (SDG 8 — Decent Work and Economic Growth)  
**QA coverage:** Playwright browser-based frontend testing + Pytest/FastAPI backend API testing  
**Latest recorded executions:** October 28, 2026  
**Status:** Both approved suites have been implemented and executed. **Six tests failed, and five backend scenarios were intentionally deferred.** Testing is complete for this execution cycle, but defect investigation and reruns remain outstanding.

> This is the **common QA README** for the two approved suites. All commands below are for **Windows PowerShell** and use **Docker Desktop**. They do **not** need `-ExecutionPolicy Bypass`, changes to application source, or a new `approved/` folder.

## 1. Testing results (latest uploaded reports)

| Layer | Approved cases | Passed | Failed | Skipped/deferred | Pass rate among executed cases |
|---|---:|---:|---:|---:|---:|
| Backend API — 15 endpoints | 237 | 231 | 1 | 5 | 99.57% (231/232) |
| Frontend UI — 5 pages | 62 | 57 | 5 | 0 | 91.94% (57/62) |
| **Combined** | **299** | **288** | **6** | **5** | **97.96% (288/294)** |

These results come from the **actual uploaded** `backend_report.html` (pytest-html) and `index.html` (Playwright), not from test discovery or anticipated behavior. A new run can produce different results. Previous uploaded reports are historical evidence and must not be treated as the results of a future run.

### Frontend scope and outcomes

| Page | Route | Smoke | Sanity | Regression | Total |
|---|---|---:|---:|---:|---:|
| Home | `/` | 2 | 2 | 5 | 9 |
| Browse Opportunities | `/opportunities` | 3 | 4 | 11 | 18 |
| Creator Dashboard | `/creator/dashboard` | 2 | 4 | 4 | 10 |
| My Opportunities | `/creator/opportunities` | 2 | 2 | 6 | 10 |
| Create Opportunity | `/creator/opportunities/create` | 3 | 4 | 8 | 15 |
| **Total** | | **12** | **16** | **34** | **62** |

The frontend tests use **Playwright + controlled/mocked API fixtures** to make UI states repeatable. They validate rendering, navigation, inputs, validation, UI-visible API payloads, error handling, and HTTP interception. **They are not an end-to-end proof that the live React frontend, FastAPI backend, and MySQL database work together.**

**Frontend failures in the uploaded run:**

| Case ID | Reported failure | Follow-up |
|---|---|---|
| `BRW-015` | The test expected the text `Deadline`; the details UI showed `Application deadline` | Check the locator/assertion against the agreed UI wording |
| `BRW-018` | Expected load-failure heading not found | Inspect network-mocking order and the actual error state |
| `MYOP-001` | Test expected one authenticated GET but captured two | Determine whether duplicate request is normal (e.g., development rendering) before treating as a product defect |
| `MYOP-005` | Test expected three cards before Refresh, but four were displayed | Fix test fixture expectation or application behavior after checking the intended data set |
| `MYOP-010` | View Opportunity navigated to `/creator/dashboard`, not a detail page | Missing creator opportunity-detail route is a likely application defect |

**All 16 frontend Sanity tests passed** in this run. Do not reclassify the five failures as passes until they have been fixed and rerun.

### Backend scope and outcomes

The backend suite covers **237 approved case IDs across 15 endpoints**, including Health, Login, Auth Me, Categories, Skills, Browse Opportunities, Creator Opportunities, Opportunity Detail/Create/Update/Publish, and Notifications. The available markers classify **23 Smoke, 15 Sanity, 194 Regression, and 5 deferred** cases. When running a marker-specific group, deferred cases are excluded; a complete run includes them as skipped.

- **Failure:** `AUTH-024` (null email or password). Evidence showed the test accidentally sent valid credentials rather than a null field, receiving HTTP 200 instead of the expected 422. **Fix the test helper/data setup and rerun before calling this a backend defect.**
- **Intentionally skipped:** `HLTH-002`, `HLTH-003`, `HLTH-004`, `HLTH-005`, and `HLTH-010`, because infrastructure-failure simulation is outside the approved scope.
- Backend tests exercise FastAPI with its test client, isolated MySQL test fixtures, and a fake event publisher where configured. They do **not** perform direct database assertions.

## 2. Project layout

The instructions assume you extracted both automation overlays into the **same `GROW-8` repository root**:

```text
GROW-8/
├── grow8-/                              # React frontend
├── grow8-backend/                       # FastAPI + Docker Compose
│   ├── .env                             # Local configuration (do not commit)
│   ├── docker-compose.yml
│   └── db/init/
└── qa/
    ├── README.md                        # This common README
    ├── Dockerfile                       # Frontend Playwright Docker image
    ├── package.json
    ├── playwright.config.mjs
    ├── scripts/run-layer.mjs
    ├── frontend/
    │   ├── helpers/
    │   ├── test-cases-62.json
    │   └── tests/
    │       ├── smoke/
    │       ├── sanity/
    │       └── regression/
    ├── backend/
    │   ├── run-backend.ps1              # Optional; not required below
    │   ├── tests/
    │   │   ├── cases.json
    │   │   ├── conftest.py
    │   │   └── test_0*.py
    │   └── reports/                     # Generated backend reports
    ├── reports/
    │   └── frontend/                    # Generated Playwright reports (ignored by Git)
    └── test-artifacts/
        └── 2026-10-28/                  # Archived execution evidence (tracked in Git)
            ├── frontend/
            │   ├── index.html
            │   ├── Grow8_Frontend_Execution_Results.xlsx
            │   └── Grow8_Frontend_Approved_Test_Matrix.xlsx
            └── backend/
                ├── backend_report.html
                └── Grow8_Backend_Results.xlsx
```

The directory may also contain older QA experiments. The frontend Playwright configuration selects only the `*.grow8-62.spec.js` files for the approved 62-case run; the backend commands below target `tests/backend_qa`, mapped from `qa/backend/tests`.

## 3. Prerequisites

1. **Docker Desktop** is installed and running in Linux-container mode.
2. Run commands in a **Windows PowerShell** terminal at the repository root unless a step specifies otherwise.
3. The frontend repository has `grow8-/package.json` and `grow8-/package-lock.json` (required by the frontend Dockerfile).
4. The frontend automation files exist under `qa/frontend`, and `qa/Dockerfile`, `qa/package.json`, and `qa/playwright.config.mjs` are present.
5. For backend testing, configure `grow8-backend/.env` using the project's `.env.example` as a starting point. **Do not commit credentials.**
6. The backend MySQL service must have a **separate `grow8_test` database**, with appropriate test-user privileges. The backend's `db/init/003_test_database.sh` creates it only when initializing a **new** MySQL volume. Existing volumes may need a safe, separate setup. **Backend tests reset and reseed `grow8_test` repeatedly; never run them against shared, development, or production data.**

Check Docker and enter the project:

```powershell
cd C:\Users\aparn\Downloads\GROW-8

docker version

docker compose version
```

## 4. Frontend — build and run all 62 Playwright tests

The frontend Docker image **starts Vite inside its own container**, so you do not need to start the backend to execute this mocked-API UI suite.

**Build the frontend QA image** from the `GROW-8` root:

```powershell
New-Item -ItemType Directory -Force .\qa\reports | Out-Null

docker build -f qa/Dockerfile -t grow8-qa:62 .
```

**Run each test level independently:**

```powershell
# 12 Smoke cases
docker run --rm -v "${PWD}\qa\reports:/workspace/qa/reports" grow8-qa:62 npm run test:frontend:smoke

# 16 Sanity cases
docker run --rm -v "${PWD}\qa\reports:/workspace/qa/reports" grow8-qa:62 npm run test:frontend:sanity

# 34 Regression cases
docker run --rm -v "${PWD}\qa\reports:/workspace/qa/reports" grow8-qa:62 npm run test:frontend:regression
```

**Or run all 62 in one execution:**

```powershell
docker run --rm -v "${PWD}\qa\reports:/workspace/qa/reports" grow8-qa:62 npm run test:frontend:all
```

These commands write **timestamped** Playwright results to your Windows folder. A test failure can cause Docker to exit with code 1 even when the report has been written successfully.

**Open the latest frontend HTML report (robust path resolution):**

```powershell
$report = Get-ChildItem .\qa\reports\frontend\all -Recurse -Filter index.html |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if ($report) { Start-Process $report.FullName } else { Write-Host 'No frontend HTML report found.' }
```

To view an individual run, replace `all` with `smoke`, `sanity`, or `regression`. Reports are generally stored at:

```text
qa/reports/frontend/<suite>/<timestamped-run-id>/html/index.html
qa/reports/frontend/<suite>/<timestamped-run-id>/junit.xml
qa/reports/frontend/<suite>/<timestamped-run-id>/artifacts/
qa/reports/frontend/<suite>/latest.json
```

**Note:** `latest.json` contains a path relative to the `qa` folder (such as `reports/frontend/all/...`). Do not resolve this relative to the repository root without adding `qa/`; otherwise PowerShell may report that `index.html` cannot be found. The `Get-ChildItem` command above avoids that issue entirely.

## 5. Backend — run all 237 approved API tests with Docker Compose

These commands invoke **Pytest in the existing FastAPI `api` service image**. The tests are mounted into the temporary container, so the original FastAPI files and `docker-compose.yml` remain unchanged.

**Start backend dependencies and build the API image:**

```powershell
cd C:\Users\aparn\Downloads\GROW-8\grow8-backend

docker compose up -d mysql rabbitmq

docker compose build api

docker compose ps
```

Wait until MySQL and RabbitMQ show `healthy` before running the tests. Docker Compose's `api` service also declares those healthy-service dependencies.

**Set up the paths and the output folder, still inside `grow8-backend`:**

```powershell
$tests = (Resolve-Path ..\qa\backend\tests).Path
$init = (Resolve-Path .\db\init).Path
$reports = Join-Path (Resolve-Path ..).Path 'qa\backend\reports'

New-Item -ItemType Directory -Force -Path $reports | Out-Null
```

**Run all 237 approved cases:**

```powershell
docker compose run --rm -u root `
  -v "${tests}:/app/api/tests/backend_qa:ro" `
  -v "${init}:/app/db/init:ro" `
  -v "${reports}:/app/api/tests/reports" `
  api sh -c 'python -m pip install -q --disable-pip-version-check -r requirements-dev.txt pytest-html==4.1.1 && python -m pytest tests/backend_qa --rootdir=/app/api -v -ra --tb=short --html=tests/reports/backend_report.html --self-contained-html --junitxml=tests/reports/backend_junit.xml'
```

This complete run should **collect 237 approved IDs**, including five deferred Health cases marked `Skipped`. The pass/fail counts are determined by the new execution; do not assume they will match the previously uploaded report.

**Run just one suite:** use the command above, adding one marker selection **inside the final quoted string**, immediately after `tests/backend_qa`:

```text
-m smoke        # 23 active cases
-m sanity       # 15 active cases
-m regression   # 194 active cases
```

For example, the Pytest portion of the command would become:

```text
python -m pytest tests/backend_qa -m smoke --rootdir=/app/api -v -ra --tb=short --html=tests/reports/backend_report.html --self-contained-html --junitxml=tests/reports/backend_junit.xml
```

For one backend case, use `-k AUTH-024` (or another approved test ID) in place of the `-m` marker. You can also use `qa/backend/run-backend.ps1` **if PowerShell permits script execution**; none of the direct Docker commands requires that script or an execution-policy bypass.

**Open the backend HTML report:**

```powershell
Start-Process ..\qa\backend\reports\backend_report.html
```

Backend outputs are regenerated on each run:

```text
qa/backend/reports/backend_report.html
qa/backend/reports/backend_junit.xml
```

Unlike frontend reports, the backend report **is overwritten** each time you run Smoke, Sanity, Regression, or All. Rename or copy it after each run if you want to retain all four results.

## 6. Recommended full testing sequence (both layers)

From `GROW-8`:

1. Build the frontend image (`docker build -f qa/Dockerfile -t grow8-qa:62 .`).
2. Run frontend **Smoke → Sanity → Regression → All** using the commands in §4. This checks the five React pages using controlled mock API data.
3. Switch to `grow8-backend`, start MySQL/RabbitMQ, build the API image, and verify the isolated test database as described in §5.
4. Run the backend approved Pytest suite. For separate classification reports, run **Smoke → Sanity → Regression** first, saving a copy of `backend_report.html` after each; then run All.
5. Review failure reports and screenshots, fix verified product defects/test harness issues, and **rerun** the affected cases. Keep historical and rerun results clearly labeled.

**These are two separate runners.** `npm run test:frontend:all` does not run the Python backend suite. Running a frontend Docker container and a backend Compose test container is the supported way to regenerate both result sets without changing application source.

## 7. Clean reports before pushing to GitHub

Keep automation code; generated reports are safe to regenerate. From the `GROW-8` root:

```powershell
Remove-Item .\qa\reports -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item .\qa\backend\reports -Recurse -Force -ErrorAction SilentlyContinue
```

Add these exclusions to the **repository root `.gitignore`**:

```gitignore
# QA runtime outputs (not test source)
/qa/reports/
/qa/backend/reports/
/qa/node_modules/
**/.pytest_cache/
**/__pycache__/
```

If reports were **already tracked**, `.gitignore` alone will not remove them from Git history or tracking. You can stop tracking their contents while leaving the source tests intact:

```powershell
git rm -r --cached --ignore-unmatch qa/reports qa/backend/reports
```

Do not delete `qa/Dockerfile`, `qa/package.json`, `qa/playwright.config.mjs`, `qa/frontend/tests`, `qa/frontend/helpers`, `qa/backend/tests`, or backend `db/init` scripts. **Do not run `docker compose down -v`** merely to clean testing outputs: `-v` removes Compose-managed volumes, including MySQL data.

## 8. Troubleshooting

| Symptom | What to check |
|---|---|
| `qa/Dockerfile` not found | Confirm the corrected frontend automation overlay was extracted into the `GROW-8` root |
| Docker build cannot find `grow8-/package-lock.json` | Build from the root; verify the existing React app files are present |
| Frontend `Start-Process` cannot find `index.html` | Use the recursive `Get-ChildItem` command in §4; report paths in `latest.json` are relative to `qa` |
| Frontend tests fail while browser report exists | Inspect Playwright HTML for assertion, route, fixture, or rendering failures; a failing suite normally returns a nonzero exit code |
| `grow8_test` unknown or access denied | Verify database initialization and grants; avoid running against development/production data |
| `fixture 'client' not found` | Do not add a local `pytest.ini` under `qa/backend/tests`; run from `/app/api` so Pytest inherits the existing application `api/tests/conftest.py` |
| Backend connection/health failure | Check `docker compose ps`, `.env`, MySQL/RabbitMQ health, and `docker compose logs` |
| Missing backend HTML report | Verify the `qa/backend/reports` volume mount and that the container could write files |
| PowerShell refuses `.ps1` | Use the **direct Docker commands** above; they require no execution-policy change |

## 9. Evidence and test ownership

- **Frontend source of truth:** `qa/frontend/test-cases-62.json` and `qa/frontend/tests/**/*.grow8-62.spec.js`.
- **Backend source of truth:** `qa/backend/tests/cases.json` and `qa/backend/tests/test_0*.py`.
- **Current-run reports:** Generated under `qa/reports/frontend/` and `qa/backend/reports/`; these can be deleted or ignored because they regenerate. **Historical execution evidence:** A snapshot of the October 28, 2026 HTML reports and workbooks is available in [`qa/test-artifacts/2026-10-28/`](test-artifacts/2026-10-28/README.md) and can be committed as evidence.
- **Test workbooks:** The separate approved-case Excel workbooks summarize the October 28, 2026 results. Reconcile or regenerate their status fields from **new reports** after any rerun.
- **Known outstanding work:** `AUTH-024`, `BRW-015`, `BRW-018`, `MYOP-001`, `MYOP-005`, and `MYOP-010`. Five Health infrastructure scenarios remain intentionally deferred.

**Acceptance criterion for closure:** No unexplained failures in the active approved cases, all intended skips explicitly documented, and updated reports showing the results of the latest execution. The October 28 run demonstrates that both automation suites ran; it does **not** establish complete functional correctness or a fully green build.

## 10. Test artifacts and HTML execution reports (archived evidence)

The **October 28, 2026 testing artifacts are included with this README overlay** in `qa/test-artifacts/2026-10-28/`. These are historical outputs captured from actual frontend and backend runs—not claims that subsequent reruns have passed. The links below are relative to `qa/README.md` and work when the entire overlay is extracted into the repository root.

| Test layer | Archived HTML report | Excel test artifact | Recorded outcome |
|---|---|---|---|
| **Backend API** | [Open backend pytest-html report](test-artifacts/2026-10-28/backend/backend_report.html) | [Backend execution results (237 cases)](test-artifacts/2026-10-28/backend/Grow8_Backend_Results.xlsx) | 231 passed, 1 failed, 5 skipped |
| **Frontend UI** | [Open frontend Playwright HTML report](test-artifacts/2026-10-28/frontend/index.html) | [Frontend execution results (62 cases)](test-artifacts/2026-10-28/frontend/Grow8_Frontend_Execution_Results.xlsx) | 57 passed, 5 failed, 0 skipped |
| **Frontend approved test plan** | Not an execution report | [Original approved frontend test matrix](test-artifacts/2026-10-28/frontend/Grow8_Frontend_Approved_Test_Matrix.xlsx) | 62 approved cases (planning baseline) |

The execution workbooks contain test-level status and investigation notes. The HTML reports contain the captured test output available at the time of export. **Screenshot images, videos, and Playwright trace files were not supplied separately.** The archived frontend `index.html` includes embedded test-result data but cannot reconstruct any media that the original report referenced as external files. Do not present those attachments as included.

**Open the archived reports from the `GROW-8` root in PowerShell (no bypass required):**

```powershell
Start-Process .\qa\test-artifacts\2026-10-28\backend\backend_report.html
Start-Process .\qa\test-artifacts\2026-10-28\frontend\index.html
```
