# ADR 0002: Deterministic seed data, separate test database, full schema up front

- **Status:** accepted
- **Date:** 2026-10-16

## Context

Every developer runs their own MySQL in Docker. There are no migrations: MySQL runs `db/init/*.sql` only when its data volume is empty, so every schema change means each developer runs `make reset-db` and loses local data. The team wants everyone to see the same data while building the frontend and API.

## Decision

1. **All 17 tables are created now**, even those whose features come later, so the team pays the reset cost once instead of per feature.
2. **`002_seed.sql` is deterministic:** explicit primary keys and fixed dates (no `NOW()`), so every developer and every test run sees identical rows. It is clearly marked development-only. All seeded accounts share one dev password.
3. **Integration tests use a separate `grow8_test` database** (created by `003_test_database.sh`). Tests load the schema once and re-apply the seed before each test, so `make test` never changes the dev data and tests can rely on exact seed values.
4. **JWT secret:** `JWT_SECRET` may be empty in development (a built-in dev-only secret is used), so teammates' existing `.env` files keep working. With `APP_ENV=production` the API refuses to start without it.

## Consequences

- After pulling a change to `db/init/`, each developer must run `make reset-db` (wipes local data).
- Seeded deadlines are fixed dates, so in the dev database they expire as the term goes on (the public list shrinks); bump them in `002_seed.sql` if that gets in the way. Tests pin "now" to 2026-10-16 and are unaffected.
- Rows created through the UI, Swagger or Postman exist only on that developer's machine.
