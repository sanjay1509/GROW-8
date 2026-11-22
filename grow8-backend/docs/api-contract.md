# GROW8 API contract

Base path: `/api/v1`. JSON bodies, `snake_case` fields. Interactive docs: <http://localhost:8000/docs>.

## Conventions

- **Auth:** `Authorization: Bearer <access_token>` from `POST /auth/login`. The token carries the user's role (`creator` | `contributor` | `admin`).
- **Times:** send ISO-8601 *with a timezone* (`2027-02-15T23:59:00-07:00`). Responses are always UTC (`...Z`).
- **Pagination:** list endpoints take `limit` (1–100, default 20) and `offset` (default 0) and return:
  ```json
  { "items": [...], "total": 42, "limit": 20, "offset": 0 }
  ```
- **Errors:** every error has the same body. `details` is present only when useful.
  ```json
  { "error": { "code": "OPPORTUNITY_INCOMPLETE", "message": "...", "details": { } } }
  ```
- **Request ID:** send `X-Request-ID` to correlate logs and events; the API generates one if absent and echoes it back.

## Auth

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| POST | `/auth/login` | anyone | Body `{email, password}`. Returns `{access_token, token_type, expires_in, user}`. Wrong email or password → 401 `INVALID_CREDENTIALS`. |
| GET | `/auth/me` | any signed-in user | The caller's `{user_id, email, full_name, role}`. |
| POST | `/auth/change-password` | any signed-in user | Body `{current_password, new_password}` (new: 8 characters to 72 bytes in UTF-8, bcrypt's limit). Wrong current password → 401 `INVALID_CURRENT_PASSWORD`; same as current → 422 `PASSWORD_UNCHANGED`. Tokens already issued stay valid until they expire ([ADR 0005](adr/0005-password-change.md)). |

There is no sign-up endpoint yet; use the seeded dev accounts (see [docs.md](../../docs.md)).

## Reference data

| Method | Path | Who | Returns |
| --- | --- | --- | --- |
| GET | `/categories` | anyone | `[{code, name, description}]` (`knowledge`, `community`) |
| GET | `/skills` | anyone | `[{code, name}]` |

Use the `code` values in filters and when creating opportunities.

## Opportunities

Lifecycle: **draft** → (publish) → **open** → (close) → **closed**; open or closed → (cancel) → **cancelled** ([ADR 0011](adr/0011-close-and-cancel-opportunities.md)).

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| GET | `/opportunities` | anyone | Public browse: only `open` opportunities whose deadline has not passed. Search, filter, sort, paginate (below). |
| GET | `/opportunities/mine` | creator | The caller's organization's opportunities in any status. Same parameters plus `status` (repeatable). Default sort `newest`. |
| GET | `/opportunities/{id}` | anyone | Drafts are visible only to their owner (others get 404). |
| POST | `/opportunities` | creator | Creates a **draft** for the caller's organization → 201. Drafts may be incomplete. |
| PATCH | `/opportunities/{id}` | owning creator | Edits a draft; only fields sent are changed. Non-draft → 409 `OPPORTUNITY_NOT_DRAFT`. |
| POST | `/opportunities/{id}/publish` | owning creator | Validates mandatory fields, sets `status=open` and `published_at`, commits, then emits `OPPORTUNITY_CREATED`. |
| POST | `/opportunities/{id}/close` | owning creator | `open` → `closed`: no new applications; pending ones can still be decided. No event. Not open → 409 `OPPORTUNITY_NOT_OPEN`. |
| POST | `/opportunities/{id}/cancel` | owning creator | `open`/`closed` → `cancelled`. Application statuses are kept; deciding is refused afterwards. Emits `OPPORTUNITY_CANCELLED` (pending and accepted applicants are notified). Draft → 409 `OPPORTUNITY_NOT_PUBLISHED`; already cancelled → 409 `OPPORTUNITY_CANCELLED`; work submitted → 409 `WORK_ALREADY_SUBMITTED`. |
| DELETE | `/opportunities/{id}` | owning creator | Deletes a **draft** → 204. Non-draft → 409 `OPPORTUNITY_NOT_DRAFT` (published opportunities are closed or cancelled instead, [ADR 0004](adr/0004-only-drafts-can-be-deleted.md)). |

### Search, filter and sort parameters (`GET /opportunities`, `/opportunities/mine`)

| Param | Example | Meaning |
| --- | --- | --- |
| `q` | `food bank` | Case-insensitive text in title, description or organization name. |
| `category` | `community` | Category code. |
| `skill` | `skill=photography&skill=translation` | Has **any** of these skill codes. |
| `work_mode` | `remote` | `on_site` \| `remote` \| `hybrid` |
| `compensation_type` | `unpaid` | `paid` \| `stipend` \| `unpaid` |
| `organization_id` | `2` | One organization's opportunities. |
| `min_hours`, `max_hours` | `min_hours=5&max_hours=20` | Expected-hours range (inclusive). `min_hours > max_hours` → 422. |
| `deadline_before` | `2026-12-01T00:00:00Z` | Application deadline before this time. |
| `sort` | `-deadline` | `deadline` (default for public), `-deadline`, `newest`, `oldest`, `hours`, `-hours`, `compensation`, `-compensation`, `title`. Ties are broken by id. |
| `status` | `status=draft` | `/mine` only; repeatable. |
| `limit`, `offset` | | Pagination. |

All filters combine with AND.

### Opportunity body (POST / PATCH)

POST requires `title` (3–200 chars), `description` and `category` (code). Everything else is optional while drafting:

`skills` (codes), `requirements`, `location`, `work_mode`, `start_date`, `end_date`, `expected_hours` (> 0), `compensation_type`, `compensation_amount` (≥ 0), `compensation_details`, `applicant_limit` (≥ 1), `application_deadline` (timezone required), `working_conditions`, `safety_information`, `accessibility_details`.

Unknown fields → 422. `end_date` before `start_date` → 422. Unknown category → 422 `UNKNOWN_CATEGORY`; unknown skill → 422 `UNKNOWN_SKILL` with `details.unknown_skills`.

### Publishing rules

To publish, these must be set: `requirements`, `start_date`, `end_date`, `expected_hours`, `compensation_type`, `applicant_limit`, `application_deadline`, `working_conditions`, `safety_information`, `accessibility_details`, plus `compensation_amount` when the type is `paid` or `stipend`. Otherwise → 422 `OPPORTUNITY_INCOMPLETE` with `details.missing_fields`. The deadline must be in the future (422 `DEADLINE_PASSED`). The same rule is enforced in MySQL by `chk_opportunity_published_complete`.

## Applications

A contributor applies to an open opportunity; the owning creator accepts or rejects it; the contributor can withdraw. Rules and reasons: [ADR 0006](adr/0006-application-lifecycle.md). All refusals are 409; see [error-codes.md](error-codes.md).

Lifecycle: **pending** → accepted / rejected (creator, once) · pending or accepted → **withdrawn** (contributor, until work is submitted).

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| POST | `/opportunities/{id}/applications` | contributor | Body `{motivation?}` (1–5000 chars) → 201. Only while the opportunity is `open`, before its deadline, and while pending + accepted applications are below `applicant_limit`. One application per opportunity, ever. Emits `APPLICATION_SUBMITTED`. |
| GET | `/opportunities/{id}/applications` | owning creator | Applications to your opportunity, newest first. `status` (repeatable), `limit`, `offset`. |
| GET | `/applications/mine` | contributor | Your applications, newest first. Same parameters. |
| GET | `/applications/received` | creator | Applications to all your opportunities, newest first. Same parameters plus `opportunity_id` (one of yours; another's matches nothing). |
| GET | `/applications/{id}` | the applicant or the owning creator | Anyone else → 404. |
| POST | `/applications/{id}/decision` | owning creator | Body `{decision: "accepted" \| "rejected"}`. Pending only (409 `APPLICATION_NOT_PENDING`). Allowed after the deadline and after closing, not after cancelling (409 `OPPORTUNITY_CANCELLED`). Emits `APPLICATION_DECIDED`. |
| POST | `/applications/{id}/withdraw` | the applicant | Pending or accepted only (409 `APPLICATION_NOT_ACTIVE`), and not once work is submitted (409 `WORK_ALREADY_SUBMITTED`). Frees the place. Emits `APPLICATION_WITHDRAWN` (the owning creator is notified). |

An application:

```json
{
  "application_id": 7,
  "status": "pending",
  "motivation": "I type fast and love bread.",
  "submitted_at": "2026-10-16T12:00:00Z",
  "decided_at": null,
  "opportunity": {
    "opportunity_id": 1,
    "title": "Digitize paper recipe archive",
    "status": "open",
    "application_deadline": "2026-11-20T23:59:59Z",
    "organization": { "organization_id": 1, "name": "Maple Street Bakery", "organization_type": "small_business", "city": "Calgary" }
  },
  "applicant": {
    "user_id": 5,
    "full_name": "Alex Chen",
    "headline": "Software engineering student",
    "institution": "University of Calgary",
    "city": "Calgary",
    "skills": [{ "code": "data-cleaning", "name": "Data cleaning" }, { "code": "spreadsheets", "name": "Spreadsheets" }, { "code": "web-basics", "name": "Web basics (HTML/CSS)" }],
    "has_resume": true
  },
  "submission_id": null,
  "work_status": "not_submitted"
}
```

The applicant's email and other contact details are not included. `applicant.has_resume` says whether `GET /applications/{id}/resume` has a file to return. `submission_id` is the submitted work's id, or `null` until the applicant submits work (see [Work submissions](#work-submissions)), so a list can show "Submit work" or "Submitted" without a call per application. `work_status` says where the work stands: `not_submitted` (also for every application that was never accepted), `awaiting_verification`, `completed` (the creator approved it) or `work_rejected`. It is derived, not stored ([ADR 0013](adr/0013-work-verification.md)).

## Resumes

A contributor can keep one optional PDF resume (at most 10 MB). Creators can download it through an application to one of their opportunities. Rules: [ADR 0008](adr/0008-contributor-resume.md); storage: [ADR 0007](adr/0007-local-file-storage.md).

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| PUT | `/contributors/me/resume` | contributor | `multipart/form-data` with one field, `file`. Creates or replaces your resume → 200 with its metadata. Must be a PDF (checked by content: 415 `UNSUPPORTED_FILE_TYPE`), non-empty (422 `EMPTY_FILE`), at most 10 MB (413 `RESUME_TOO_LARGE`), and sent with `Content-Length` (411 `LENGTH_REQUIRED`). |
| GET | `/contributors/me/resume` | contributor | Your resume's metadata, or 404 `RESUME_NOT_FOUND`. |
| GET | `/contributors/me/resume/file` | contributor | Downloads the PDF. |
| DELETE | `/contributors/me/resume` | contributor | → 204. Creators lose access too. |
| GET | `/applications/{id}/resume` | owning creator (or the applicant) | Downloads the applicant's **current** resume. Works for any application status. Anyone else → 404 `APPLICATION_NOT_FOUND`; no resume → 404 `RESUME_NOT_FOUND`. |

Metadata:

```json
{ "file_name": "Alex Chen CV.pdf", "content_type": "application/pdf", "size_bytes": 48213, "uploaded_at": "2026-11-15T22:10:04Z" }
```

`file_name` is for display only (cleaned, always ends in `.pdf`). Downloads are `application/pdf` with `Content-Disposition: attachment` (the name also sent as UTF-8 `filename*`), `X-Content-Type-Options: nosniff` and `Cache-Control: private, no-store`. `Content-Disposition` is exposed to cross-origin JavaScript (CORS), so a frontend that downloads with `fetch` can read the file name from it.

From a browser:

```js
const form = new FormData();
form.append("file", fileInput.files[0]);
await fetch(`${API}/contributors/me/resume`, { method: "PUT", body: form, headers: { Authorization: `Bearer ${token}` } });
```

Don't set `Content-Type` yourself; the browser adds the multipart boundary and `Content-Length`.

## Work submissions

An accepted contributor submits their work once, with optional files, for the owning creator to verify. Rules and reasons: [ADR 0012](adr/0012-work-submission.md); storage: [ADR 0007](adr/0007-local-file-storage.md).

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| POST | `/applications/{id}/submission` | the applicant | `multipart/form-data`: `description` (1–5000 chars), `hours_claimed` (> 0, at most 9999.99, 2 decimals), and up to 5 `files` (optional, repeat the field). → 201 with the submission. The application must be `accepted` (409 `APPLICATION_NOT_ACCEPTED`) and the opportunity not cancelled (409 `OPPORTUNITY_CANCELLED`; closed is fine). Once per application, no resubmitting (409 `WORK_ALREADY_SUBMITTED`). Emits `WORK_SUBMITTED` (the owning creator is notified). |
| GET | `/applications/{id}/submission` | the applicant or the owning creator | The submission with its attachments' metadata. Anyone else → 404 `APPLICATION_NOT_FOUND`; nothing submitted yet → 404 `SUBMISSION_NOT_FOUND`. |
| GET | `/submissions/{id}/attachments/{attachment_id}` | the applicant or the owning creator | Downloads the file. Anything you can't see or that doesn't exist → 404 `ATTACHMENT_NOT_FOUND`. |
| GET | `/submissions/received` | creator | Your review queue: submissions to all your opportunities, **oldest first**. `status` (repeatable: `awaiting`, `approved`, `rejected`; default all), `opportunity_id` (one of yours; another's matches nothing), `limit`, `offset`. |
| GET | `/submissions/{id}` | the applicant or the owning creator | The submission with its verification. Anyone else → 404 `SUBMISSION_NOT_FOUND`. |
| POST | `/submissions/{id}/verification` | owning creator | Approve or reject the work, once → 200 with the submission. See [Verifying work](#verifying-work). |

Files: PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT, at most 5 MB each (413 `ATTACHMENT_TOO_LARGE`), non-empty (422 `EMPTY_FILE`). The type is decided by the content (415 `UNSUPPORTED_FILE_TYPE`), and one bad file refuses the whole submission. More than 5 files → 422 `TOO_MANY_FILES`. The request needs `Content-Length` (411 `LENGTH_REQUIRED`).

A submission:

```json
{
  "submission_id": 6,
  "application_id": 12,
  "status": "approved",
  "description": "Typed up 40 recipes into the shared sheet.",
  "hours_claimed": "6.50",
  "submitted_at": "2026-11-18T15:00:00Z",
  "opportunity": { "opportunity_id": 2, "title": "Inventory spreadsheet cleanup", "status": "open" },
  "applicant": { "user_id": 5, "full_name": "Alex Chen" },
  "attachments": [
    { "attachment_id": 3, "file_name": "recipes.xlsx", "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "size_bytes": 23855, "uploaded_at": "2026-11-18T15:00:00Z" }
  ],
  "verification": { "decision": "approved", "verified_hours": "6.00", "comment": "Thanks, this is great.", "verified_at": "2026-11-19T10:00:00Z" }
}
```

`status` is `awaiting` (and `verification` is `null`) until the creator decides, then `approved` or `rejected`. `hours_claimed` and `verified_hours` are decimals sent as strings. `file_name` is for display only: cleaned, and always ending in an extension that matches the detected type. Downloads use the stored `content_type` with the same headers as resumes (`Content-Disposition: attachment`, `nosniff`, `no-store`).

From a browser:

```js
const form = new FormData();
form.append("description", "Typed up 40 recipes.");
form.append("hours_claimed", "6.5");
for (const file of fileInput.files) form.append("files", file);
await fetch(`${API}/applications/${applicationId}/submission`, { method: "POST", body: form, headers: { Authorization: `Bearer ${token}` } });
```

### Verifying work

The creator who owns the opportunity approves or rejects each submission once ([ADR 0013](adr/0013-work-verification.md)). `POST /submissions/{id}/verification`:

```json
{ "decision": "approved", "verified_hours": "6", "comment": "Thanks, this is great." }
```

```json
{ "decision": "rejected", "comment": "Only 10 of the 40 recipes are in the sheet." }
```

- **Approve:** `verified_hours` is required, > 0 with at most 2 decimals, and no more than `hours_claimed` (422 `VERIFIED_HOURS_EXCEED_CLAIMED`). Verifying fewer hours than claimed is fine. `comment` is optional.
- **Reject:** `comment` is required (422 `REJECTION_COMMENT_REQUIRED`) and `verified_hours` must be left out.
- `comment` is trimmed, at most 2000 characters.
- Once per submission, final (409 `SUBMISSION_ALREADY_VERIFIED`). Not once the opportunity is cancelled (409 `OPPORTUNITY_CANCELLED`); closed is fine. Another creator, or a submission that doesn't exist → 404 `SUBMISSION_NOT_FOUND`.
- Emits `WORK_VERIFIED` or `WORK_REJECTED`; the contributor is notified. Approved hours count toward the contributor's verified hours and skills from then on (computed by the database views, never stored).

## Notifications

Every signed-in user (any role) has an inbox. The consumer services write the notifications when events happen (see [events.md](events.md) and [ADR 0003](adr/0003-persisted-notifications.md)); the API only reads them and marks them read. You only ever see your own: someone else's `id` → 404, the same as one that doesn't exist.

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| GET | `/notifications` | any signed-in user | Your notifications, newest first. `unread_only=true` for the unread ones; paginated (`limit`, `offset`). |
| GET | `/notifications/unread-count` | any signed-in user | `{"unread_count": 3}`. Cheap; meant to be polled for a badge (e.g. every 30 s while the tab is visible). |
| PATCH | `/notifications/{id}/read` | the notification's user | Marks it read and returns it. Safe to repeat: a notification that is already read keeps its first `read_at`. |
| POST | `/notifications/read-all` | any signed-in user | Marks all your unread notifications read. `{"marked_read": 3}` (0 if there were none). |

A notification:

```json
{
  "notification_id": 12,
  "notification_type": "opportunity_created",
  "title": "New opportunity: Volunteer coordinator for spring market",
  "message": "Apply by 2027-02-28 23:59 UTC. Your matching skills: customer-service, event-setup.",
  "opportunity_id": 15,
  "read_at": null,
  "created_at": "2026-10-27T20:13:51Z",
  "is_read": false
}
```

| `notification_type` | Who gets it | When |
| --- | --- | --- |
| `opportunity_created` | contributors with a matching skill | An opportunity is published. |
| `opportunity_published` | the creator who owns it | Their opportunity is published. |
| `application_submitted` | the creator who owns the opportunity | A contributor applied. |
| `application_decided` | the contributor who applied | Their application was accepted or rejected. |
| `application_withdrawn` | the creator who owns the opportunity | An applicant withdrew; the message says if an accepted place opened up. |
| `opportunity_cancelled` | each pending or accepted applicant | The opportunity was cancelled. |
| `work_submitted` | the creator who owns the opportunity | An accepted applicant submitted their work for verification. |
| `work_verified` | the contributor who submitted the work | The creator approved it; the message gives the verified hours. |
| `work_rejected` | the contributor who submitted the work | The creator rejected it; the message quotes their comment. |

`opportunity_id` links to `GET /opportunities/{id}`. It is `null` if the opportunity was deleted. `title` and `message` are stored as written and don't change if the opportunity is edited later.

## Error codes

Every code, its status and when it happens: **[error-codes.md](error-codes.md)**. In short: 401 identity, 403 role or ownership on something public, 404 missing or hidden, 409 business rule, 422 bad input.

