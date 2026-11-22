# ADR 0018: Creators edit their own organization

- **Status:** accepted
- **Date:** 2026-11-22
- **Builds on:** [ADR 0017](0017-contributor-profile.md) (the same pattern for contributor profiles), [ADR 0006](0006-application-lifecycle.md) (people see each other's current details).

## Context

`creator_organization` (name, type, description, website, city) has been in the schema from the start, and its summary appears on every opportunity. But creators had no way to read or change theirs, so the frontend's **Organization profile** page (`/creator/profile`) had nothing to load or save. A creator can already change their own name with `PATCH /auth/me` (ADR 0017). Issue #33.

## Decision

1. **Two creator-only endpoints, on the caller's own organization** (one per creator, `uq_creator_organization_owner`). Contributors and admins get 403 `ROLE_FORBIDDEN`.
   - `GET /creators/me/organization` returns `{organization_id, name, organization_type, description, website, city, updated_at}`.
   - `PATCH /creators/me/organization` changes only the fields sent and returns the organization. The input rules are the same as ADR 0017:
     - whitespace is trimmed;
     - for the optional fields (`description`, `website`, `city`), `null` or `""` clears the value;
     - `name` and `organization_type` can't be cleared;
     - unknown fields are refused.

     All of these are 422 `VALIDATION_ERROR`.
2. **The website must be an `http://` or `https://` address with a host,** at most 255 characters, and is stored as sent. The frontend shows it as a link, so `javascript:` and other schemes must never get in.
3. **A creator without an organization creates it with their first save.** Seeded creators all have one, but an account might not.
   - `GET` returns 404 `ORGANIZATION_NOT_FOUND`.
   - A `PATCH` that sends both `name` and `organization_type` creates it.
   - Any other `PATCH` is 409 `ORGANIZATION_REQUIRED`, the same code `POST /opportunities` already uses for a creator without an organization.
4. **Saving locks the creator's account row first,** then the organization. The organization row can't be pre-inserted with a no-op upsert the way ADR 0017 does for profiles, because `name` and `organization_type` are required. The account row always exists, so two saves at once run one after the other. That includes two first saves: the second one edits the organization the first created, instead of failing on the unique key.
5. **Edits show on every opportunity straight away,** published and past ones included, because opportunity responses read the organization when they're loaded. That's intended: an opportunity shows who the creator is now, just as ADR 0006 shows applicants' current details. Notifications already sent keep the name they were written with.
6. **No events and no schema change.** No consumer reacts to an organization edit, and `trg_creator_organization_bi/bu` already check that the owner is a creator.

## Consequences

- The creator Organization profile page can load and save.
- Search by organization name (`q`) finds opportunities under the new name straight away.
- Out of scope: logos, more than one organization per creator, transferring ownership and a public organization page.
