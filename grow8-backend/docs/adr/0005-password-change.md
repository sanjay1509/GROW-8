# ADR 0005: Password changes re-check the current password and don't revoke tokens

- **Status:** accepted
- **Date:** 2026-11-15

## Context

The creator Settings and Profile pages let a signed-in user change their password through `POST /auth/change-password`. Three things needed deciding: how the caller proves it is really them, which error each failure returns, and what happens to access tokens issued before the change. Authentication is a stateless JWT (HS256, `sub` + `role` + `exp`, lifetime `ACCESS_TOKEN_EXPIRE_MINUTES`, default 60); the API keeps no session or token table.

## Decision

1. **The current password is required and re-checked** with bcrypt, even though the caller already has a valid token. A token left in an unattended browser or copied from `localStorage` must not be enough to take over the account.
2. **Error codes:**
   - Wrong current password → **401 `INVALID_CURRENT_PASSWORD`**. It is a failed proof of identity, like a failed login.
   - New password equal to the current one → **422 `PASSWORD_UNCHANGED`**. The request is well-formed but breaks a rule. The check is a plain string comparison, done after the current password has been verified.
   - New password shorter than 8 or longer than 128 characters → 422 `VALIDATION_ERROR` from the request schema. There are no other strength rules in the MVP.
3. **Existing tokens are not revoked.** They stay valid until they expire. Revoking them would need server-side state (a token version per user checked on every request, or a deny-list), which the stateless design deliberately avoids. The window is bounded by the token lifetime.
4. The service sets the new bcrypt hash and commits. No event is published: no other service reacts to a password change.

## Consequences

- If a password is changed because it leaked, an attacker who already holds a token keeps access until that token expires (up to 60 minutes by default). This is documented in `docs/api-contract.md`.
- Frontends must not treat every 401 as "session expired": on this endpoint 401 means the current password was wrong, and the user should stay signed in.
- bcrypt only uses the first 72 bytes of a password. With the pinned `bcrypt==4.3.0`, anything after byte 72 is silently ignored (a 73-byte password matches the hash of its first 72 bytes), so the 128-character limit allows passwords whose tail doesn't count. `bcrypt` 5.x raises `ValueError` instead, which would turn long passwords into 500s. Before upgrading `bcrypt`, cap passwords at 72 **bytes** (not characters) in the schemas, or pre-hash them.
- If revocation becomes necessary, the smallest change is a `token_version` column on `user_account`, included as a claim and compared in `get_current_user`. That is a schema change (`make reset-db` without migrations).
- Covered by the four `test_change_password_*` tests in `api/tests/integration/test_auth.py`.
