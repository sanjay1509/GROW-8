# ADR 0008: One optional PDF resume per contributor, visible through applications

- **Status:** accepted; decision 5 amended by [ADR 0020](0020-application-resume-copies.md) (each application keeps its own copy)
- **Date:** 2026-11-15

## Context

Contributors want creators to see their experience without retyping it into every application. Resume upload is GROW8's first file upload. Storage is settled in [ADR 0007](0007-local-file-storage.md): a local volume behind a `FileStorage` interface, with metadata in MySQL. This ADR records the product rules on top of that.

## Decision

1. **Optional, one per contributor.** Applying never needs a resume. Uploading again replaces the old one (the row is updated and the old file deleted after the commit).
2. **A new 1 : 0..1 table, `contributor_resume`.** It shares the profile's key (`user_id` PK and FK → `contributor_profile`, `ON DELETE CASCADE`) and holds `file_name`, `content_type`, `size_bytes`, `storage_key` (`UNIQUE`) and `uploaded_at`. This mirrors `submission_attachment` and avoids five all-or-nothing nullable columns on `contributor_profile`. It is the 19th table.
3. **PDF only.** The type is decided by the file's signature (`%PDF-`), never by the client's `Content-Type` or the file name. A ZIP renamed to `.pdf` is refused with 415.
4. **At most 10 MB; empty files refused.** The limit is enforced twice:
   - up front by `BodySizeLimitMiddleware`, from `Content-Length` (an upload without one gets 411);
   - while copying, on the real file size.

   The database only checks `size_bytes > 0`; the cap is API policy, so changing it needs no schema change.
5. **Who can read it:**
   - the contributor;
   - the creator who owns an opportunity the contributor applied to, in **any** application status (withdrawn and rejected included, for the record);
   - to everyone else, 404 (the same as the application itself).

   Creators always get the contributor's **current** resume, not a copy from when they applied.
6. **The file name is for display only.** It is cut to its last path segment, stripped of control characters, at most 255 characters, and ends in `.pdf`. Downloads send it as an RFC 6266/5987 `Content-Disposition: attachment` with an ASCII fallback, plus `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`.
7. **Errors:** 413 `RESUME_TOO_LARGE`, 411 `LENGTH_REQUIRED`, 415 `UNSUPPORTED_FILE_TYPE`, 422 `EMPTY_FILE`, 404 `RESUME_NOT_FOUND`, 409 `CONTRIBUTOR_PROFILE_REQUIRED`.
8. **No event.** Nothing in the event catalog reacts to a resume, and no consumer needs the file.

## Consequences

- **Schema change:** `make reset-db`, which now also clears the `file_storage` volume. The ENSF 608 docs list `contributor_resume` (data dictionary, relational schema, functional dependencies). The ER diagram images need the new entity added by hand.
- `ApplicationRead.applicant.has_resume` tells the creator UI whether to show a download link.
- **Privacy:** if a contributor deletes their resume, creators lose access to it, even for past applications. Snapshotting a resume per application is future work if the record needs to be kept.
- **No malware scanning** (out of scope for the MVP). Files are only ever downloaded as attachments with `nosniff`, never rendered inline by the API.
- Covered by `api/tests/integration/test_resumes.py`, `api/tests/unit/test_local_storage.py` and `api/tests/unit/test_resume_rules.py`.
