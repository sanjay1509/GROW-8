# How to Create, Populate and Use the Grow8 Database

**ENSF 608 · Group 2**

The database can be built in two ways:

- **On its own** (A): from the files in this package, on any MySQL 8 server. This is all a grader needs.
- **As part of the running application** (B): the backend's Docker setup builds the same database automatically.

## Requirements

- **MySQL 8.0 or newer.** Tested on 8.0.46 and 8.4. MySQL Workbench 8 works too.
- **An account that can create a database, triggers and procedures.** `root` works.
  - With a non-root account, the server's binary logging blocks trigger creation (error 1419).
  - Fix: as root, run `SET GLOBAL log_bin_trust_function_creators = 1;`

## A. Create and populate from the submitted files

All scripts are in `04-implementation/` and run in this order:

| Step | File | What it does |
|---|---|---|
| 0 | `00_create_database.sql` | Creates an empty database, `grow8_608` (drops it first if it exists). |
| 1 | `01_create_schema.sql` | 21 tables with primary keys, foreign keys, unique keys and CHECK constraints; 10 integrity procedures and 21 triggers; 5 views. |
| 2 | `02_populate_reference_and_core_data.sql` | Reference data (categories, skills, badges), 7 users (1 admin, 3 creators, 3 contributors), organizations, profiles and 15 opportunities. |
| 3 | `03_populate_workflow_history.sql` | A believable history on top of step 2: applications, work submissions and verifications, points and badges, feedback and admin reviews, opportunity reports and notifications. Every row passes the integrity triggers. |
| 4 | `04_verify_database.sql` | Read-only. Prints how many objects were created and how many rows each table holds. |

**Command line, all steps in one go:**

```bash
cd ENSF608-Final-Artifacts/04-implementation
mysql -u root -p < run_all.sql
```

`run_all.sql` uses `SOURCE` with relative paths, so start `mysql` from inside `04-implementation`.

**MySQL Workbench:** open each file in the order above and run it with the lightning-bolt button (Execute all). Workbench understands the `DELIMITER` lines in step 1.

**Expected result of step 4:**
- Objects: 21 tables, 5 views, 21 triggers, 10 procedures, 21 primary keys, 31 foreign keys, 20 unique keys, 13 check constraints.
- Rows: 7 users, 15 opportunities, 14 applications, 5 work submissions, 4 verifications, 7 feedback entries, 8 point transactions, 2 reports, 9 notifications.

## B. The database inside the running application (Docker)

From `grow8-backend/`, run `make reset-db`. It rebuilds the application's database, `grow8`, from the same files (`db/init/001_schema.sql`, `002_seed.sql`, `004_seed_workflow.sql`) on MySQL 8.4 in Docker.

| Setting | Value |
|---|---|
| Host and port | 127.0.0.1:3307 |
| Database | `grow8` |
| User | `grow8` (password from `grow8-backend/.env`) |

Full setup steps are in `docs.md` at the repository root.

**On a Mac**, `make reset-db` can report "mysql is unhealthy" because Docker refuses to run `003_test_database.sh`, which also stops `004_seed_workflow.sql`. Run its two steps by hand:

```bash
docker compose exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" -e "CREATE DATABASE IF NOT EXISTS grow8_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci; GRANT ALL PRIVILEGES ON grow8_test.* TO grow8;"'
docker compose exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" grow8' < db/init/004_seed_workflow.sql
```

## Using the database

**Operations, queries and stored procedures:**

```bash
cd ENSF608-Final-Artifacts/05-operations
mysql -u root -p --force -t grow8_608 < grow8_operations.sql
```

- `--force` is needed because part 4 of the file runs statements that are meant to fail. Each error message is the proof that a rule holds.
- In Workbench, turn on *Query → Continue on SQL Script Error* before running the file.
- Parts 3 and 4 run in a transaction that is rolled back, so the data is the same afterwards and the file can be run again.

**Regenerating the evidence:** `Operations-Evidence.md` is produced by running the file through `generate_evidence.py`:

```bash
pip install pymysql
python3 generate_evidence.py --user root --password <password>
```

**Accounts in the data:** every seeded account has the password `Grow8Dev!2026`. These are development data only.

| Email | Role |
|---|---|
| `admin@grow8.dev` | admin |
| `maple.bakery@grow8.dev`, `foodbank@grow8.dev`, `yyc.events@grow8.dev` | creators |
| `alex.chen@grow8.dev`, `jordan.lee@grow8.dev`, `sam.patel@grow8.dev` | contributors |

**A few starting points:**

```sql
USE grow8_608;
SELECT * FROM v_leaderboard;                    -- points and rank, calculated
CALL sp_contributor_summary(6);                 -- one contributor's dashboard
CALL sp_find_open_opportunities('community', NULL);
```

`sp_*` procedures exist after `grow8_operations.sql` has been run once.

**Starting over:** run `run_all.sql` again. It drops and recreates `grow8_608`.

## Troubleshooting

| Message | Cause and fix |
|---|---|
| `ERROR 1419 … binary logging is enabled` | A non-root account is creating triggers. Run as root, or run `SET GLOBAL log_bin_trust_function_creators = 1;` as root first. |
| `ERROR 1046 … No database selected` | Workbench has no default schema. Run `USE grow8_608;` or double-click the schema. |
| `Failed to open file '00_create_database.sql'` | `mysql` was started outside `04-implementation`. `cd` into the folder first. |
| Workbench stops at the first error in `grow8_operations.sql` | Turn on *Continue on SQL Script Error* (see above). |

## Reference documents

- **Every table and column**, with type, key and constraint: `Data-Dictionary.md` (this folder).
- **Why the tables look the way they do:** `03-normalization/Normalization-3NF.md`.
- **How the relationships and rules were checked:** `06-testing/Relationship-Validation.md`.
