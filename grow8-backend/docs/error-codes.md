# GROW8 API error codes

Every error response has the same body. `details` is present only when it helps.

```json
{ "error": { "code": "APPLICANT_LIMIT_REACHED", "message": "This opportunity has no places left" } }
```

Clients should branch on `code`, never on `message` (messages are for people and may change). A 401 response also carries `WWW-Authenticate: Bearer`.

## How statuses are used

| Status | Meaning in GROW8 |
| --- | --- |
| 401 | Who you are couldn't be established (no token, bad token, wrong password). |
| 403 | You are signed in, but your role or ownership doesn't allow this. Used when the target is public, so hiding it would be pointless. |
| 404 | Doesn't exist, **or** exists but you may not know about it (someone else's draft, application or notification). The two cases are deliberately indistinguishable. |
| 409 | The request is valid, but the current state doesn't allow it (a business rule). Retrying won't help until the state changes. |
| 411 / 413 / 415 | Upload problems: no `Content-Length`, file too large, wrong file type. |
| 422 | The request itself is malformed or incomplete. Fix the input and retry. |

## Codes

### Authentication and roles

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 401 | `AUTH_REQUIRED` | any protected endpoint | No `Authorization: Bearer` token. |
| 401 | `INVALID_TOKEN` | any protected endpoint | Token is malformed, expired, or its user no longer exists or is inactive. Sign in again. |
| 401 | `INVALID_CREDENTIALS` | `POST /auth/login` | Wrong email or password (the two are not told apart). |
| 401 | `INVALID_CURRENT_PASSWORD` | `POST /auth/change-password` | `current_password` is wrong. The user stays signed in; don't treat this as an expired session. |
| 403 | `ROLE_FORBIDDEN` | role-restricted endpoints | Your role can't do this (e.g. a contributor creating an opportunity, a creator applying). |

### Opportunities

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 403 | `NOT_OPPORTUNITY_OWNER` | `PATCH`, `DELETE`, `POST …/publish`, `…/close`, `…/cancel`, `GET …/applications` on `/opportunities/{id}` | The opportunity is public but belongs to another organization. |
| 404 | `OPPORTUNITY_NOT_FOUND` | any `/opportunities/{id}…` | Missing, or a draft you don't own. |
| 409 | `OPPORTUNITY_NOT_DRAFT` | `PATCH`, `DELETE`, `POST …/publish` | Only drafts can be edited, deleted or published ([ADR 0001](adr/0001-opportunity-draft-and-publish.md), [ADR 0004](adr/0004-only-drafts-can-be-deleted.md)). |
| 409 | `OPPORTUNITY_NOT_OPEN` | `POST …/close` | Only an open opportunity can be closed ([ADR 0011](adr/0011-close-and-cancel-opportunities.md)). |
| 409 | `OPPORTUNITY_NOT_PUBLISHED` | `POST …/cancel` | A draft can't be cancelled; delete it instead. |
| 409 | `OPPORTUNITY_CANCELLED` | `POST …/cancel` | It is already cancelled. |
| 409 | `WORK_ALREADY_SUBMITTED` | `POST …/cancel` | Work was submitted for one of its applications. |
| 409 | `ORGANIZATION_REQUIRED` | `POST /opportunities` | The creator account has no organization to post for. Create it with `PATCH /creators/me/organization` ([ADR 0018](adr/0018-creator-organization.md)). |
| 422 | `OPPORTUNITY_INCOMPLETE` | `POST …/publish` | Mandatory disclosures are missing; `details.missing_fields` lists them. |
| 422 | `DEADLINE_PASSED` | `POST …/publish` | The application deadline is not in the future. |
| 422 | `INVALID_DATES` | `POST`, `PATCH /opportunities` | `end_date` is before `start_date`. |
| 422 | `UNKNOWN_CATEGORY` | `POST`, `PATCH /opportunities` | The category code doesn't exist (see `GET /categories`). |
| 422 | `UNKNOWN_SKILL` | `POST`, `PATCH /opportunities`, `PUT /contributors/me/skills` | Skill code(s) don't exist; `details.unknown_skills` lists them (see `GET /skills`). |

