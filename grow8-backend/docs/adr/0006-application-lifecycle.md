# ADR 0006: Application lifecycle, capacity and errors

- **Status:** accepted; decision 1 amended by [ADR 0021](0021-reapply-after-withdrawal.md) (a withdrawn application can be re-opened)
- **Date:** 2026-11-15

## Context

Applications connect a contributor to an opportunity, and everything later in the workflow (work submission, verification, verified hours and skills, feedback, points) hangs off an accepted application. The schema already enforces the core rules with triggers (`trg_application_bi/bu` in `001_schema.sql`, "decision 4" in `docs/db/relationship-validation.md`): apply only to an `open` opportunity, no later than its deadline, while pending + accepted applications are below `applicant_limit`; one application per contributor and opportunity (`uq_application_contributor_opportunity`); and an accepted application with submitted work can't leave `accepted` (R9). The API had to decide who may do what, and how those rules surface to clients.

## Decision

1. **States and who moves them:**

   ```text
   pending ──(creator accepts)──▶ accepted
      │   └─(creator rejects)──▶ rejected
      └─(contributor withdraws)─▶ withdrawn ◀─(contributor withdraws)── accepted
   ```

   - The **owning creator** decides each application **once**, while it is `pending`. Deciding is allowed after the deadline and after the opportunity closes: the window applies to applying, not to choosing. *Not after it is cancelled: [ADR 0011](0011-close-and-cancel-opportunities.md).*
   - The **applicant** may withdraw while the application is `pending` or `accepted`, **until work is submitted** for it. After that, R9 keeps it `accepted` (verified hours, skills and feedback rely on it), so withdrawing returns 409 `WORK_ALREADY_SUBMITTED`. `rejected` and `withdrawn` are final: 409 `APPLICATION_NOT_ACTIVE`. *Amended by [ADR 0021](0021-reapply-after-withdrawal.md): the contributor can re-open a withdrawn application by applying again.*
   - **No auto-reject.** When the last place is filled, the remaining pending applications stay pending; the creator decides each one.
   - **No re-applying.** The unique key means a contributor who withdrew (or was rejected) cannot apply to the same opportunity again. Re-opening an application is future work. *Superseded by [ADR 0021](0021-reapply-after-withdrawal.md): applying again re-opens a withdrawn application (not a rejected one).*
2. **Capacity counts pending + accepted.** Rejecting or withdrawing frees a place. Accepting doesn't change the count, so it never fails on capacity.
3. **Checked twice, reported once.** The service locks the opportunity row (`SELECT … FOR UPDATE`), counts active applications with a locking read, and refuses with a clear error before writing. The triggers check the same rules again, so a race the service can't see ends in the same error, never a 500: `app/repositories/db_errors.py` recognises trigger errors (MySQL 1644, message prefixed with the rule name) and the duplicate key, and the service maps them to the codes below.
4. **409 for every business-rule refusal**: `OPPORTUNITY_NOT_OPEN`, `APPLICATION_DEADLINE_PASSED`, `APPLICANT_LIMIT_REACHED`, `APPLICATION_DUPLICATE`, `APPLICATION_NOT_PENDING`, `APPLICATION_NOT_ACTIVE`, `WORK_ALREADY_SUBMITTED`, `CONTRIBUTOR_PROFILE_REQUIRED`. The request is valid; the current state doesn't allow it. 422 stays for malformed input.
5. **Applications are private to their two parties.** Only the applicant and the creator who owns the opportunity can see one; to anyone else (including other creators) it is 404, so ids can't be probed. Listing an opportunity's applications is creator-owner only (another organization's public opportunity → 403 `NOT_OPPORTUNITY_OWNER`, as for editing).
6. **The creator sees the applicant's public profile**: name, headline, institution, city and skills. Email and other contact details are **not** shared; how the parties get in touch after acceptance is undecided.
7. **Events** (commit first, then publish):
   - `APPLICATION_SUBMITTED` → creator_service notifies the organization's owner (`application_submitted`).
   - `APPLICATION_DECIDED` → contributor_service notifies the applicant (`application_decided`).
   - **Withdrawing publishes nothing**: the event catalog (`docs/events.md`) has no withdrawal event. The creator sees the new status in the list. An `APPLICATION_WITHDRAWN` event is a possible follow-up. *Superseded by [ADR 0009](0009-application-withdrawn-event.md): withdrawing now notifies the creator.*
8. `submitted_at` and `decided_at` are set by the API from one clock (`utcnow()` without fractional seconds, since MySQL would round them and could date a row in the future). The trigger compares them with `NOW()`, which follows the session time zone, so the shared engine pins every connection to UTC (`SET time_zone = '+00:00'` in `grow8_common/db/session.py`). Otherwise, on a server with a local time zone behind UTC, every new application would look future-dated and fail with a 500. Added 2026-11-16 after review.

## Consequences

- `notification_type` gains `application_submitted` and `application_decided`. This is a schema change: each developer must run `make reset-db` (wipes local data). The ENSF 608 data dictionary lists the new values.
- New consumer bindings: `grow8.creator_service` ← `application.submitted`, `grow8.contributor_service` ← `application.decided`. They are declared when the services start.
- The API tests start from `002_seed.sql`, which has no applications; the race between two applicants for the last place is tested against the real database (`test_two_contributors_racing_for_the_last_place`).
- Error codes are listed in one place: [docs/error-codes.md](../error-codes.md).
