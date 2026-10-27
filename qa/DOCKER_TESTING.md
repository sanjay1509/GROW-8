# Grow8 QA — Docker Test Execution (PowerShell)

This guide starts from `C:\Users\aparn\Downloads\GROW-8` on Windows. The existing application Docker Compose files are **not modified**. Keep your working `grow8-backend/.env` file; it was intentionally excluded from the cleaned archive. Restore it from your own backup before starting the backend.

## 1. Start application dependencies

```powershell
cd C:\Users\aparn\Downloads\GROW-8\grow8-backend
docker compose up -d --build
docker compose ps
```

Wait for MySQL and RabbitMQ to be healthy. Frontend browser tests also require the Grow8 frontend web server to be reachable; starting backend containers alone does not launch the frontend.

## 2. Python backend — 346-case matrix, HTML report

**Safety:** The existing Pytest fixtures reset `grow8_test`. Verify the database is isolated and is NOT your development or shared database before running. Keep `qa/backend/tests/qa_matrix/pytest.ini` absent; that file previously hid the parent `client` fixture.

From `GROW-8\grow8-backend`:

```powershell
# Verify one case before the full run
docker compose run --rm `
  -v "${PWD}\..\qa\backend\tests\qa_matrix:/app/api/tests/qa_matrix:ro" `
  api python -m pytest tests/qa_matrix -k "BE-HLTH-001" -v -x --tb=short
```

```powershell
# Full run, producing a standalone HTML report and JUnit XML
docker compose run --rm -u root `
  -v "${PWD}\..\qa\backend\tests\qa_matrix:/app/api/tests/qa_matrix:ro" `
  -v "${PWD}\..\qa\backend\reports:/app/api/tests/reports" `
  api sh -c 'python -m pip install -q pytest-html && python -m pytest tests/qa_matrix -v -ra --tb=short --html=tests/reports/backend-report.html --self-contained-html --junitxml=tests/reports/qa_matrix/junit.xml'
```

Open from `grow8-backend`:

```powershell
Start-Process ..\qa\backend\reports\backend-report.html
```

The HTML report shows test IDs, pass/fail/skip statuses, durations, and failure diagnostics. It does not currently record full HTTP response bodies for each passing test.

## 3. Playwright QA in Docker (frontend, backend HTTP, database)

The project already includes `qa/Dockerfile`. Build it **from the repository root**, because it copies both `grow8-` and `qa/`:

```powershell
cd C:\Users\aparn\Downloads\GROW-8
docker build -f qa/Dockerfile -t grow8-qa:local .
```

For backend and database tests, join the existing Compose network `grow8_default` (the Compose project name is `grow8`). Container-to-container URLs must use Docker service names, not `localhost`. The commands below assume the API is accessible as `http://api:8000`, and MySQL as `mysql:3306` from that network. Supply your actual test-only database credentials via environment variables; do not hard-code secrets in documentation.

```powershell
# Backend HTTP smoke tests, report persisted on Windows
docker run --rm --network grow8_default `
  -e API_URL=http://api:8000 `
  -v "${PWD}\qa\reports:/workspace/qa/reports" `
  grow8-qa:local npm run test:backend:smoke
```

```powershell
# Backend HTTP sanity / regression
docker run --rm --network grow8_default `
  -e API_URL=http://api:8000 `
  -v "${PWD}\qa\reports:/workspace/qa/reports" `
  grow8-qa:local npm run test:backend:sanity

docker run --rm --network grow8_default `
  -e API_URL=http://api:8000 `
  -v "${PWD}\qa\reports:/workspace/qa/reports" `
  grow8-qa:local npm run test:backend:regression
```

For database tests, supply `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME` from a dedicated **test** database. In PowerShell set `$env:DB_USER`, `$env:DB_PASSWORD`, and `$env:DB_NAME` to your own test credentials before executing:

```powershell
docker run --rm --network grow8_default `
  -e DB_HOST=mysql -e DB_PORT=3306 `
  -e DB_USER=$env:DB_USER -e DB_PASSWORD=$env:DB_PASSWORD -e DB_NAME=$env:DB_NAME `
  -v "${PWD}\qa\reports:/workspace/qa/reports" `
  grow8-qa:local npm run test:database:smoke
```

Replace `test:database:smoke` with `test:database:sanity` or `test:database:regression` for those suites.

For frontend tests, **start the frontend web server first**. The correct `BASE_URL`/frontend environment variable depends on the checked-in Playwright configuration. Use a browser-reachable frontend address from inside the QA container (e.g. a frontend container service name if it shares `grow8_default`, or `http://host.docker.internal:<frontend-port>` if the frontend runs on Windows). Do not assume `localhost` inside Docker points to your Windows host. Example, replacing `<frontend-port>` with the actual port and setting the URL variable required by your Playwright config:

```powershell
docker run --rm --network grow8_default `
  -e BASE_URL=http://host.docker.internal:<frontend-port> `
  -v "${PWD}\qa\reports:/workspace/qa/reports" `
  grow8-qa:local npm run test:frontend:smoke
```

Use `test:frontend:sanity` and `test:frontend:regression` for the other frontend suites. Confirm the actual configured URL variable before running; the `BASE_URL` line above is illustrative.

## 4. HTML reports

Playwright saves per-run HTML reports under `qa/reports/<layer>/<suite>/<run-id>/html/index.html`. Python Pytest writes `qa/backend/reports/backend-report.html`. Run the tests to generate fresh reports; old reports were intentionally removed from the clean archive. Open HTML files directly in a browser on Windows.

## 5. Troubleshooting

- `no configuration file provided`: run `docker compose` from `grow8-backend`, not repository root.
- `fixture 'client' not found`: remove/disable the nested `qa_matrix/pytest.ini`; it interferes with parent fixture discovery.
- `pytest-html` option `--html` unrecognized: install `pytest-html` in the one-off container as shown above.
- Connection refused: check `docker compose ps`, container network, and the API/frontend URL. Inside Docker, `localhost` is the QA container itself.
- Missing database: check the dedicated test database and credentials; do not point tests at production/development data.
- No report: ensure the host reports folder is bind-mounted to `/workspace/qa/reports` (Playwright) or `/app/api/tests/reports` (Pytest).