### Applications ([ADR 0006](adr/0006-application-lifecycle.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `APPLICATION_NOT_FOUND` | `/applications/{id}…` | Missing, or not yours (only the applicant and the owning creator can see it). |
| 409 | `OPPORTUNITY_NOT_OPEN` | `POST /opportunities/{id}/applications` | The opportunity is closed or cancelled. |
| 409 | `APPLICATION_DEADLINE_PASSED` | `POST /opportunities/{id}/applications` | The application deadline has passed. |
| 409 | `APPLICANT_LIMIT_REACHED` | `POST /opportunities/{id}/applications` | Pending + accepted applications already fill `applicant_limit`. A place frees up if one is rejected or withdrawn. |
| 409 | `APPLICATION_DUPLICATE` | `POST /opportunities/{id}/applications` | You already applied (in any status, including withdrawn); `details.application_id` points to it when known. |
| 409 | `CONTRIBUTOR_PROFILE_REQUIRED` | `POST /opportunities/{id}/applications`, `PUT /contributors/me/resume` | The contributor account has no profile row yet. The message is "Save your profile first": the first `PATCH /contributors/me/profile` or `PUT /contributors/me/skills` creates it ([ADR 0017](adr/0017-contributor-profile.md)). |
| 409 | `APPLICATION_NOT_PENDING` | `POST /applications/{id}/decision` | It was already decided or withdrawn; each application is decided once. |
| 409 | `OPPORTUNITY_CANCELLED` | `POST /applications/{id}/decision` | The opportunity was cancelled, so its applications can't be decided ([ADR 0011](adr/0011-close-and-cancel-opportunities.md)). |
| 409 | `APPLICATION_NOT_ACTIVE` | `POST /applications/{id}/withdraw` | It is already rejected or withdrawn. |
| 409 | `WORK_ALREADY_SUBMITTED` | `POST /applications/{id}/withdraw` | Work was submitted for it, so it must stay accepted. |

### Resumes ([ADR 0008](adr/0008-contributor-resume.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `RESUME_NOT_FOUND` | `/contributors/me/resume…`, `GET /applications/{id}/resume` | The contributor has no resume (or its file is missing from storage). |
| 409 | `CONTRIBUTOR_PROFILE_REQUIRED` | `PUT /contributors/me/resume` | The contributor account has no profile row to attach it to yet ("Save your profile first"). |
| 411 | `LENGTH_REQUIRED` | `PUT /contributors/me/resume` | The upload was sent without `Content-Length` (e.g. chunked). Browsers always send it. |
| 413 | `RESUME_TOO_LARGE` | `PUT /contributors/me/resume` | Over 10 MB. Refused before the body is read when `Content-Length` shows it. |
| 415 | `UNSUPPORTED_FILE_TYPE` | `PUT /contributors/me/resume` | Not a PDF. Decided by the file's content, not its name or `Content-Type`. |
| 422 | `EMPTY_FILE` | `PUT /contributors/me/resume` | The file has no bytes. |

`GET /applications/{id}/resume` also returns `APPLICATION_NOT_FOUND` (404) when the application isn't yours to see.

### Work submissions ([ADR 0012](adr/0012-work-submission.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `APPLICATION_NOT_FOUND` | `POST`, `GET /applications/{id}/submission` | Missing, or not yours: only the applicant submits, and only the applicant and the owning creator can see the submission. |
| 404 | `SUBMISSION_NOT_FOUND` | `GET /applications/{id}/submission` | No work has been submitted for the application yet. |
| 404 | `ATTACHMENT_NOT_FOUND` | `GET /submissions/{id}/attachments/{attachment_id}` | Missing, not yours to see, or its file is missing from storage. |
| 409 | `APPLICATION_NOT_ACCEPTED` | `POST /applications/{id}/submission` | The application is pending, rejected or withdrawn. |
| 409 | `WORK_ALREADY_SUBMITTED` | `POST /applications/{id}/submission` | Work was already submitted for it; there is no resubmitting. |
| 409 | `OPPORTUNITY_CANCELLED` | `POST /applications/{id}/submission` | The opportunity was cancelled. |
| 411 | `LENGTH_REQUIRED` | `POST /applications/{id}/submission` | Sent without `Content-Length`. |
| 413 | `ATTACHMENT_TOO_LARGE` | `POST /applications/{id}/submission` | A file is over 5 MB. Refused before the body is read when `Content-Length` is over 5 × 5 MB. |
| 415 | `UNSUPPORTED_FILE_TYPE` | `POST /applications/{id}/submission` | A file isn't PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT. Decided by its content, not its name or `Content-Type`. |
| 422 | `EMPTY_FILE` | `POST /applications/{id}/submission` | A file has no bytes. |
| 422 | `TOO_MANY_FILES` | `POST /applications/{id}/submission` | More than 5 files. |

