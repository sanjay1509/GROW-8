# CLAUDE.md – GROW8 Backend

Instructions for Claude Code working in this repository. Read this file fully before making changes. If a task conflicts with it, stop and ask rather than silently deviating.

## 1. What this project is

GROW8 ("Earn, Learn and Grow") is a web platform (ENSF 607 / ENSF 608 team project, UN SDG 8) that connects people who need short-term work done (**Creators**: small businesses, nonprofits, event organizers) with students and early-career workers (**Contributors**) who want verifiable experience. **Admins** moderate feedback.

This repo is the **backend only**. The React frontend lives elsewhere; do not create or modify frontend code here.

Out of scope: payment processing. Compensation is disclosed on opportunities but arranged off-platform. Never add payment, wallet, or checkout logic.

## 2. Architecture (do not change without approval)

Event-driven:

```
React ──REST──▶ FastAPI (producer) ──commit──▶ MySQL
                    │
                    └──publish──▶ RabbitMQ (topic exchange) ──▶ creator_service
                                                            ├─▶ contributor_service
                                                            └─▶ admin_service
```

- **api/** – FastAPI. Validates requests, applies business rules, commits to MySQL, **then** publishes an event.
- **services/creator_service, contributor_service, admin_service** – independent Python consumer processes (no HTTP). Each owns its own queue and handlers.
- **shared/grow8_common/** – installable package used by the API and all three services: settings, SQLAlchemy session, ORM models, event schemas, RabbitMQ connection/topology/consumer base. It is the single source of truth for these; never duplicate them per service.
- **MySQL** – one shared instance (deliberate scope simplification). Schema source of truth is `db/init/001_schema.sql`.
- **RabbitMQ** – one topic exchange `grow8.events` (name from `RABBITMQ_EXCHANGE`).

## 3. Repository layout

```
grow8-backend/
├── CLAUDE.md
├── docker-compose.yml            # prod-like stack
├── docker-compose.override.yml   # dev: hot reload + bind mounts (auto-applied)
├── .env.example                  # copy to .env (never commit .env)
├── Makefile
├── api/
│   ├── Dockerfile
│   ├── requirements.txt / requirements-dev.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, router registration, /health
│   │   ├── core/                 # config, security (JWT, hashing), exceptions
│   │   ├── dependencies/         # auth + role guards, DB session dependency
│   │   ├── routers/              # thin HTTP layer only
│   │   ├── schemas/              # Pydantic request/response models
│   │   ├── services/             # business rules + transactions
│   │   ├── repositories/         # all SQL / ORM queries
│   │   └── events/publisher.py   # publish with retry
│   └── tests/{unit,integration}/
├── services/
│   ├── creator_service/    {Dockerfile, app/{main.py, consumer.py, handlers/}, tests/}
│   ├── contributor_service/{Dockerfile, app/{main.py, consumer.py, handlers/}, tests/}
│   └── admin_service/      {Dockerfile, app/{main.py, consumer.py, handlers/}, tests/}
├── shared/
│   ├── pyproject.toml
│   └── grow8_common/{config, db, models, events, messaging, logging}/
├── db/init/                  # 001_schema.sql, 002_seed.sql (run by MySQL on first start)
├── tests/{postman/, reports/}
├── docs/{architecture.md, events.md, api-contract.md, adr/}
└── scripts/
```

Layering rule inside `api/app`: **router → service → repository**. Routers never contain business rules or queries. Services never build HTTP responses. Repositories never decide business policy.

## 4. Commands

Everything runs through Docker. Do not rely on a host Python install.

```bash
make env          # create .env from .env.example if missing
make up           # build + start mysql, rabbitmq, api, 3 consumers (detached)
make down
make logs
make reset-db     # destroys the MySQL and file_storage volumes so db/init/*.sql re-runs
make test         # pytest inside the api container
make mysql        # MySQL shell
```

URLs (defaults): API <http://localhost:8000> (Swagger at `/docs`), RabbitMQ UI <http://localhost:15672>, MySQL on host port 3307.

## 5. Docker rules

- Build context for every image is the **repo root** (the shared package is copied in). Each Dockerfile is at `<service>/Dockerfile`. Keep it that way.
- Install `shared/` with `pip install` in every image; do not copy `grow8_common` by hand.
- Containers run as a non-root user. Do not add `USER root` or bake secrets into images.
- Config comes only from environment variables (see `.env.example`). Inside Docker the hosts are `mysql` and `rabbitmq`, never `localhost`.
- Any new env var must be added to **both** `.env.example` and the relevant `docker-compose.yml` service.
- Every long-running dependency has a healthcheck; app services use `depends_on: condition: service_healthy`.
- Consumers must reconnect to RabbitMQ and MySQL with backoff on startup/failure (use `tenacity`), not crash-loop.
- After changing Dockerfiles, compose files, or dependencies, run `docker compose config -q` and `make build`.

## 6. Stack and conventions

- Python 3.12, FastAPI, SQLAlchemy 2.x (typed `Mapped[...]` style), PyMySQL, Pydantic v2, `pika` for RabbitMQ, pytest.
- Type hints on all functions. Format/lint with `ruff`. Keep functions small; prefer explicit over clever.
- REST under `/api/v1`. Plural nouns, JSON bodies, `snake_case` fields.
- Auth: JWT bearer, bcrypt password hashes, role claim in the token (`creator` | `contributor` | `admin`). Role guards are FastAPI dependencies; enforce **ownership** too (e.g. a Creator can only manage their own organization's opportunities).
- Errors: consistent body `{"error": {"code": "...", "message": "..."}}`; use 400/401/403/404/409/422 correctly (409 for duplicate application, capacity full, etc.).
- List endpoints are paginated (`limit`, `offset`) and filterable where useful (category, status, skill).
- Never log secrets, tokens, or password hashes. Never return password hashes.

## 7. Events

### Envelope (all events)

```json
{
  "event_id": "uuid4",
  "event_type": "WORK_VERIFIED",
  "version": 1,
  "occurred_at": "ISO-8601 UTC",
  "correlation_id": "request id",
  "payload": { }
}
```

Routing key = event type lower-cased with dots, e.g. `work.verified`. Define types and Pydantic payload schemas in `shared/grow8_common/events/`. Producers and consumers import from there; never hand-write event JSON elsewhere.

### Catalog

| Event | Published by | Consumed by | Behaviour |
| --- | --- | --- | --- |
| `OPPORTUNITY_CREATED` | creator action | contributor_service | Notify contributors of new opportunity |
| `APPLICATION_SUBMITTED` | contributor action | creator_service | Notify creator of new application |
| `APPLICATION_DECIDED` | creator action | contributor_service | Notify contributor of accept/reject |
| `WORK_SUBMITTED` | contributor action | creator_service | Notify creator work awaits verification |
| `WORK_VERIFIED` | creator action | contributor_service | Update verified hours and skills |
| `WORK_REJECTED` | creator action | contributor_service | Notify contributor of rejection |
| `FEEDBACK_SUBMITTED` | creator or contributor | admin_service | Alert admins of feedback awaiting review |
| `FEEDBACK_APPROVED` | admin action | all three services | Public ratings updated; notify author and subject |
| `FEEDBACK_REJECTED` | admin action | all three services | Record rejection; notify author and subject |

### Rules

1. **Commit first, publish second.** Never publish inside an open transaction and never publish an event for state that was not committed.
2. Failed publishes are retried (bounded retries with backoff, then logged loudly). A transactional outbox is explicitly **future work**: do not build it unless asked, but keep publishing behind `events/publisher.py` so it can be swapped later.
3. **Consumers are idempotent.** RabbitMQ is at-least-once. Dedupe by `event_id` or by naturally idempotent writes (e.g. verified hours must never be added twice for the same verification).
4. Manual acks: ack only after the handler succeeds; nack/dead-letter poison messages instead of looping forever. Declare a dead-letter exchange and queue per consumer.
5. Each service has a durable queue (`creator_service.q`, `contributor_service.q`, `admin_service.q`) bound only to the routing keys it needs. Topology lives in `grow8_common/messaging/topology.py`.
6. Handlers are one file per event under `handlers/` and contain no AMQP code (that stays in `consumer.py`/shared base).

## 8. Domain rules to enforce (in `api/app/services`)

- Mandatory opportunity fields must validate before an opportunity can be **published**: category, requirements, duration, expected hours, compensation disclosure, applicant limit, deadline, working conditions, **safety information**, accessibility details.
- Two categories: knowledge-based and community (via `OpportunityCategory`).
- No duplicate applications: unique (`contributor`, `opportunity`). Reject applications after the deadline, when the opportunity is not open, or when applicant capacity is reached. Capacity checks must be race-safe (transaction + row lock, e.g. `SELECT ... FOR UPDATE`).
- Only the owning Creator may decide applications and verify work.
- Work submission only for **accepted** applications; at most one submission per application in the MVP; attachments are metadata + storage key only (files are stored outside MySQL).
- **Uploaded files** (resumes, attachments) go through the `FileStorage` interface onto the `file_storage` Docker volume (ADR 0007): server-generated keys only, write the file before committing its row, delete replaced files after the commit.
- Verified hours count **only for approved work** (a `WorkVerification` with approved status). Verifying twice must not double count.
- Feedback only between participants of a real application. **Only Admin-approved feedback affects public Creator ratings.** Compute average ratings from approved feedback only.
- Admin reviews feedback once; unreviewed feedback is "pending".
- Rewards (stretch goal, but the schema supports them from day one): points awarded once per verification or badge; leaderboard totals are **calculated** from `PointTransaction`, never stored.

## 9. Data model

17 entities (from the ENSF 608 proposal): `UserAccount`, `ContributorProfile`, `CreatorOrganization`, `OpportunityCategory`, `Opportunity`, `Skill`, `ContributorSkill`, `OpportunitySkill`, `Application`, `WorkSubmission`, `SubmissionAttachment`, `WorkVerification`, `Feedback`, `AdminReview`, `Badge`, `ContributorBadge`, `PointTransaction`.

- Write DDL in `db/init/001_schema.sql` with real PKs, FKs, `UNIQUE` constraints, `CHECK`s/ENUMs for status values, and sensible indexes (deadline, status, category, foreign keys). It must also satisfy the ENSF 608 deliverable, so keep it clean and normalized (3NF+).
- ORM models in `shared/grow8_common/models/` must mirror the DDL exactly. If you change one, change the other in the same commit.
- `002_seed.sql`: categories, a few skills, badge definitions, one admin user (dev only, clearly marked).
- There are no migration tools in the MVP. Schema change = edit the SQL + `make reset-db`. Tell the user when this wipes data.

## 10. Testing

- Unit tests (rules, services) and integration tests (API against the compose MySQL/RabbitMQ) under `api/tests/`; consumer handler tests under each service's `tests/`.
- Maintain a Postman collection in `tests/postman/` covering each role's happy path and the key failure cases (duplicate application, capacity full, unauthorized verification, unapproved feedback not affecting ratings).
- Save execution output/reports to `tests/reports/` (git-ignored except `.gitkeep`).
- A feature is not done until its rules have tests and `make test` passes.

## 11. How to work

1. **Plan before large work.** For anything touching more than one service or the schema, state a short plan first.
2. **Suggested build order:** (a) `db/init` schema + seed, (b) `shared` package (settings, session, models, event schemas, messaging), (c) API auth/RBAC + health, (d) opportunities + applications, (e) submissions + verifications, (f) feedback + admin review, (g) the three consumers, (h) tests/Postman, (i) stretch: rewards/leaderboard.
3. Make small, reviewable commits. Do not refactor unrelated code. Do not add dependencies without saying why; pin them in the right requirements file or `shared/pyproject.toml`.
4. After each step: run `docker compose config -q`, bring the stack up, hit `/health`, run tests. Report what you ran and what failed. Never claim something works without running it.
5. Keep `docs/events.md` and `docs/api-contract.md` in sync with the code when you add or change events or endpoints.
6. Record notable design decisions as short ADRs in `docs/adr/`.
7. Don't touch `.env`; edit `.env.example` instead. Never commit secrets.
8. Do not use destructive commands (`docker compose down -v`, `rm -rf`, dropping tables) unless the task needs it, and say so first.

## 12. Open questions (ask the user; don't guess)

- **Notification storage:** the 17-entity schema has no `Notification` table. Until told otherwise, consumers emit structured log lines for "notify" behaviours. If persisted in-app notifications are wanted, propose a `Notification` table first.
- **Public rating storage:** README lists "Ratings" as stored, the proposal says compute from approved feedback. Default: compute on read via query; add a cached column only if asked.
- Whether rewards/leaderboard are built in this term (stretch goal) or schema-only.
