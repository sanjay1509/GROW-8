# ADR 0005: Password changes re-check the current password and don't revoke tokens

- **Status:** accepted
- **Date:** 2026-11-15

## Context

The creator Settings and Profile pages let a signed-in user change their password through `POST /auth/change-password`. Three things needed deciding: how the caller proves it is really them, which error each failure returns, and what happens to access tokens issued before the change. Authentication is a stateless JWT (HS256, `sub` + `role` + `exp`, lifetime `ACCESS_TOKEN_EXPIRE_MINUTES`, default 60); the API keeps no session or token table.

## Decision

1. **The current password is required and re-checked** with bcrypt, even though the caller already has a valid token. A token left in an unattended browser or copied from `localStorage` must not be enough to take over the account.
2. **Error codes:**
   - Wrong current password → **401 `INVALID_CURRENT_PASSWORD`**. It is a failed proof of identity, like a failed login.
   - New password equal to the current one → **422 `PASSWORD_UNCHANGED`**. The request is well-formed but breaks a rule. "Equal" means equal to bcrypt: the first 72 bytes match (see 5).
   - New password shorter than 8 characters or longer than **72 bytes** (UTF-8) → 422 `VALIDATION_ERROR` from the request schema. There are no other strength rules in the MVP.
3. **Existing tokens are not revoked.** They stay valid until they expire. Revoking them would need server-side state (a token version per user checked on every request, or a deny-list), which the stateless design deliberately avoids. The window is bounded by the token lifetime.
4. The service sets the new bcrypt hash and commits. No event is published: no other service reacts to a password change.
5. **bcrypt's 72-byte limit is explicit** (added 2026-11-15). bcrypt only uses the first 72 bytes of a password; the pinned `bcrypt==4.3.0` silently ignores the rest and `bcrypt` 5.x raises `ValueError`. So:
   - **New passwords** are capped at 72 bytes, counted in UTF-8 bytes rather than characters (`é` is 2 bytes, most emoji 4). `hash_password` refuses longer input as a second line of defence.
   - **Verifying** (login, current password) compares only the first 72 bytes, exactly what bcrypt 4.x did. Login still accepts up to 128 characters, so any hash made from a longer password before the cap keeps working, and upgrading `bcrypt` can't turn logins into 500s.

## Consequences

- If a password is changed because it leaked, an attacker who already holds a token keeps access until that token expires (up to 60 minutes by default). This is documented in `docs/api-contract.md`.
- Frontends must not treat every 401 as "session expired": on this endpoint 401 means the current password was wrong, and the user should stay signed in.
- A user can't choose a password longer than 72 bytes. Pre-hashing (e.g. SHA-256 then bcrypt) would lift the limit, but it changes every stored hash's meaning and needs a migration; not worth it at this scale.
- Frontends should enforce the same limit (8 characters to 72 bytes) to show a clear message; the API's 422 only says which field failed.
- If revocation becomes necessary, the smallest change is a `token_version` column on `user_account`, included as a claim and compared in `get_current_user`. That is a schema change (`make reset-db` without migrations).
- Covered by the `test_change_password_*`, `test_new_password_is_limited_to_72_bytes`, `test_a_72_byte_password_works` and `test_user_with_an_over_long_password_from_before_the_cap` tests in `api/tests/integration/test_auth.py`, and by `api/tests/unit/test_security.py`.
