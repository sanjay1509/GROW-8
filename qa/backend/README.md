# Grow8 backend QA

Two independent backend test runners are maintained; **do not mix their test folders**.

## Python / Pytest: 346-case backend matrix

- `tests/qa_matrix/test_backend_matrix.py` — parametrized test implementation
- `tests/qa_matrix/cases.json` — scenario definitions and case IDs
- Fixtures come from `grow8-backend/api/tests/conftest.py` inside the API container.
- **Do not restore `tests/qa_matrix/pytest.ini`**: a local configuration root previously hid the `client` fixture.

Run from `GROW-8\grow8-backend` in PowerShell after confirming the isolated `grow8_test` database:

```powershell
docker compose run --rm -u root `
  -v "${PWD}\..\qa\backend\tests\qa_matrix:/app/api/tests/qa_matrix:ro" `
  -v "${PWD}\..\qa\backend\reports:/app/api/tests/reports" `
  api sh -c 'python -m pip install -q pytest-html && python -m pytest tests/qa_matrix -v -ra --tb=short --html=tests/reports/backend-report.html --self-contained-html --junitxml=tests/reports/qa_matrix/junit.xml'
```

To validate only the first health test, replace the Pytest command after `&&` with `python -m pytest tests/qa_matrix -k "BE-HLTH-001" -v -x --tb=short`.

HTML: `GROW-8\qa\backend\reports\backend-report.html`.
JUnit: `GROW-8\qa\backend\reports\qa_matrix\junit.xml`.

The report shows observed status and error diagnostics. It does **not** provide a detailed actual HTTP response for every successful case unless logging is added to the tests. Skip statuses should be retained, not converted to passes.

## Playwright backend API tests

From `GROW-8\qa` with backend services running and `API_URL` configured:

```powershell
npm run test:backend:smoke
npm run test:backend:sanity
npm run test:backend:regression
npm run report:backend:regression
```

Playwright's HTML report is under `qa/reports/backend/<suite>/<run-id>/html/index.html`.

## Notes

- Only test an isolated database. The Python matrix's fixtures rebuild `grow8_test`.
- Do not install dependencies inside this source folder; installed Node modules and generated reports are excluded from the clean ZIP.
- The removed Excel importer/export files were a separate, obsolete reporting workflow; HTML is the primary execution report.


## Docker execution guide

For copy-paste PowerShell commands covering Docker build, frontend, backend (Playwright and Pytest), database, and HTML reports, see `../DOCKER_TESTING.md`.
