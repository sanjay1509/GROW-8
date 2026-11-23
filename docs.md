# GROW8 – Developer Documentation

This file covers how to work on GROW8 day to day. For project goals, architecture and team, see [README.md](README.md).

## Contents

1. [Running the application](#1-running-the-application)
2. [Database and seed data](#2-database-and-seed-data)
3. [Using the API](#3-using-the-api)
4. [Editor setup (VS Code)](#4-editor-setup-vs-code)
5. [Adding a Python package](#5-adding-a-python-package)

---

## 1. Running the application

The backend lives in [`grow8-backend/`](grow8-backend/). It runs entirely in Docker, so you do **not** need Python, MySQL or RabbitMQ installed on your machine.

The stack is made of six containers:

| Container | What it is |
| --- | --- |
| `mysql` | MySQL 8.4 database |
| `rabbitmq` | RabbitMQ message broker, with its web UI |
| `api` | FastAPI backend (REST API) |
| `creator_service` | Consumer for Creator events |
| `contributor_service` | Consumer for Contributor events |
| `admin_service` | Consumer for Admin events |

### 1.1 Prerequisites

- **Docker Desktop**, installed and **running** (whale icon in the system tray). Docker Compose v2 comes with it.
- **Git**.
- **`make`** (optional but recommended). Every `make` command below has a plain `docker compose` equivalent in [1.6](#16-without-make).
  - Windows: `make` works from Git Bash, PowerShell or cmd. The Makefile's commands need the `sh` that comes with **Git for Windows**; the Makefile finds it automatically from wherever Git is installed, as long as `git --version` works in that terminal. If `make` isn't found, install it (e.g. `winget install GnuWin32.Make` or `choco install make`) or use the `docker compose` commands.
  - macOS / Linux: `make` is usually already installed.

### 1.2 First-time setup

From the repository root:

```bash
cd grow8-backend
make env    # creates .env from .env.example (skips it if .env already exists)
```

`.env` holds local passwords and ports. The defaults work for local development. **Never commit `.env`**: it is git-ignored. If you add a new setting, add it to `.env.example` and `docker-compose.yml` instead.

### 1.3 Start the stack

```bash
make up
```

This builds the images and starts all six containers in the background. The first run downloads base images and takes a few minutes; later runs are quick.

MySQL and RabbitMQ start first. The API and consumers wait until both report healthy.

### 1.4 Check that it works

```bash
make ps
```

All six containers should be `Up`, and `mysql`, `rabbitmq` and `api` should show `(healthy)`.

Then open:

| What | URL | Notes |
| --- | --- | --- |
| API health | <http://localhost:8000/health> | Should return `{"status":"ok","checks":{"mysql":"ok","rabbitmq":"ok"}}` |
| API docs (Swagger) | <http://localhost:8000/docs> | Interactive API documentation |
| RabbitMQ UI | <http://localhost:15672> | Log in with `RABBITMQ_USER` / `RABBITMQ_PASSWORD` from `.env` |
| MySQL | `localhost:3307` | For MySQL Workbench etc. Credentials are `MYSQL_USER` / `MYSQL_PASSWORD` from `.env` |

If `/health` returns `"status":"degraded"` (HTTP 503), the `checks` field tells you whether MySQL or RabbitMQ is the problem.

### 1.5 Everyday commands

Run these from `grow8-backend/`.

| Command | What it does |
| --- | --- |
| `make up` | Build and start everything (also picks up Dockerfile / dependency changes) |
| `make down` | Stop and remove the containers. **Data is kept.** |
| `make restart` | `down` then `up` |
| `make ps` | Show container status |
| `make logs` | Follow logs from all containers (Ctrl+C to stop following) |
| `make test` | Run the API tests |
| `make test-services` | Run the tests of the three consumer services |
| `make postman` | Run the Postman collection (report in `tests/reports/`). Adds a few rows to your dev database. |
| `make lint` | Check code style with ruff |
| `make fmt` | Auto-fix and format code with ruff |
| `make mysql` | Open a MySQL shell on the GROW8 database |
| `make config` | Validate the Docker Compose files |
| `make venv` | Create/update the editor-only `.venv` for VS Code (see [section 4](#4-editor-setup-vs-code)) |
| `make reset-db` | ⚠️ **Deletes all database data** and recreates it from `db/init/*.sql` |

`make test`, `make test-services`, `make lint`, `make fmt` and `make mysql` run inside the containers, so start the stack first with `make up`.

To see the logs of one container only: `docker compose logs -f api` (or `creator_service`, `mysql`, ...).

#### Hot reload

In development your source folders are mounted into the containers. **Save a `.py` file and the affected container restarts automatically.** You don't need to rebuild.

You **do** need `make up` again (to rebuild) after changing:

- a `requirements*.txt` file or `shared/pyproject.toml`
- a `Dockerfile`
- `docker-compose*.yml` or `.env`

#### Database changes

The database is created from `db/init/001_schema.sql` and `db/init/002_seed.sql`. MySQL only runs these files **the first time** it starts with an empty data volume. After you change them, run:

```bash
make reset-db
```

⚠️ This deletes everything in your local database. RabbitMQ data is not touched.

### 1.6 Without make

If you can't use `make`, run these from `grow8-backend/` instead:

| make | Equivalent |
| --- | --- |
| `make env` | `cp .env.example .env` (PowerShell: `Copy-Item .env.example .env`) |
| `make up` | `docker compose up -d --build` |
| `make down` | `docker compose down` |
| `make ps` | `docker compose ps` |
| `make logs` | `docker compose logs -f --tail=200` |
| `make test` | `docker compose exec -T api pytest` |
| `make test-services` | `docker compose exec -T creator_service pytest` (repeat for `contributor_service` and `admin_service`) |
| `make lint` | `docker compose exec -T api ruff check /app/api /app/shared` |
| `make mysql` | `docker compose exec mysql sh -c 'mysql -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE"'` |
| `make reset-db` | `docker compose rm -sf mysql`, then `docker volume rm grow8_mysql_data`, then `docker compose up -d --build` |

### 1.7 Stopping

```bash
make down
```

Your data is kept in Docker volumes and will be there next time you run `make up`. Avoid `docker compose down -v`: the `-v` deletes the database and RabbitMQ data.

### 1.8 Troubleshooting

| Problem | Fix |
| --- | --- |
| `open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified` | Docker Desktop isn't running. Start it, wait until it says *Engine running*, and try again. |
| `make: command not found` | Use Git Bash, install `make`, or use the commands in [1.6](#16-without-make). |
| `'cp' is not recognized as an internal or external command` (or `'test'`) | `make` couldn't find `sh`. Pull the latest Makefile, which adds Git for Windows' `sh` automatically. Also check that `git --version` works in that terminal (install Git for Windows with `winget install Git.Git` and open a new terminal). As a fallback, run `make` from **Git Bash**. |
| `port is already allocated` / `address already in use` | Another program is using port 8000, 3307, 5672 or 15672. Stop it, or change `API_HOST_PORT`, `MYSQL_HOST_PORT`, `RABBITMQ_HOST_PORT` or `RABBITMQ_MGMT_HOST_PORT` in your `.env` and run `make up`. |
| A container keeps restarting | `docker compose logs <container>` shows the error. |
| `/health` shows `"mysql":"unavailable"` right after startup | MySQL can take up to ~30 s on first start. Wait and refresh. |
| Code changes aren't picked up | If you changed dependencies, a Dockerfile or `.env`, run `make up`. Otherwise check `make logs` for an error that stopped the reload. |
| Database still has old tables after editing `db/init/*.sql` | The init scripts only run on an empty database. Run `make reset-db` (deletes local data). |
| `Table 'grow8.opportunity' doesn't exist` (or another table) | Your database was created before the schema existed. Run `make reset-db`. See [2.2](#22-after-pulling-database-changes). |
| `make test` fails with `(1419, 'You do not have the SUPER privilege and binary logging is enabled ...')` | Your MySQL container still runs with the old settings. Run `make up` (it restarts MySQL with `--skip-log-bin`), then `make test` again. |
| A teammate's changes don't work for you after `git pull` | Run `make up` to rebuild, and compare your `.env` with `.env.example` for new settings. |

---

## 2. Database and seed data

### 2.1 Everyone gets the same database

The database is defined by three files in [`grow8-backend/db/init/`](grow8-backend/db/init/), which are committed to Git:

| File | What it does |
| --- | --- |
| `001_schema.sql` | Creates all 19 tables (the 17 from the ENSF 608 proposal plus `notification`, see [ADR 0003](grow8-backend/docs/adr/0003-persisted-notifications.md), and `contributor_resume`, see [ADR 0008](grow8-backend/docs/adr/0008-contributor-resume.md)), the integrity triggers and the derived-value views. It is the single source of truth for the schema. |
| `002_seed.sql` | Fills them with **development-only** placeholder data. It uses fixed IDs and dates, so every developer gets identical rows. |
| `003_test_database.sh` | Creates an empty `grow8_test` database that `make test` uses, so tests never change your dev data. |

MySQL runs these files automatically **the first time** it starts with an empty data volume. Anything you create later through Swagger, Postman or the frontend exists only on your machine.

### 2.2 After pulling database changes

MySQL does not re-run the files on an existing database. Whenever a pull changes anything in `grow8-backend/db/init/`, run:

```bash
cd grow8-backend
make reset-db
```

⚠️ This deletes everything in **your** local database, and the files uploaded to it (resumes and work submission attachments, kept on the `file_storage` volume), then recreates the database from the files. It does not affect anyone else.

If the pull also changed `docker-compose.yml`, run `make up` first so MySQL restarts with the new settings.

You can see whether a pull touched the database files with `git diff --stat HEAD@{1} -- grow8-backend/db/init`.

### 2.3 What is seeded

| Data | Contents |
| --- | --- |
| Categories | `knowledge` (Knowledge-based), `community` (Community) |
| Skills | 12, e.g. `data-entry`, `spreadsheets`, `photography`, `translation`, `event-setup` |
| Badges | 4 badge definitions (for the rewards stretch goal) |
| Organizations | Maple Street Bakery, Bow River Community Food Bank, YYC Neighbourhood Events |
| Opportunities | 15: 12 open (#10 is past its deadline, so it is hidden from the public list), 1 closed (#11), 2 drafts (#14 incomplete, #15 ready to publish) |

### 2.4 Dev accounts

All seeded accounts use the password **`Grow8Dev!2026`**. Development only.

| Email | Role | Notes |
| --- | --- | --- |
| `admin@grow8.dev` | admin | |
| `maple.bakery@grow8.dev` | creator | Owns Maple Street Bakery (opportunities 1–4, draft 14) |
| `foodbank@grow8.dev` | creator | Owns Bow River Community Food Bank (5–7, 10, 11) |
| `yyc.events@grow8.dev` | creator | Owns YYC Neighbourhood Events (8, 9, 12, 13, draft 15) |
| `alex.chen@grow8.dev` | contributor | |
| `jordan.lee@grow8.dev` | contributor | |
| `sam.patel@grow8.dev` | contributor | |

### 2.5 Changing the schema or seed

- Edit `001_schema.sql` **and** the matching ORM model in `grow8-backend/shared/grow8_common/models/` in the same commit. `make test` fails if they differ.
- Business rules that a foreign key or `CHECK` can't express live as triggers at the end of `001_schema.sql`, and derived values (verified hours, ratings, leaderboard, feedback status, verified skills) as views. Each rule is explained in `docs/db/relationship-validation.md` and tested in `api/tests/integration/test_db_integrity.py` and `test_db_applications.py`. Applying is checked by the database too: the opportunity must be open, `submitted_at` on or before the deadline, and pending + accepted applications below `applicant_limit`. A violated rule raises MySQL error 1644 with a message that starts with the rule name. Views and triggers are not part of the ORM.
- Update `docs/db/data-dictionary.md` (ENSF 608) when you add or change a column, and add new tables to `docs/db/functional-dependencies.md` and `relationship-validation.md`.
- Regenerate the physical ER diagram and relational schema (`docs/diagrams/GROW8-ER-Diagram.pdf`, `docs/db/relational-schema.md`) with `python docs/diagrams/generate_er_diagram.py` while the stack is up, and update the conceptual ERD (`docs/diagrams/ER-diagram.drawio.svg`, open it in draw.io) if an entity or attribute changed.
- Keep seed data deterministic: explicit IDs, fixed dates, no `NOW()`. `002_seed.sql` holds users and opportunities; `004_seed_workflow.sql` adds applications, submissions, verifications, feedback, badges and points on top (dev database only; the tests start from 002).
- `docs/db/database-questions.md` answers the proposal's eight database questions; run the SQL with `make queries`. `docs/db/test-report.md` summarizes the database tests.
- Tell the team in chat, because everyone has to run `make reset-db` after pulling.

Seeded application deadlines are fixed dates, so as the term goes on some opportunities drop out of the public list. Move the dates forward in `002_seed.sql` if that becomes a problem.

---

## 3. Using the API

Full reference: [`grow8-backend/docs/api-contract.md`](grow8-backend/docs/api-contract.md). Try everything interactively at <http://localhost:8000/docs>.

### 3.1 Signing in

1. `POST /api/v1/auth/login` with `{"email": "maple.bakery@grow8.dev", "password": "Grow8Dev!2026"}`.
2. Copy `access_token` from the response.
3. Send it as `Authorization: Bearer <token>`. In Swagger, click **Authorize** and paste the token.

### 3.2 Opportunities at a glance

| Task | Request |
| --- | --- |
| Browse open opportunities | `GET /api/v1/opportunities` |
| Search | `GET /api/v1/opportunities?q=food bank` |
| Filter | `?category=community&skill=photography&work_mode=on_site&compensation_type=paid&min_hours=5&max_hours=20` |
| Sort | `?sort=deadline` (also `-deadline`, `newest`, `oldest`, `hours`, `-hours`, `compensation`, `-compensation`, `title`) |
| Page | `?limit=20&offset=40` |
| Create a draft (creator) | `POST /api/v1/opportunities` |
| Edit a draft (owner) | `PATCH /api/v1/opportunities/{id}` |
| Publish (owner) | `POST /api/v1/opportunities/{id}/publish` |
| My opportunities, incl. drafts (creator) | `GET /api/v1/opportunities/mine?status=draft` |
| Delete a draft (owner) | `DELETE /api/v1/opportunities/{id}` |
| Close: stop taking applications (owner) | `POST /api/v1/opportunities/{id}/close` |
| Cancel: call it off, applicants are told (owner) | `POST /api/v1/opportunities/{id}/cancel` |

Opportunities start as **drafts**, which can be incomplete. Publishing checks that every mandatory disclosure is filled in (requirements, dates, hours, compensation, applicant limit, deadline, working conditions, safety and accessibility information). If anything is missing, the response lists it.

### 3.3 Applications at a glance

| Task | Request |
| --- | --- |
| Apply (contributor) | `POST /api/v1/opportunities/{id}/applications` with `{"motivation": "..."}` (optional) |
| My applications (contributor) | `GET /api/v1/applications/mine?status=pending` |
| Applications to my opportunity (creator) | `GET /api/v1/opportunities/{id}/applications` |
| Applications to all my opportunities (creator) | `GET /api/v1/applications/received?status=pending` |
| Accept or reject (owner) | `POST /api/v1/applications/{id}/decision` with `{"decision": "accepted"}` |
| Withdraw (applicant) | `POST /api/v1/applications/{id}/withdraw` |

Try it on the dev data (with the stack running, since the notifications come from the consumer services):

1. Sign in as `alex.chen@grow8.dev` and apply to opportunity **4** (holiday market booth, 3 places, no applications yet).
2. Sign in as `maple.bakery@grow8.dev`: `GET /api/v1/notifications` shows "New application: Holiday market booth assistant". Accept it with the `application_id` from step 1.
3. Back as Alex, the notifications show "You were accepted: …". Withdraw it (`POST /api/v1/applications/{id}/withdraw`).
4. As Maple Street Bakery again, the notifications show "Application withdrawn: …", saying the place is open again.
5. Opportunity **1** already has two pending applications for its two places (from `004_seed_workflow.sql`), so Alex applying there gets 409 `APPLICANT_LIMIT_REACHED`.

Seeded deadlines are real dates, so this works until opportunity 4 closes on 2026-12-01.

### 3.4 Profile and resume

Contributors edit their own profile and skills, creators their organization; any user can change their name ([ADR 0017](grow8-backend/docs/adr/0017-contributor-profile.md)).

| Task | Request |
| --- | --- |
| See your profile (contributor) | `GET /api/v1/contributors/me/profile` |
| Change name, headline, bio, institution or city | `PATCH /api/v1/contributors/me/profile` with only the fields to change, e.g. `{"headline": "Data student", "city": null}` |
| Replace your skills | `PUT /api/v1/contributors/me/skills` with `{"skill_codes": ["spreadsheets", "translation"]}` (codes from `GET /api/v1/skills`) |
| Change your name (any role) | `PATCH /api/v1/auth/me` with `{"full_name": "..."}` |
| See or edit your organization (creator) | `GET` / `PATCH /api/v1/creators/me/organization`, e.g. `{"website": "https://example.com", "city": null}` ([ADR 0018](grow8-backend/docs/adr/0018-creator-organization.md)) |

Each skill comes back with `listed` and `verified`; `verified` turns true once a creator approves your work on an opportunity that required that skill, even if you never listed it (then it shows as `listed: false`, and editing your skills can't remove it, [ADR 0019](grow8-backend/docs/adr/0019-earned-skills.md)). Email can't be changed. An account without a profile row (none of the seeded ones) sees empty fields until its first save creates it.

A contributor can also keep one PDF resume (at most 10 MB); creators download it from an application. In Swagger, `PUT /api/v1/contributors/me/resume` shows a file picker. With curl:

```bash
curl -X PUT http://localhost:8000/api/v1/contributors/me/resume   -H "Authorization: Bearer <contributor token>" -F "file=@my-cv.pdf"
```

| Task | Request |
| --- | --- |
| Upload or replace (contributor) | `PUT /api/v1/contributors/me/resume` (multipart field `file`) |
| See or download your own | `GET /api/v1/contributors/me/resume` · `GET /api/v1/contributors/me/resume/file` |
| Delete it | `DELETE /api/v1/contributors/me/resume` |
| Download an applicant's (creator) | `GET /api/v1/applications/{id}/resume` |

Files are stored on the `file_storage` Docker volume, never in MySQL ([ADR 0007](grow8-backend/docs/adr/0007-local-file-storage.md)). A file that isn't really a PDF gets 415, even if it's named `.pdf`.

### 3.5 Work submission

An accepted contributor submits their work once, with a description, the hours they worked and up to 5 files (PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT, 5 MB each). The creator is notified and can read it and download the files. There is no resubmitting ([ADR 0012](grow8-backend/docs/adr/0012-work-submission.md)).

| Task | Request |
| --- | --- |
| Submit (applicant) | `POST /api/v1/applications/{id}/submission` (multipart: `description`, `hours_claimed`, `files`) |
| Read it (applicant or creator) | `GET /api/v1/applications/{id}/submission` |
| Download a file (applicant or creator) | `GET /api/v1/submissions/{id}/attachments/{attachment_id}` |

Try it on the dev data. Seeded application **12** is Alex's accepted application to Maple Street Bakery's opportunity 2, with nothing submitted yet:

```bash
curl -X POST http://localhost:8000/api/v1/applications/12/submission \
  -H "Authorization: Bearer <alex's token>" \
  -F "description=Cleaned up the inventory sheet." -F "hours_claimed=4.5" -F "files=@inventory.xlsx"
```

Then sign in as `maple.bakery@grow8.dev`: `GET /api/v1/notifications` shows "Work submitted: Inventory spreadsheet cleanup", and `GET /api/v1/applications/12/submission` lists the file to download. Submitting again gets 409 `WORK_ALREADY_SUBMITTED`, and Alex can no longer withdraw. `make reset-db` puts application 12 back if you want to repeat it.

The file type is decided by the content, not the name: a text file named `notes.pdf` is accepted as plain text and offered for download as `notes.pdf.txt`, and a GIF gets 415.

### 3.6 Work verification

The creator who owns the opportunity reviews submitted work and decides once: **approve** it with the hours they verify (at most the hours claimed), or **reject** it with a comment saying why. The contributor is notified either way. Approved work counts as completed, and its hours and skills count toward the contributor's verified hours and skills; the database views compute these, so nothing else is updated ([ADR 0013](grow8-backend/docs/adr/0013-work-verification.md)).

| Task | Request |
| --- | --- |
| Review queue (creator) | `GET /api/v1/submissions/received?status=awaiting` (oldest first; also `approved`, `rejected`, `opportunity_id`) |
| Read one, with its decision (applicant or creator) | `GET /api/v1/submissions/{id}` |
| Approve (creator) | `POST /api/v1/submissions/{id}/verification` with `{"decision": "approved", "verified_hours": "6", "comment": "optional"}` |
| Reject (creator) | `POST /api/v1/submissions/{id}/verification` with `{"decision": "rejected", "comment": "why"}` |

Every application also shows `work_status`: `not_submitted`, `awaiting_verification`, `completed` or `work_rejected`.

Try it on the dev data. Seeded submission **5** is Alex's 8 hours on the food bank's warehouse count, still awaiting verification. Sign in as `foodbank@grow8.dev`:

```bash
curl http://localhost:8000/api/v1/submissions/received?status=awaiting -H "Authorization: Bearer <food bank's token>"
curl -X POST http://localhost:8000/api/v1/submissions/5/verification \
  -H "Authorization: Bearer <food bank's token>" -H "Content-Type: application/json" \
  -d '{"decision": "approved", "verified_hours": "7.5", "comment": "Thanks for the recount!"}'
```

Then sign in as `alex.chen@grow8.dev`: `GET /api/v1/notifications` shows "Work verified: Warehouse inventory count" ("… was verified (7.5 h)"), and `GET /api/v1/applications/6` shows `"work_status": "completed"`. Verifying again gets 409 `SUBMISSION_ALREADY_VERIFIED`; `9` hours gets 422 `VERIFIED_HOURS_EXCEED_CLAIMED`; signed in as another creator you get 404. `make reset-db` puts submission 5 back if you want to repeat it.

If you keep your local data instead of running `make reset-db`, add the two new notification types first (the `ALTER TABLE` is in ADR 0013) and restart `contributor_service`.

### 3.7 Feedback and admin review

Once the work on an application is verified (approved or rejected), the contributor and the creator can each rate the other once, 1 to 5, with an optional comment and a "something went wrong" flag (`reports_discrepancy`). Every feedback waits for an admin. Only approved feedback is shown to the person rated and counts toward their public rating ([ADR 0015](grow8-backend/docs/adr/0015-feedback-and-admin-review.md)).

| Task | Request |
| --- | --- |
| Rate the other participant | `POST /api/v1/applications/{id}/feedback` with `{"rating": 5, "comment": "optional", "reports_discrepancy": false}` |
| See feedback on your application | `GET /api/v1/applications/{id}/feedback` → `{given, received}` |
| Review queue (admin) | `GET /api/v1/admin/feedback?status=pending` (discrepancy reports first) |
| Approve or reject (admin) | `POST /api/v1/admin/feedback/{id}/review` with `{"decision": "approved"}` or `{"decision": "rejected", "reason": "why"}` |
| Someone's public rating (no token) | `GET /api/v1/users/{id}/rating` |

Who sees what: you always see your own feedback and its status (with the admin's reason if it was rejected). Feedback **about** you appears only once an admin approves it. A rejection notifies only its author.

Try it on the dev data. Seeded feedback **5** (Sam's discrepancy report) and **6** (Jordan's rating of the food bank, 3/5) are waiting for review. Sign in as `admin@grow8.dev`:

```bash
curl "http://localhost:8000/api/v1/admin/feedback?status=pending" -H "Authorization: Bearer <admin token>"
curl http://localhost:8000/api/v1/users/3/rating     # food bank owner: 4.50 from 2 approved
curl -X POST http://localhost:8000/api/v1/admin/feedback/6/review \
  -H "Authorization: Bearer <admin token>" -H "Content-Type: application/json" -d '{"decision": "approved"}'
curl http://localhost:8000/api/v1/users/3/rating     # now 4.00 from 3
```

Feedback 5 comes first in the queue because it reports a discrepancy. Rejecting it without a `reason` gets 422 `REJECTION_REASON_REQUIRED`; reviewing anything twice gets 409 `FEEDBACK_ALREADY_REVIEWED`; a creator or contributor on the admin routes gets 403. Jordan (`jordan.lee@grow8.dev`) gets "Your feedback was published" and the food bank gets "New rating". `make reset-db` puts both back to pending.

If you keep your local data instead of running `make reset-db`, add the three new notification types first (the `ALTER TABLE` is in ADR 0015) and restart all three consumers.

### 3.8 Reporting opportunities

A contributor who sees a misleading, unsafe, discriminatory or scam posting can report it once. Admins review each report: dismiss it, or uphold it and **take the opportunity down**. A takedown cancels the opportunity, tells its applicants it won't go ahead, and tells the creator why. The creator never learns who reported ([ADR 0016](grow8-backend/docs/adr/0016-opportunity-reports-and-takedown.md)).

| Task | Request |
| --- | --- |
| Report (contributor) | `POST /api/v1/opportunities/{id}/reports` with `{"reason": "misleading_terms", "details": "optional"}` |
| Your reports and their outcome | `GET /api/v1/reports/mine` |
| Review queue (admin) | `GET /api/v1/admin/reports?status=pending` (most-reported opportunities first) |
| Take down (admin) | `POST /api/v1/admin/reports/{id}/review` with `{"decision": "upheld", "reason": "why"}` |
| Dismiss (admin) | `POST /api/v1/admin/reports/{id}/review` with `{"decision": "dismissed", "reason": "optional note"}` |

Reasons: `misleading_terms`, `unsafe_conditions`, `discriminatory`, `scam_or_spam`, `other`. A takedown upholds every pending report on the opportunity at once. It is refused once work has been submitted on the opportunity (409 `WORK_ALREADY_SUBMITTED`); dismiss the report instead.

Try it on the dev data. Opportunity **3** (Maple Street Bakery's social media calendar) is open, Sam has a pending application, and no work has been submitted:

```bash
# as alex.chen@grow8.dev
curl -X POST http://localhost:8000/api/v1/opportunities/3/reports \
  -H "Authorization: Bearer <alex's token>" -H "Content-Type: application/json" \
  -d '{"reason": "misleading_terms", "details": "Listed as paid, but the pay is not real."}'
# as admin@grow8.dev: find the report, then take it down
curl "http://localhost:8000/api/v1/admin/reports?status=pending" -H "Authorization: Bearer <admin token>"
curl -X POST http://localhost:8000/api/v1/admin/reports/<report_id>/review \
  -H "Authorization: Bearer <admin token>" -H "Content-Type: application/json" \
  -d '{"decision": "upheld", "reason": "The advertised pay is not real."}'
```

Then `GET /api/v1/opportunities/3` shows `"status": "cancelled"` and it is gone from browse. Notifications: `maple.bakery@grow8.dev` gets "Opportunity taken down" with the reason, `sam.patel@grow8.dev` gets told their application won't go ahead, and Alex gets "Thanks for your report". Reporting again gets 409 `OPPORTUNITY_ALREADY_REPORTED`; a creator reporting gets 403. `make reset-db` puts opportunity 3 back.

This feature adds two tables, so if you keep your local data instead of running `make reset-db`, run the statements listed in ADR 0016 first and restart all three consumers.

### 3.9 When something is refused

Every error has the body `{"error": {"code": "...", "message": "..."}}`. All codes are listed in [`grow8-backend/docs/error-codes.md`](grow8-backend/docs/error-codes.md).

---

## 4. Editor setup (VS Code)

The code runs in Docker, but VS Code analyses it with a Python interpreter on your machine. Out of the box that interpreter doesn't have FastAPI, SQLAlchemy and the other packages, so the editor shows false "import could not be resolved" errors. The fix is an **editor-only** virtual environment plus a workspace file.

> The `.venv` is only for autocomplete, type checking and linting. Keep running the app with `make up` and tests with `make test`.

### 4.1 One-time setup

1. Install **Python 3.12**, the same version as the containers.
2. Create the venv from `grow8-backend/`:

   ```bash
   make venv
   ```

   Without make, in PowerShell: `.\scripts\setup-venv.ps1`. If scripts are blocked: `powershell -ExecutionPolicy Bypass -File .\scripts\setup-venv.ps1`.
3. In VS Code: **File → Open Workspace from File…** → `grow8.code-workspace` at the **repository root**, next to `README.md`.
4. Install the recommended extensions when prompted (Python, Pylance, Ruff).

The workspace's first folder is the repository root (`GROW-8`), so Source Control and git work as usual. It also opens `api`, `shared` and each service as its **own folder**. That matters because the API and all three services each have a package called `app`; as separate folders, each `from app...` import resolves to the right one.

The workspace also:

- points every folder at `grow8-backend/.venv`;
- formats with the same ruff version as `make fmt`;
- turns off VS Code's test runner, because tests need MySQL and RabbitMQ and run with `make test`.

### 4.2 Keeping it up to date

Re-run `make venv` whenever a pull changes a `requirements*.txt` file or `shared/pyproject.toml`. After it finishes, run **Python: Restart Language Server** (Ctrl+Shift+P) so Pylance picks up the changes. The venv installs from the same pinned files as the Docker images, so the versions match.

### 4.3 Troubleshooting

| Problem | Fix |
| --- | --- |
| Imports still unresolved | Make sure you opened `grow8.code-workspace` (repository root), not a plain folder. Then run **Python: Select Interpreter** in each folder and pick `grow8-backend/.venv`. |
| `Import "grow8_common..." could not be resolved` (other imports fine) | Your venv was created before `make venv` installed `shared` in Pylance-compatible mode. Run `make venv` again, then **Python: Restart Language Server** (Ctrl+Shift+P). |
| macOS / Linux: interpreter not found | The workspace uses the Windows path `.venv/Scripts/python.exe`. Run **Python: Select Interpreter** → `grow8-backend/.venv/bin/python`, or set `python.defaultInterpreterPath` in your user settings. |
| `Python 3.12 not found` | Install 3.12, or point the script at it: `PYTHON=/path/to/python3.12 make venv`. |
| Source Control shows no repository | Open the workspace file from the repository root, not a copy elsewhere. If VS Code asks whether to open the repository in a parent folder, choose **Yes**. |
| Tests fail when run from the editor | Expected. Tests run inside Docker; use `make test`. |

---

## 5. Adding a Python package

Packages are declared in requirement files and installed when the Docker images are built. **Don't `pip install` inside a running container:** the package goes into a temporary location, disappears when the container is recreated, and your teammates never get it.

### 5.1 Pick the right file

Where the package is used decides where it goes (paths relative to `grow8-backend/`):

| Used by | File |
| --- | --- |
| API code only | `api/requirements.txt` |
| API tests or tooling only (e.g. a pytest plugin) | `api/requirements-dev.txt` |
| Shared code in `grow8_common` (used by the API and the services) | `dependencies` list in `shared/pyproject.toml` |
| One consumer service only | `services/<service_name>/requirements.txt` |
| A service's tests or tooling only | `services/<service_name>/requirements-dev.txt` |

### 5.2 Pin an exact version and say why

Always pin with `==`, and add a short comment explaining why the package is needed. To see the available versions:

```bash
docker compose exec api pip index versions <package>
```

Example entry in `api/requirements.txt`:

```text
# send transactional emails (notifications feature)
some-package==1.2.3
```

In `shared/pyproject.toml`, the same goes into the `dependencies` list: `"some-package==1.2.3",`.

### 5.3 Rebuild and check

From `grow8-backend/`:

```bash
make up                              # rebuilds the images that use the changed file
docker compose exec api pip check    # reports dependency conflicts, if any
make test                            # and make test-services if a service changed
make venv                            # so VS Code also knows the package
```

### 5.4 Commit and tell the team

Commit the requirements change **together with the code that uses it**, and mention the new package in your PR. After pulling, teammates run:

```bash
make up      # rebuild the images
make venv    # update the editor venv
```

### 5.5 Trying a package before adding it

To experiment without changing anything, use a throwaway container that is deleted afterwards:

```bash
docker compose run --rm --no-deps api sh -c "pip install <package> && python -c 'import <package>'"
```

Once you decide to keep it, add it properly using steps 5.1–5.4.
