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

There is no sign-up endpoint yet; use the seeded dev accounts (see [docs.md](../../docs.md)).

## Reference data

| Method | Path | Who | Returns |
| --- | --- | --- | --- |
| GET | `/categories` | anyone | `[{code, name, description}]` (`knowledge`, `community`) |
| GET | `/skills` | anyone | `[{code, name}]` |

Use the `code` values in filters and when creating opportunities.

## Opportunities

Lifecycle: **draft** → (publish) → **open** → closed / cancelled (closing is not built yet).

| Method | Path | Who | Notes |
| --- | --- | --- | --- |
| GET | `/opportunities` | anyone | Public browse: only `open` opportunities whose deadline has not passed. Search, filter, sort, paginate (below). |
| GET | `/opportunities/mine` | creator | The caller's organization's opportunities in any status. Same parameters plus `status` (repeatable). Default sort `newest`. |
| GET | `/opportunities/{id}` | anyone | Drafts are visible only to their owner (others get 404). |
| POST | `/opportunities` | creator | Creates a **draft** for the caller's organization → 201. Drafts may be incomplete. |
| PATCH | `/opportunities/{id}` | owning creator | Edits a draft; only fields sent are changed. Non-draft → 409 `OPPORTUNITY_NOT_DRAFT`. |
| POST | `/opportunities/{id}/publish` | owning creator | Validates mandatory fields, sets `status=open` and `published_at`, commits, then emits `OPPORTUNITY_CREATED`. |

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

`opportunity_id` links to `GET /opportunities/{id}`. It is `null` if the opportunity was deleted. `title` and `message` are stored as written and don't change if the opportunity is edited later.

## Error codes

| Status | Code | When |
| --- | --- | --- |
| 401 | `AUTH_REQUIRED` | No token on a protected endpoint. |
| 401 | `INVALID_TOKEN` | Token invalid, expired, or user inactive. |
| 401 | `INVALID_CREDENTIALS` | Login failed. |
| 403 | `ROLE_FORBIDDEN` | Wrong role (e.g. contributor creating an opportunity). |
| 403 | `NOT_OPPORTUNITY_OWNER` | Changing another organization's (non-draft) opportunity. |
| 404 | `OPPORTUNITY_NOT_FOUND` | Missing, or a draft you don't own. |
| 404 | `NOTIFICATION_NOT_FOUND` | Missing, or someone else's notification. |
| 409 | `OPPORTUNITY_NOT_DRAFT` | Editing or publishing a non-draft. |
| 409 | `ORGANIZATION_REQUIRED` | Creator account has no organization. |
| 422 | `VALIDATION_ERROR` | Body or query failed validation (`details` lists each problem). |
| 422 | `OPPORTUNITY_INCOMPLETE`, `DEADLINE_PASSED`, `UNKNOWN_CATEGORY`, `UNKNOWN_SKILL`, `INVALID_DATES` | See above. |
