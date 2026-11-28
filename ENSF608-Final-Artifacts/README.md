# Grow8 — ENSF 608 Final Project Artifacts (Group 2)

This folder contains the ENSF 608 submission artifacts. Each required artifact has its own numbered folder.

**To build the database:**

```bash
cd 04-implementation && mysql -u root -p < run_all.sql
```

**To run every operation:**

```bash
cd 05-operations && mysql -u root -p --force -t grow8_608 < grow8_operations.sql
```

Step-by-step instructions, including MySQL Workbench, are in `07-documentation/How-To-Create-Populate-And-Use.md`.

## Where each required artifact is

| # | Required artifact | Files |
|---|---|---|
| 1 | Final conceptual database model | `01-conceptual-model/Conceptual-ERD-Part1.drawio.svg` (+ `.png`) — the Chen-notation ERD: entities, relationships, cardinalities and key attributes<br>`01-conceptual-model/Conceptual-ERD-Part2-Reports.drawio.svg` (+ `.png`) — opportunity reports and takedown, added Nov 22 |
| 2 | Final logical database model | `02-logical-model/Relational-Schema.md` — 21 relations with primary and foreign keys<br>`02-logical-model/Logical-ERD-and-Relational-Schema.pdf` — every table with columns, types, keys and crow's-foot relationships (page 1) and the relational schema (page 2) |
| 3 | Normalization documentation | `03-normalization/Normalization-3NF.md` — the normalization decisions that mattered (N1–N10) and a one-line result for each of the 21 relations, all in 3NF (and BCNF) |
| 4 | Complete SQL database implementation | `04-implementation/00_create_database.sql`, `01_create_schema.sql` — tables, primary and foreign keys, unique and CHECK constraints, integrity triggers and procedures, views |
| 5 | Database population data or scripts | `04-implementation/02_populate_reference_and_core_data.sql`, `03_populate_workflow_history.sql`<br>`run_all.sql` runs steps 0–4 in order; `04_verify_database.sql` prints what was created and loaded |
| 6 | SQL operations and queries | `05-operations/grow8_operations.sql` — by category: 9 stored procedures (SP), 15 queries (Q) and 5 views (V), 22 data modification steps (OP) and 18 integrity checks (IC), each with a short description of its purpose |
| 7 | Database testing evidence and results | `05-operations/Operations-Evidence.md` — the actual output of every operation, query and procedure, including the 18 integrity checks the database refused<br>`06-testing/Database-Test-Report.md` — the automated test suite (pytest against a real MySQL) and the rules it covers<br>`06-testing/Relationship-Validation.md` — every relationship and business rule, and how it is enforced |
| 8 | Documentation to create, populate and use the database | `07-documentation/How-To-Create-Populate-And-Use.md`<br>`07-documentation/Data-Dictionary.md` — every table and column |
| 9 | Evidence of individual contributions | `08-individual-contributions/Individual-Contributions.md` |

## The database in numbers

| Item | Count |
|---|---|
| Tables (all in 3NF and BCNF) | 21 |
| Primary keys | 21 |
| Foreign keys | 31 |
| Unique keys | 20 |
| CHECK constraints | 13 |
| Integrity triggers | 21 (calling 10 procedures) |
| Views for derived values | 5 |
| Stored procedures for operations | 9 |
| Rows in the dataset | 7 users, 15 opportunities, 14 applications, 5 work submissions, 4 verifications, 7 feedback entries, 8 point transactions, 2 reports, 9 notifications |

## Keeping the package in step with the repository

Several files here are copies of the files the application actually uses:

| Copy in this package | Source in the repository |
|---|---|
| `04-implementation/01`–`03` | `grow8-backend/db/init/` |
| The logical-model files | `docs/db/` and `docs/diagrams/` |
| The test and documentation copies | `docs/db/` |
| The conceptual ERDs | `docs/diagrams/` |

`sync.sh` refreshes the copies, and `sh sync.sh --check` reports any that are out of date. Edit the repository files, not the copies.
