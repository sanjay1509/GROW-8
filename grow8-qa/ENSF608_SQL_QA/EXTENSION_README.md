# ENSF 608 — GROW8 SQL QA extension (SQL-077–126)

The [ENSF 608 submission results](../../ENSF608-Final-Artifacts/README.md#sql-qa-submission-evidence) record 76 baseline passes and 50 extension passes from two executions on November 26, 2026 on MySQL 8.0.46.

## Windows / PowerShell

Run the commands below from the repository root. The local submission archive includes `baseline_76.zip` with the original 76-case execution. In a fresh checkout, supply that archive with `--baseline <path-to-archive>`, or package a fresh passing baseline run as described in the [baseline runner guide](README.md).

```powershell
cd grow8-qa/ENSF608_SQL_QA
python -m pip install -r requirements.txt
python .\run_extended_sql_tests.py --repo ..\.. --check-only
python .\run_extended_sql_tests.py --repo ..\..
```

Start Docker Desktop first. The extension runs only the additional 50 cases on a disposable MySQL 8.0.46 container; the existing dev database is not contacted. The original SQL runner remains available for a fresh 76-case run. The source preflight checks the exact reviewed team's SQL blob hashes; if the team changes a source, review the changes instead of disabling the guard. `baseline_76.zip` is the uploaded historical report, not a new execution. `--baseline` accepts a matching alternate 76-pass report ZIP if needed.

## Results

`reports/extended-<timestamp>/` contains `ENSF608_SQL_Test_Results_126.xlsx`, `case-results.csv`, `run-metadata.json`, `Evidence/`, `setup.txt`, and the original organized SQL operations file. The workbook includes all 126 IDs, 25 rubric mappings (the baseline), and an RTM with separate baseline coverage and extension outcomes. Evidence for the 76 original cases is copied byte-for-byte from the prior ZIP. Evidence for new tests is generated only when attempted; setup failures leave unexecuted cases marked Not run. All routine cases use rollback and compare all 21 table content hashes; the concurrency case uses two independent transactions, commits its fixture/winner, and explicitly deletes its fixture rows before verifying the original content hashes. Auto-increment counters are not part of row-content verification. The 126-case design workbook is not evidence of execution.

The expected result catalog is reviewed against the team's final DDL and fixed seed snapshot at `59c7f71885ad064033ddfa7c21c11ab5152278f7`. The additional cases include positive assertions, exact expected error codes and constraint names, and row-result comparisons. A test with multiple checks is counted once. If an assertion fails, the evidence records the failure. Do not alter expected values simply to force passes. No quantitative latency requirement, cryptographic authentication proof, UI/file authorization, broker delivery, full normalization proof, conceptual diagram review, or full ORM parity is established by this SQL extension. The original RTM gaps are retained as historical context, not automatically marked covered. Review the SQL and understand the results before submission; record AI assistance in the repository README as required by the course.
