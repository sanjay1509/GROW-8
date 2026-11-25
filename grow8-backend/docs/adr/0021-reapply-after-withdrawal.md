# ADR 0021: A contributor who withdrew can apply again

- **Status:** accepted
- **Date:** 2026-11-25
- **Amends:** [ADR 0006](0006-application-lifecycle.md) decision 1 ("No re-applying", and `withdrawn` being final).

## Context

ADR 0006 made one application per contributor and opportunity final: after withdrawing, a contributor could never apply to that opportunity again. Commit `ffcb35a` changed this so that a contributor who changed their mind can apply again. The API contract was updated, but the design record still forbade it (#50).

## Decision

1. **Only a withdrawn application can be re-opened, and only if no work was submitted for it.** A rejected application stays final: the creator already said no. (Withdrawing is refused once work is submitted, so a withdrawn application normally never has a submission; the check is kept as a safeguard.)
2. **The same row is reused, never duplicated.** `uq_application_contributor_opportunity` still holds, the application keeps its id, and `POST /opportunities/{id}/applications` returns it with 201. Applying again while the application is `pending` or `accepted` is still 409 `APPLICATION_DUPLICATE`.
3. **Re-applying is a new application in every other way:**
   - the opportunity must be `open` and before its deadline, with a free place: the same checks and 409s as a first application, under the same opportunity row lock;
   - status goes back to `pending`. `submitted_at` becomes now, `decided_at` is cleared, and `motivation`, `application_details` and the resume copy are replaced. The old resume file is deleted after the commit ([ADR 0020](0020-application-resume-copies.md));
   - `APPLICATION_SUBMITTED` is published again, so the creator is notified.
4. **The database still checks it.** `application_immutable` lets `submitted_at` change only on withdrawn → pending, for the same contributor and opportunity. Every other change to the contributor, opportunity or `submitted_at` is still refused. The capacity trigger already re-checks a free place whenever a rejected or withdrawn application becomes active again.

## Consequences

- A withdrawal is no longer final for the contributor. The creator sees the application again as pending, and its earlier decision time is gone.
- Earlier motivations and answers aren't kept. Only the latest application is stored, consistent with "one application per contributor and opportunity".
- Covered by `test_withdrawn_contributor_can_apply_again_on_the_same_application` (`test_applications.py`) and the re-apply cases in `test_application_resume_files.py`.