A missing or invalid `description` or `hours_claimed` is a `VALIDATION_ERROR`.

### Work verification ([ADR 0013](adr/0013-work-verification.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `SUBMISSION_NOT_FOUND` | `GET /submissions/{id}`, `POST /submissions/{id}/verification` | Missing, or not yours: only the owning creator verifies, and only the applicant and the owning creator can see the submission. A different creator trying to verify gets this too. |
| 409 | `SUBMISSION_ALREADY_VERIFIED` | `POST /submissions/{id}/verification` | It was already approved or rejected. Each submission is verified once and the decision is final. |
| 409 | `OPPORTUNITY_CANCELLED` | `POST /submissions/{id}/verification` | The opportunity was cancelled. |
| 422 | `VERIFIED_HOURS_EXCEED_CLAIMED` | `POST /submissions/{id}/verification` | Approving with more `verified_hours` than the contributor claimed. Fewer is fine. |
| 422 | `REJECTION_COMMENT_REQUIRED` | `POST /submissions/{id}/verification` | Rejecting without a `comment`, or with a blank one. |

Checked in this order: not found, already verified, cancelled, then the two 422s. A missing or invalid `decision`, `verified_hours` sent with a rejection, no `verified_hours` with an approval, hours that aren't > 0 with at most 2 decimals, or a comment over 2000 characters is a `VALIDATION_ERROR`. So is an unknown `status` filter on `GET /submissions/received`.

### Feedback and admin review ([ADR 0015](adr/0015-feedback-and-admin-review.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 403 | `ROLE_FORBIDDEN` | `GET /admin/feedback`, `POST /admin/feedback/{id}/review` | You aren't an admin. |
| 404 | `APPLICATION_NOT_FOUND` | `POST`, `GET /applications/{id}/feedback` | Missing, or you aren't the applicant or the owning creator. |
| 404 | `FEEDBACK_NOT_FOUND` | `POST /admin/feedback/{id}/review` | No such feedback. |
| 404 | `USER_NOT_FOUND` | `GET /users/{id}/rating` | No such user, or their account is inactive. |
| 409 | `WORK_NOT_VERIFIED` | `POST /applications/{id}/feedback` | No work was submitted yet, or the creator hasn't verified it. Feedback opens once the work is approved or rejected. |
| 409 | `FEEDBACK_ALREADY_SUBMITTED` | `POST /applications/{id}/feedback` | You already left feedback on this application; it can't be changed. |
| 409 | `FEEDBACK_ALREADY_REVIEWED` | `POST /admin/feedback/{id}/review` | It was already approved or rejected. Each feedback is reviewed once. |
| 422 | `REJECTION_REASON_REQUIRED` | `POST /admin/feedback/{id}/review` | Rejecting without a `reason`, or with a blank one. |

A `rating` that isn't a whole number from 1 to 5, a comment over 2000 characters, a reason over 500, an unknown field (the subject is never chosen by the client), or an unknown `status` or `discrepancy` filter is a `VALIDATION_ERROR`. Pending and rejected feedback never change a rating; the tests check this for each case.

