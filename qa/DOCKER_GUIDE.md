# Grow8 QA and Docker (Windows PowerShell)

## Application containers

The existing Compose configuration is in `grow8-backend/`, not at the repository root.

```powershell
cd .\grow8-backend
docker compose up -d --build
docker compose ps
```

For the **Python backend 346-case suite**, use the one-off `docker compose run` command in [`backend/README.md`](backend/README.md). It bind-mounts the QA-only Python test files and writes a standalone Pytest HTML report to `qa/backend/reports/backend-report.html`. Confirm the isolated `grow8_test` database before running.

For **Playwright** frontend/backend/database QA, use the Node scripts in [`README.md`](README.md) from the `qa/` folder. This archive does **not** contain `grow8-backend/docker-compose.qa.yml`; do not use commands that depend on that overlay without creating it separately.

The clean distribution excludes prior generated reports and dependency directories. Install dependencies and execute tests to generate current HTML reports.
