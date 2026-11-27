# GROW8 QA – Automated Test Suite

ENSF 607 and ENSF 608 · Group 2 · GROW8

## Overview

This directory contains the [ENSF 607 UI and API automation](ens607_qa/) and the [ENSF 608 SQL verification suite](ENSF608_SQL_QA/README.md).

The QA implementation is contained in `grow8-qa/`. No existing application source files are modified by this contribution. The suite is based on the team main baseline `59c7f71885ad064033ddfa7c21c11ab5152278f7`.

## Final submission

| Course | Recorded outcome | Submission artifacts |
| --- | --- | --- |
| ENSF 607 | 108/108 UI and 301/301 API cases passed across completed runs and targeted retests on November 26, 2026 | `ENSF607-GROW8-Final-Submission.zip` contains the results and test suite workbooks, UI screenshots, API HTML evidence, and the requirements and architecture PDFs. |
| ENSF 608 | 126/126 SQL cases passed on MySQL 8.0.46 across two executions on November 26, 2026 | `ENSF608-GROW8-Final-Submission.zip` contains the [SQL submission index](../ENSF608-Final-Artifacts/README.md#sql-qa-submission-evidence), results, test suite, traceability matrix, evidence and requirements PDF. |

The prepared local upload archives are in `grow8-qa/ens607_qa/reports/submission/`. Extract each ZIP into its own folder to keep the results workbook beside its `Evidence/` folder. For ENSF 608, open the workbook under `ENSF608-Final-Artifacts/06-testing/`. ENSF 607 raw reports are retained locally under `grow8-qa/ens607_qa/reports/`. The consolidated ENSF 607 results workbook also includes exploratory testing outside the 409 automated cases.

## ENSF 607 test inventory

| Suite | Test case IDs | Count |
| --- | --- | ---: |
| UI | UI-001 to UI-108 | 108 |
| API | API-001 to API-301 | 301 |
| **Total** | | **409** |

### Execution coverage

| Runner | Scope | Count |
| --- | --- | ---: |
| Playwright UI | Live browser workflows with API setup | 46 |
| Playwright UI | Browser regression scenarios using primarily mocked API fixtures | 62 |
| Playwright API | Live HTTP API tests | 64 |
| pytest | FastAPI TestClient with isolated MySQL and a fake event publisher | 237 |

The test IDs are unique across the catalog and are not counted twice. `cases.json` defines the test catalog, and `automation-map.csv` maps the cases to implementations and requirements. The map also documents coverage limitations; it does not imply that every manual test step is independently asserted.

## Prerequisites

- Windows PowerShell (commands below are written for this environment).
- Git, Node.js (22 or newer), npm, and Python 3.
- Docker Desktop running Linux containers, with Docker Compose available.
- Internet access for dependency installation and Docker image downloads.
- Available local ports: 18000 (API), 15173 (UI), 13307 (MySQL), and 15673 (RabbitMQ management).

Use the isolated QA environment only. Do not run these tests against production or a shared database. The tests can create and change application data, including test account credentials.

## Local execution

From the repository root, with the QA contribution checked out, confirm the current branch and working tree:

```powershell
git branch --show-current
git status --short
```

Validate the test inventory:

```powershell
node grow8-qa/ens607_qa/verify-inventory.mjs
```

Expected inventory: 108 UI IDs, 301 API IDs, 409 total, with no missing or duplicate IDs. Inventory validation is a static check, not an execution result.

Start Docker Desktop before running any of the following commands. Select the required suite:

```powershell
# UI only
node grow8-qa/ens607_qa/run-local.mjs ui

# API only
node grow8-qa/ens607_qa/run-local.mjs api

# Both suites
node grow8-qa/ens607_qa/run-local.mjs all
```

The local runner installs required dependencies, starts an isolated Docker Compose project using QA-specific ports and volumes, executes the selected suites, and collects the results. It is designed to clean up only its own QA Compose project. If a run is interrupted, verify the QA resources before restarting; do not remove unrelated Docker projects or volumes.

A nonzero exit code indicates a failure or incomplete execution. Inspect the reports before rerunning.

## Targeted UI retesting

For a faster retest, use direct Playwright execution only when dependencies and the isolated QA frontend and backend are already running. This command does not start the environment itself.

From the repository root:

```powershell
cd grow8-qa/ens607_qa
$env:QA_API_URL = 'http://localhost:18000/api/v1'
$env:QA_UI_URL = 'http://localhost:15173'
$env:QA_REPORT_DIR = "reports/ui-retest-$(Get-Date -Format yyyyMMdd-HHmmss)"

# Example: retest UI-010 only
npx playwright test tests/ui.spec.mjs --project=ui --workers=1 --timeout=60000 --retries=0 --grep 'UI-010\b'
```

Use one worker for live tests that modify shared accounts, passwords, profiles, notifications, or other shared data. Parallel runs may be useful for isolated mocked browser tests, but any concurrency-related failure should be investigated before classification as a product defect.

## Reports and evidence

The local runner writes execution artifacts under `grow8-qa/ens607_qa/reports/` in a run-specific directory. Depending on the selected suite and whether setup succeeds, artifacts include:

- Playwright HTML, JSON and JUnit reports.
- UI screenshots, failure traces and configured video attachments.
- Live API request/response evidence attachments.
- pytest HTML/JUnit reports and individual API evidence records.
- `case-results.csv`, combining executed outcomes using the test catalog IDs.
- Docker Compose logs, run metadata and setup failure details where applicable.

Generated ENSF 607 reports are excluded from Git and are retained locally for the project submission. Review logs, screenshots, traces and request/response attachments for sensitive data before sharing.

To populate a copy of a compatible execution workbook using the result importer, run from the repository root:

```powershell
python -m pip install openpyxl
python grow8-qa/ens607_qa/import-results.py "<input-workbook.xlsx>" "grow8-qa/ens607_qa/reports/<run-folder>/case-results.csv" "<output-workbook.xlsx>"
```

Replace the placeholders with actual file paths. The workbook must match the schema expected by the importer. Do not use the execution-independent Test Suite workbook as an execution template unless its compatibility has been verified. Preserve initial failures and retest evidence; missing results are not passes.

## QA directory structure

```text
grow8-qa/
├── ens607_qa/
│   ├── tests/                # Live UI and HTTP API tests and helpers
│   ├── legacy-ui/            # Browser regression tests and fixtures
│   ├── legacy-api/           # pytest API tests and fixtures
│   ├── cases.json            # Test catalog
│   ├── automation-map.csv    # Implementation and requirement mapping
│   ├── run-local.mjs         # Isolated local runner
│   └── reports/              # Local execution evidence and submission archives
├── ENSF608_SQL_QA/            # SQL test catalogs and runners
└── README.md
```

## Scope and limitations

- The mocked browser tests validate UI behavior against controlled fixtures; they do not independently establish live backend integration.
- The pytest API tests use FastAPI TestClient, isolated MySQL and a fake publisher. Five health scenarios use injected probe failures; these are not physical service outage or recovery tests.
- NFR-04, NFR-05, NFR-09 and NFR-10 require additional consumer, infrastructure or architecture evidence for full verification.
- Test failures may result from product defects, outdated automation, fixture differences or environmental issues. Review the actual evidence and reproduce the behavior before reporting a product defect.
- A fresh run is required to establish results for a new application revision.

## CI/CD and contribution

The suite currently supports local execution. No GitHub Actions workflow is included in this QA contribution; automated CI integration is deferred until the workflow has been validated.

The contribution branch is `grow8-qa-final`, based on the team repository's `main` branch. The curated SQL submission artifacts live in `ENSF608-Final-Artifacts/`. The ignore rules cover raw reports, upload archives, dependencies, caches and temporary backups.

Review the branch diff and test evidence before merging. Keep application changes and future CI integration in separate, reviewed contributions.