### Reports and takedown ([ADR 0016](adr/0016-opportunity-reports-and-takedown.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 403 | `ROLE_FORBIDDEN` | `POST /opportunities/{id}/reports`, `GET /reports/mine`; `GET /opportunities/{id}/takedown`; `GET /admin/reports`, `POST /admin/reports/{id}/review` | Only contributors report; only creators see a takedown; only admins use the admin routes. |
| 404 | `OPPORTUNITY_NOT_FOUND` | `POST /opportunities/{id}/reports` | Missing, or a draft. |
| 404 | `REPORT_NOT_FOUND` | `POST /admin/reports/{id}/review` | No such report. |
| 404 | `OPPORTUNITY_NOT_FOUND` | `GET /opportunities/{id}/takedown` | Missing, or not one of your opportunities. |
| 404 | `TAKEDOWN_NOT_FOUND` | `GET /opportunities/{id}/takedown` | Your opportunity wasn't taken down (no upheld report). |
| 409 | `OPPORTUNITY_ALREADY_REPORTED` | `POST /opportunities/{id}/reports` | You already reported this opportunity (once, ever). |
| 409 | `OPPORTUNITY_CANCELLED` | `POST /opportunities/{id}/reports`; upholding on `POST /admin/reports/{id}/review` | The opportunity is cancelled (by its creator or a takedown). An admin can still dismiss reports on it. |
| 409 | `REPORT_ALREADY_REVIEWED` | `POST /admin/reports/{id}/review` | It was already upheld or dismissed. A takedown upholds every pending report on the opportunity, so those get this too. |
| 409 | `WORK_ALREADY_SUBMITTED` | upholding on `POST /admin/reports/{id}/review` | Work was submitted for one of its applications, so it can't be taken down (as for a creator's cancel, ADR 0011). The report stays pending; it can be dismissed. |
| 422 | `TAKEDOWN_REASON_REQUIRED` | `POST /admin/reports/{id}/review` | Upholding without a `reason`, or with a blank one. The creator is shown it. |

Checked in this order when reviewing: not found, already reviewed, reason required, then cancelled and work submitted. An unknown `reason` on a report, details over 2000 characters, a review reason over 500, an unknown field, or an unknown `status` filter on `GET /admin/reports` is a `VALIDATION_ERROR`.

### Creator organization ([ADR 0018](adr/0018-creator-organization.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `ORGANIZATION_NOT_FOUND` | `GET /creators/me/organization` | You have no organization yet. |
| 409 | `ORGANIZATION_REQUIRED` | `PATCH /creators/me/organization` | You have no organization yet, and this save doesn't send both `name` and `organization_type` to create it. |

A website that isn't an `http://` or `https://` address, or clearing `name` or `organization_type`, is a `VALIDATION_ERROR`.

### Account

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 422 | `PASSWORD_UNCHANGED` | `POST /auth/change-password` | The new password equals the current one, as bcrypt sees it: the first 72 bytes match ([ADR 0005](adr/0005-password-change.md)). |

A new password shorter than 8 characters or longer than 72 bytes (UTF-8) is a `VALIDATION_ERROR`.

Changing your name (`PATCH /auth/me`, `PATCH /contributors/me/profile`) has no codes of its own: an empty name, sending `email`, or more than 25 skills is a `VALIDATION_ERROR` ([ADR 0017](adr/0017-contributor-profile.md)).

### Notifications

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `NOTIFICATION_NOT_FOUND` | `PATCH /notifications/{id}/read` | Missing, or someone else's notification. |

### Generic

| Status | Code | When |
| --- | --- | --- |
| 422 | `VALIDATION_ERROR` | The body, query or path failed validation. `details` is a list of `{loc, message, type}`, one per problem. |
| 404 | `NOT_FOUND` | No such route. |
| 405 | `METHOD_NOT_ALLOWED` | The route exists but not with this HTTP method. |
| other | `HTTP_ERROR` | Any other framework-level HTTP error. |

An unexpected server error returns a plain-text 500 without this body or an `X-Request-ID` header. To trace one in the API logs, send your own `X-Request-ID` with requests and report that value.

## Adding a code

1. Raise the matching `AppError` subclass from `api/app/core/exceptions.py` with an explicit `code=` in `SCREAMING_SNAKE_CASE`, named after the rule (not the HTTP status).
2. Pick the status from the table above (409 for business rules, 422 for bad input, 411/413/415 for uploads).
3. Add a row here and a test that asserts the code.
