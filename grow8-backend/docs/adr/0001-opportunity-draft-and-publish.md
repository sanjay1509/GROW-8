# ADR 0001: Opportunities are created as drafts and published separately

- **Status:** accepted
- **Date:** 2026-10-16

## Context

Opportunities have ten mandatory disclosures (requirements, duration, expected hours, compensation, applicant limit, deadline, working conditions, safety information, accessibility details) that must be validated "before an opportunity can be published". Creators often fill these in over several sittings. The catalog also has an `OPPORTUNITY_CREATED` event meant to notify contributors.

## Decision

- `POST /opportunities` always creates a **draft**. Drafts may be incomplete and are visible only to their owner.
- `PATCH /opportunities/{id}` edits drafts only. Editing a published opportunity is not allowed in the MVP, so applicants never see terms change under them.
- `POST /opportunities/{id}/publish` checks the mandatory fields (and a future deadline), sets `status=open` and `published_at`, commits, then emits `OPPORTUNITY_CREATED`.
- The same completeness rule is a MySQL `CHECK` (`chk_opportunity_published_complete`), so no code path can store an incomplete non-draft.
- `OPPORTUNITY_CREATED` is emitted on **publish**, not on draft creation, because that is when contributors can act on it.

## Consequences

- Duration is stored as `start_date` + `end_date` (both required to publish).
- Location and work mode are optional because they are not in the mandatory list.
- Changing a published opportunity, closing and cancelling will need their own endpoints and events later.
