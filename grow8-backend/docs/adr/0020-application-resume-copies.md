# ADR 0020: Each application keeps its own copy of the resume

- **Status:** accepted
- **Date:** 2026-11-25
- **Amends:** [ADR 0008](0008-contributor-resume.md) decision 5 (creators saw the contributor's current resume). Builds on [ADR 0007](0007-local-file-storage.md) (file storage).

## Context

ADR 0008 let creators download the contributor's **current** profile resume through an application. Since commit `f0ab681`, applying takes `multipart/form-data` with an optional `resume` file, and every application stores a resume of its own (`application.resume_file_name`, `resume_content_type`, `resume_size_bytes`, `resume_storage_key`). The code review (#48) found that these files were never deleted when an apply failed or a re-application replaced them, and that the change had no design record.

## Decision

1. **An application keeps the resume it was sent with.** When applying:
   - a `resume` sent with the application (PDF, at most 10 MB, the same checks as the profile resume) is stored for that application only. The profile resume isn't changed;
   - otherwise, the profile resume is copied, if there is one. If its file is missing from storage, the application is saved without a resume and a warning is logged;
   - otherwise, the application has no resume.

   The creator sees the resume as it was when the contributor applied, even if the profile resume changes later.
2. **Downloads** (`GET /applications/{id}/resume`, applicant or owning creator) return the application's copy. Applications made before this change have no copy, so they fall back to the current profile resume, as in ADR 0008.
3. **No orphan files** (ADR 0007's rule, now applied here):
   - the copy is written before the row is committed. If the database refuses the row (for example, a race fills the last place) or the commit fails, the copy is deleted again;
   - re-applying after a withdrawal replaces the application's copy, and the old file is deleted after the commit;
   - an upload that fails partway leaves no partial file (`LocalFileStorage.save` writes to a temporary file and renames it).
4. **Copies stay with the application.** Deleting or replacing the profile resume doesn't touch them, because they are part of the application record, which only the applicant and the owning creator can see. Removing them on account deletion is future work, together with account deletion itself.
5. Copies are stored under the `applicationresumes/` prefix on the `file_storage` volume. No schema change beyond the four `application` columns already added.

## Consequences

- Storage grows by one resume per application when a contributor has a profile resume. That's acceptable at this scale (10 MB at most each).
- The behaviour is covered by `test_application_resume_files.py`.
