# Grow8 Database automation

**Scope:** Read-only SQL checks against MySQL. This directory contains its own `tests/smoke`, `tests/sanity`, `tests/regression` and `helpers`.

**Prerequisites:** Grow8 MySQL running and valid local DB_* credentials. No frontend or API required.

Run from the repository's `qa/` folder:

```powershell
npm run test:database:smoke
npm run report:database:smoke
npm run test:database:sanity
npm run report:database:sanity
npm run test:database:regression
npm run report:database:regression
```

The regression command executes **all tests in this layer**. Individual runs get unique report directories under `qa/reports/database/<suite>/<run-id>/html/`; `latest.json` links the latest run.

See `../README.md` for environment setup and GitHub CI steps. The tests supplied here have not been run against live services in this environment.


## Docker execution guide

For copy-paste PowerShell commands covering Docker build, frontend, backend (Playwright and Pytest), database, and HTML reports, see `../DOCKER_TESTING.md`.
