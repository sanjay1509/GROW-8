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
| 409 | `ORGANIZATION_REQUIRED` | `POST /opportunities` | The creator account has no organization to post for. |
| 422 | `OPPORTUNITY_INCOMPLETE` | `POST …/publish` | Mandatory disclosures are missing; `details.missing_fields` lists them. |
| 422 | `DEADLINE_PASSED` | `POST …/publish` | The application deadline is not in the future. |
| 422 | `INVALID_DATES` | `POST`, `PATCH /opportunities` | `end_date` is before `start_date`. |
| 422 | `UNKNOWN_CATEGORY` | `POST`, `PATCH /opportunities` | The category code doesn't exist (see `GET /categories`). |
| 422 | `UNKNOWN_SKILL` | `POST`, `PATCH /opportunities` | Skill code(s) don't exist; `details.unknown_skills` lists them (see `GET /skills`). |

### Applications ([ADR 0006](adr/0006-application-lifecycle.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `APPLICATION_NOT_FOUND` | `/applications/{id}…` | Missing, or not yours (only the applicant and the owning creator can see it). |
| 409 | `OPPORTUNITY_NOT_OPEN` | `POST /opportunities/{id}/applications` | The opportunity is closed or cancelled. |
| 409 | `APPLICATION_DEADLINE_PASSED` | `POST /opportunities/{id}/applications` | The application deadline has passed. |
| 409 | `APPLICANT_LIMIT_REACHED` | `POST /opportunities/{id}/applications` | Pending + accepted applications already fill `applicant_limit`. A place frees up if one is rejected or withdrawn. |
| 409 | `APPLICATION_DUPLICATE` | `POST /opportunities/{id}/applications` | You already applied (in any status, including withdrawn); `details.application_id` points to it when known. |
| 409 | `CONTRIBUTOR_PROFILE_REQUIRED` | `POST /opportunities/{id}/applications`, `PUT /contributors/me/resume` | The contributor account has no profile. |
| 409 | `APPLICATION_NOT_PENDING` | `POST /applications/{id}/decision` | It was already decided or withdrawn; each application is decided once. |
| 409 | `OPPORTUNITY_CANCELLED` | `POST /applications/{id}/decision` | The opportunity was cancelled, so its applications can't be decided ([ADR 0011](adr/0011-close-and-cancel-opportunities.md)). |
| 409 | `APPLICATION_NOT_ACTIVE` | `POST /applications/{id}/withdraw` | It is already rejected or withdrawn. |
| 409 | `WORK_ALREADY_SUBMITTED` | `POST /applications/{id}/withdraw` | Work was submitted for it, so it must stay accepted. |

### Resumes ([ADR 0008](adr/0008-contributor-resume.md))

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 404 | `RESUME_NOT_FOUND` | `/contributors/me/resume…`, `GET /applications/{id}/resume` | The contributor has no resume (or its file is missing from storage). |
| 409 | `CONTRIBUTOR_PROFILE_REQUIRED` | `PUT /contributors/me/resume` | The contributor account has no profile to attach it to. |
| 411 | `LENGTH_REQUIRED` | `PUT /contributors/me/resume` | The upload was sent without `Content-Length` (e.g. chunked). Browsers always send it. |
| 413 | `RESUME_TOO_LARGE` | `PUT /contributors/me/resume` | Over 10 MB. Refused before the body is read when `Content-Length` shows it. |
| 415 | `UNSUPPORTED_FILE_TYPE` | `PUT /contributors/me/resume` | Not a PDF. Decided by the file's content, not its name or `Content-Type`. |
| 422 | `EMPTY_FILE` | `PUT /contributors/me/resume` | The file has no bytes. |

`GET /applications/{id}/resume` also returns `APPLICATION_NOT_FOUND` (404) when the application isn't yours to see.

### Account

| Status | Code | Endpoint(s) | When |
| --- | --- | --- | --- |
| 422 | `PASSWORD_UNCHANGED` | `POST /auth/change-password` | The new password equals the current one, as bcrypt sees it: the first 72 bytes match ([ADR 0005](adr/0005-password-change.md)). |

A new password shorter than 8 characters or longer than 72 bytes (UTF-8) is a `VALIDATION_ERROR`.

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
