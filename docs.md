# GROW8 – Developer Documentation

This file covers how to work on GROW8 day to day. For project goals, architecture and team, see [README.md](README.md).

## Contents

1. [Running the application](#1-running-the-application)

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
  - Windows: run `make` from **Git Bash**. If `make` isn't found, install it (e.g. `winget install GnuWin32.Make` or `choco install make`) or use the `docker compose` commands.
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
| `make lint` | Check code style with ruff |
| `make fmt` | Auto-fix and format code with ruff |
| `make mysql` | Open a MySQL shell on the GROW8 database |
| `make config` | Validate the Docker Compose files |
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
| `port is already allocated` / `address already in use` | Another program is using port 8000, 3307, 5672 or 15672. Stop it, or change `API_HOST_PORT`, `MYSQL_HOST_PORT`, `RABBITMQ_HOST_PORT` or `RABBITMQ_MGMT_HOST_PORT` in your `.env` and run `make up`. |
| A container keeps restarting | `docker compose logs <container>` shows the error. |
| `/health` shows `"mysql":"unavailable"` right after startup | MySQL can take up to ~30 s on first start. Wait and refresh. |
| Code changes aren't picked up | If you changed dependencies, a Dockerfile or `.env`, run `make up`. Otherwise check `make logs` for an error that stopped the reload. |
| Database still has old tables after editing `db/init/*.sql` | The init scripts only run on an empty database. Run `make reset-db` (deletes local data). |
| A teammate's changes don't work for you after `git pull` | Run `make up` to rebuild, and compare your `.env` with `.env.example` for new settings. |
