# GROW8 — ENSF 608 independent SQL operations verification

Group 2 · Requirements analysis and database quality assurance · Aparna Ayyalasomayajula

## Scope and attribution

This verification suite complements the team's existing schema, seed scripts, SQL operations and direct database tests. It does **not** replace those artifacts or claim authorship of the team's SQL. It tests the actual SQL source, not API responses or mocked data. The source snapshot is team `main` commit `59c7f71885ad064033ddfa7c21c11ab5152278f7`.

* 71 original labeled blocks: 9 stored procedure definitions, 15 retrieval queries, 5 views, 2 stored procedure execution blocks, 22 workflow/transaction blocks and 18 integrity checks.
* 5 independent supplemental read-only queries: four basic filtering queries and one explicit `GROUP BY ... HAVING` query. These make the filtering and HAVING rubric coverage explicit without modifying the original operations file.
* 76 verification cases in total; 25 distinct rubric operations mapped once each. The two stored procedure mappings require both definition and representative call to pass.
* Every positive result set is checked against the team reference output or explicit seed-based expected rows. Expected rejection tests check both the MySQL error code and constraint/rule name. A failed expected-rejection assertion is a failure, not an automatic pass. OP-22 also compares row-content hashes of all 21 base tables before and after rollback (not auto-increment counters).

The source team's `Operations-Evidence.md` documents historical actual outputs from November 26, 2026. Here it is used solely as an expected-value reference. The new run's evidence will be generated on your machine. The reference report limits displayed cell values to 90 characters; comparisons use that same convention. Full actual outputs are retained in new evidence. V-5 seed-generated listed timestamps are checked for presence/format rather than exact clock values. SQL session time is set to November 26, 2026, 15:06:50 UTC so the date-sensitive seeded operations can be reproduced (not a real-time availability test). Results do not establish all application or infrastructure requirements. Reward, badge and leaderboard checks here are SQL/schema demonstrations in the team operations artifact, not a claim that corresponding deferred application screens are implemented.

## Windows PowerShell setup and execution

The [SQL submission evidence](../../ENSF608-Final-Artifacts/README.md#sql-qa-submission-evidence) combines this 76-case baseline with the [50-case extension](EXTENSION_README.md).

Open Docker Desktop with Linux containers. The runner requires Python 3.10+ and pip. It uses a separate MySQL container, random local port, random temporary credentials and its own volume. Internet access is needed if the Docker image or packages must be downloaded.

From the repository root:

```powershell
cd grow8-qa/ENSF608_SQL_QA
python -m pip install -r requirements.txt
$repo = (Resolve-Path ../..).Path
python .\run_sql_tests.py --repo $repo --check-only
python .\run_sql_tests.py --repo $repo
```

The first command using `--check-only` validates the exact source file hashes, 71 block IDs, descriptions, reference result sets and 25 distinct rubric mappings. It also generates `prepared/grow8_operations_by_category.sql` from the original team file plus the supplements; it does not execute MySQL. If the source is absent or its hashes differ, do not replace team files or edit the checks just to pass. Fetch the exact reviewed source snapshot into a separate worktree, leaving your QA branch untouched:

```powershell
cd C:\Users\aparn\Downloads\GROW-8-Final-QA
git fetch upstream --prune
git worktree add --detach "$HOME\Downloads\GROW8-608-DB-Source" 59c7f71885ad064033ddfa7c21c11ab5152278f7
```

Return to the extracted `ENSF608_SQL_QA` folder and run:

```powershell
$repo = "$HOME\Downloads\GROW8-608-DB-Source"
python .\run_sql_tests.py --repo $repo --check-only
python .\run_sql_tests.py --repo $repo
```

The default image is `mysql:8.0.46` (the team's reference report used MySQL 8.0.46). If the exact tag cannot be pulled, explicitly use `--image mysql:8.0` and retain the recorded version; review any behavior differences. The runner exits nonzero if setup is blocked, any check fails, or any check does not complete. Missing tests remain `Not run`.

## Outputs — keep only the needed evidence

Each run creates `reports/<timestamp>/`:

* `ENSF608_SQL_Test_Results.xlsx`: a populated copy of the test suite workbook, with the 76 test outcomes, direct relative hyperlinks and an automatically calculated summary/rubric status. The original suite stays unchanged.
* `Evidence/SQL-001.html` through `SQL-076.html`: one file per executed test, with executed SQL, purpose, expected rows/error, actual result rows/error, verdict and execution timestamp. No invented screenshots. The HTML reports are the evidence of the new actual execution.
* `grow8_operations_by_category.sql`: organized rubric index followed by the **unmodified team operations** and the five new supplemental queries; this retains dependency/transaction order rather than reordering DML into separate non-executable fragments. The wrapper includes the fixed reference clock. Do not execute this file on a production/shared database. It is intended for the same isolated freshly seeded database and requires `mysql --force` for intentional negative cases.
* `case-results.csv`: machine-readable outcomes; `run-metadata.json`: source hashes, execution timestamp, version, counts; `setup.txt` or `setup-failure.txt` as appropriate.

When uploading the report, ZIP the completed timestamp folder (keep the workbook and Evidence folder together). Do not include `node_modules`, database volumes, Docker images or application code. Before submitting, inspect all failed cases and review the actual result rows. Do not convert an expected rejection into a product defect; do not mark a test passed if its result has not been verified. Re-run the suite in a new timestamp folder after legitimate fixes; do not overwrite earlier evidence.

```powershell
$latest = Get-ChildItem .\reports -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Compress-Archive -Path "$($latest.FullName)\*" -DestinationPath "$HOME\Downloads\GROW8_ENSF608_SQL_Execution_Evidence.zip" -Force
```

## Rubric alignment

The workbook's `Rubric Coverage` tab specifies a unique source block/statement for each of the 25 required operations (2 INSERT, 2 UPDATE, 2 DELETE, 4 basic filtering SELECT, 2 sorting/limit, 3 aggregation, 2 grouping including HAVING, 3 INNER JOIN, 2 LEFT JOIN, 1 combined JOIN/aggregation, 2 stored procedures with inputs). The combined SQL file is generated from the exact verified source during the run. The group project should include the original team operations artifact, these supplemental queries if accepted by the team, the results workbook and matching evidence. Do not count the individual tests in this suite as new unique backend tests in addition to overlapping team cases.

## Academic review

Refer to the project README.md for generative AI usage disclosure. Update the disclosure to accurately identify tools and how they were used, as required by the course. Review and meaningfully adapt this code and its expected outcomes yourself before submission; be prepared to explain the queries, constraints and assertions. Team SQL and historical evidence are separately attributed. No independent SQL execution has been performed in the assistant's environment.
