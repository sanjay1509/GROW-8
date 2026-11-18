# ADR 0012: Work submission and attachments

- **Status:** accepted
- **Date:** 2026-11-17
- **Builds on:** [ADR 0006](0006-application-lifecycle.md) (accepted applications), [ADR 0007](0007-local-file-storage.md) (file storage), [ADR 0011](0011-close-and-cancel-opportunities.md) ("submitting work must lock the application row").

## Context

An accepted contributor needs a way to hand in their work, so the creator can verify it and the contributor's hours and skills can count. The schema has had `work_submission` and `submission_attachment` from the start, and the `trg_work_submission_bi/bu` triggers already refuse a submission for an application that isn't `accepted`. Withdrawing and cancelling already refuse once work is submitted (`WORK_ALREADY_SUBMITTED`). Nothing could create a submission yet.

## Decision

1. **Who and when.** Only the applicant submits, and only while the application is `accepted` and the opportunity isn't `cancelled`. A `closed` opportunity is fine: closing only stops new applications (ADR 0011).
2. **One submission per application, no resubmitting** (`uq_work_submission_application`). If the creator rejects the work, that decision is final. Allowing a second attempt would need a schema change and would complicate verified hours and points.
3. **One request.** `POST /applications/{id}/submission` is `multipart/form-data` with `description` (1–5000 characters), `hours_claimed` (> 0, two decimals) and up to **5** optional `files`.
4. **Attachments.** At most **5 MB each**. Allowed: PDF, PNG, JPEG, DOCX, XLSX, CSV, TXT. The type is decided from the file's content, never from its name or the client's `Content-Type`, and the detected type is what gets stored.
   - PDF, PNG and JPEG by their signature. DOCX and XLSX are ZIP archives with `[Content_Types].xml` and a `word/` or `xl/` part; any other ZIP is refused.
   - CSV and TXT must be UTF-8 with no control characters other than whitespace, judged on the first 8 KB. The name decides between the two (`.csv` or not).
   - The stored display name always ends in an extension that matches the detected type, so a text file named `notes.exe` downloads as `notes.exe.txt`. Files go through `FileStorage` under `submissions/<uuid>` keys (ADR 0007 anticipated an `attachments/` prefix; `submissions/` names the feature, as `resumes/` does), as in ADR 0007: write the files first, commit the rows second, and delete the written files if the commit fails.
5. **Concurrency.** Submitting locks the application row (`FOR UPDATE`), then takes a shared lock on the opportunity's status (`FOR SHARE`). This is the same order as deciding (ADR 0011 decision 5), so a submit and a withdraw or cancel are serialized and can't deadlock each other. The triggers and the unique key remain the backstop. Their errors map to the same 409 codes, never a 500.
6. **Visibility.** The applicant and the owning creator can see the submission and download its attachments. To anyone else the application doesn't exist (404), as in ADR 0006.
7. **New event `WORK_SUBMITTED` (v1)**, published after the commit. **creator_service** notifies the organization's owner that work is waiting for verification, with notification type `work_submitted`.

## Consequences

- `notification.notification_type` gains `work_submitted`: run `make reset-db` (wipes local data and uploaded files), or keep your data with:

  ```sql
  ALTER TABLE notification MODIFY notification_type ENUM('opportunity_created', 'opportunity_published', 'application_submitted', 'application_decided', 'application_withdrawn', 'opportunity_cancelled', 'work_submitted') NOT NULL;
  ```

  Restart creator_service so its queue gets the `work.submitted` binding.
- Application responses gain `submission_id` (`null` until work is submitted), so the frontend can tell which accepted applications still need work without a request per application.
- CORS exposes `Content-Disposition`, so a browser downloading an attachment (or a resume) with `fetch` can read its file name.
- The upload size middleware matches paths with an id (`/applications/{id}/submission`), not only fixed paths.
- New error codes: `APPLICATION_NOT_ACCEPTED`, `SUBMISSION_NOT_FOUND`, `ATTACHMENT_NOT_FOUND`, `ATTACHMENT_TOO_LARGE`, `TOO_MANY_FILES`. `WORK_ALREADY_SUBMITTED`, `OPPORTUNITY_CANCELLED`, `UNSUPPORTED_FILE_TYPE` and `EMPTY_FILE` gain an endpoint. See [error-codes.md](../error-codes.md).
- Verifying the work (approve with hours, or reject with a comment) is the next step and gets its own ADR.
