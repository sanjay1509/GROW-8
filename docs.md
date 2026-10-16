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
| A teammate's changes don't work for you after `git pull` | Run `make up` to rebuild, and compare your `.env` with `.env.example` for new settings. |

---

## 2. Database and seed data

### 2.1 Everyone gets the same database

The database is defined by three files in [`grow8-backend/db/init/`](grow8-backend/db/init/), which are committed to Git:

| File | What it does |
| --- | --- |
| `001_schema.sql` | Creates all 17 tables (the single source of truth for the schema). |
| `002_seed.sql` | Fills them with **development-only** placeholder data. It uses fixed IDs and dates, so every developer gets identical rows. |
| `003_test_database.sh` | Creates an empty `grow8_test` database that `make test` uses, so tests never change your dev data. |

MySQL runs these files automatically **the first time** it starts with an empty data volume. Anything you create later through Swagger, Postman or the frontend exists only on your machine.

### 2.2 After pulling database changes

MySQL does not re-run the files on an existing database. Whenever a pull changes anything in `grow8-backend/db/init/`, run:

```bash
cd grow8-backend
make reset-db
```

⚠️ This deletes everything in **your** local database and recreates it from the files. It does not affect anyone else.

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
- Keep seed data deterministic: explicit IDs, fixed dates, no `NOW()`.
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

Opportunities start as **drafts**, which can be incomplete. Publishing checks that every mandatory disclosure is filled in (requirements, dates, hours, compensation, applicant limit, deadline, working conditions, safety and accessibility information). If anything is missing, the response lists it.

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
