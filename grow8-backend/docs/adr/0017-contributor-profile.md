# ADR 0017: Contributors edit their own profile and skills; everyone edits their name

- **Status:** accepted; decision 5 amended by [ADR 0019](0019-earned-skills.md) (earned skills now appear, listed or not)
- **Date:** 2026-11-22
- **Builds on:** [ADR 0006](0006-application-lifecycle.md) (creators see the applicant's current public profile), [ADR 0008](0008-contributor-resume.md) (the profile row the resume hangs off).

## Context

The schema has stored contributor profiles from the start (`contributor_profile`: headline, bio, institution and city; `contributor_skill`), and creators see part of a profile on every application. But contributors had no way to read or change theirs: the frontend's contributor **Profile** page was blocked. The creator Profile and Settings pages already save the user's name with `PATCH /auth/me`, which didn't exist, so every save failed with 405. Issue #19.

Skills matter beyond display: `contributor_service` matches new opportunities to contributors by skill. It reads the current skills each time it handles `OPPORTUNITY_CREATED`, so edited skills take effect with no change to the consumers.

## Decision

1. **Three contributor-only endpoints, on the caller's own profile.** Creators and admins get 403 `ROLE_FORBIDDEN`.
   - `GET /contributors/me/profile` returns the full profile: the account's name and email, the profile fields, the skills, `has_resume` and `updated_at`.
   - `PATCH /contributors/me/profile` changes only the fields sent: `full_name`, `headline`, `bio`, `institution` or `city`. Whitespace is trimmed. For the optional fields, `null` or an empty string clears the value. `full_name` can't be cleared. Unknown fields, `email` included, are 422 `VALIDATION_ERROR`.
   - `PUT /contributors/me/skills` with `{skill_codes}` **replaces** the listed skills. Duplicates are collapsed, and an empty list removes them all. More than 25 different skills is 422 `VALIDATION_ERROR`. Unknown codes are 422 `UNKNOWN_SKILL` with `details.unknown_skills`, the same code and lookup as opportunities. A full-list `PUT` keeps the frontend simple: a multi-select sends whatever is selected. Skills that stay are left untouched, so their "listed since" date (`contributor_skill.created_at`) is kept.
2. **Any role can change their name: `PATCH /auth/me` with `{full_name}`.** It returns the same body as `GET /auth/me`. Email is the sign-in, so changing it needs its own design (uniqueness, re-authentication) and is refused here as an unknown field. Tokens don't carry the name, so they stay valid.
3. **A missing profile row is created on the first save.** Sign-up always creates one, but seeded or old accounts might lack it, and that user must never be stuck.
   - `GET` returns the name and email with empty profile fields, `skills: []` and `updated_at: null`, and writes nothing.
   - The first `PATCH` or `PUT` creates the row.
   - Applying and uploading a resume still refuse with 409 `CONTRIBUTOR_PROFILE_REQUIRED`, now with the message "Save your profile first", which the user can act on.
4. **Saving locks the profile row.** Locking a row that doesn't exist locks nothing, so the row is first ensured with `INSERT … ON DUPLICATE KEY UPDATE user_id = user_id` (a no-op when it exists; never `INSERT IGNORE`, ADR 0010), then locked with `SELECT … FOR UPDATE`. Two saves at once, including two first saves, run one after the other instead of interleaving or failing on a duplicate key. Replacing skills is one transaction.
5. **Skills come in two kinds: listed and verified.** Each skill is returned as `{code, name, listed, verified, verified_at}`, sorted by name. `verified` and `verified_at` are read from `v_contributor_skill` and never recomputed in Python, so there is one definition.
   - Today the view only covers listed skills, so every returned skill has `listed: true`.
   - Removing a listed skill hides its verification, but nothing is lost: the approved work stays, and adding the skill back shows it as verified again, with its original date.
   - Skills earned through approved work but never listed will appear as `listed: false, verified: true` once #29 changes the view. The response shape doesn't change, and `PUT /skills` will still edit only listed skills.
6. **`updated_at` is when the profile last changed,** skills included. MySQL sets it on a profile field change. A skill change sets it too, using the database's clock, because skills live in their own table. Saving identical values changes nothing.
7. **Visibility is unchanged.** Creators see the public part through an application only (ADR 0006), and always the current version, so edits show there straight away. Email is never shown to creators. There's no public profile page.
8. **No events.** No other service reacts to a profile edit.

No schema change.

## Consequences

- The contributor Profile page can be built, and the creator pages' name save works.
- Contributors who change their skills get better-matched opportunity notifications without any consumer change.
- Moving the skill lookup into `reference_service.resolve_skills` means opportunities and profiles report unknown skills the same way.
- Still to do: a creator's organization (name, type, description, website, city) can't be edited yet. That's the same pattern for creators and has its own issue. Changing email, profile photos and a public profile page are out of scope.
