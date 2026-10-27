# Grow8 frontend UI automation

The current frontend automation covers the Home (`/`) and Browse Opportunities (`/opportunities`) pages, including navigation, with separate smoke, sanity, and regression suites. The project contains source tests under `tests/` and shared fixtures under `helpers/`.

Tests use deterministic mocked API responses. A screenshot helper attaches a full-page PNG for each executed frontend test; failures may also include trace/video evidence.

From `GROW-8\qa` (after installing Node dependencies and Chromium):

```powershell
npm run test:frontend:smoke
npm run test:frontend:sanity
npm run test:frontend:regression
npm run report:frontend:regression
```

The runner generates timestamped HTML reports under `qa/reports/frontend/<suite>/<run-id>/html/index.html`. The cleaned ZIP excludes old execution outputs, so run a suite to generate a new report. See `../README.md` for setup.


## Docker execution guide

For copy-paste PowerShell commands covering Docker build, frontend, backend (Playwright and Pytest), database, and HTML reports, see `../DOCKER_TESTING.md`.
