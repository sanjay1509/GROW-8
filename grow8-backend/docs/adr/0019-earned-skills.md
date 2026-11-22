# ADR 0019: Skills earned through approved work count, listed or not

- **Status:** accepted
- **Date:** 2026-11-22
- **Amends:** ENSF 608 decision 7 (`docs/db/functional-dependencies.md`, section 5) and [ADR 0017](0017-contributor-profile.md) decision 5.

## Context

Decision 7 made "verified skill" derived: `v_contributor_skill` marked a skill verified once the contributor had approved work on an opportunity that required it. But the view started `FROM contributor_skill`, so only skills the contributor had **listed** could ever be verified.
- **Unlisted skills earned nothing.** Approved work on an opportunity requiring a skill the contributor hadn't listed counted for nothing.
- **Removing a listing hid the skill.** If the contributor removed a listed skill, its verification disappeared from their profile.

The proposal says verified work updates a contributor's verified hours **and skills**, and SDG target 8.6 measures the skills each contributor acquires. Since #23 made verification real, the gap shows in actual data. Issue #29.

## Decision

1. **A skill is verified once the contributor has approved work on an opportunity that required it, listed or not.** A skill is **listed** when it's in `contributor_skill`, which the contributor edits on their profile.
2. **`v_contributor_skill` returns one row per contributor and skill:** every listed skill, plus every earned skill.
   - `contributor_id`, `skill_id`.
   - `is_listed`: whether the skill is in `contributor_skill`.
   - `created_at`: when it was listed, or `NULL` if never listed.
   - `is_verified`: whether approved work proved it.
   - `verified_at`: the first approval that proved it.

   It is a `UNION ALL` of listed skills and earned skills, grouped by contributor and skill. It's still derived: no new table or column.
3. **Editing the listed skills never removes an earned skill.** `PUT /contributors/me/skills` only changes `contributor_skill`. Removing a listed skill that work also proved leaves it as `listed: false, verified: true`, and listing an earned skill gives one entry with `listed: true, verified: true`.
4. **The profile API keeps its shape** (ADR 0017): `{code, name, listed, verified, verified_at}`, sorted by name. `listed` now comes from the view, and earned skills appear with `listed: false`.
5. **Opportunity matching stays on listed skills.** `find_matching_contributors` (`OPPORTUNITY_CREATED`) reads `contributor_skill` only. Listing is how a contributor says what they want to be notified about, and an earned skill can't be removed, so matching on it would leave them no way to opt out. The profile can suggest listing an earned skill.
6. **Rewards (#24)** should read `v_contributor_skill WHERE is_verified` for "verified skills", so earned skills count.

## Migration

The view is the only change. It can be replaced on an existing database without `make reset-db`, so no data is lost:

```sql
CREATE OR REPLACE VIEW v_contributor_skill AS
SELECT k.contributor_id,
       k.skill_id,
       MAX(k.is_listed) AS is_listed,
       MAX(k.listed_at) AS created_at,
       (MIN(k.verified_at) IS NOT NULL) AS is_verified,
       MIN(k.verified_at) AS verified_at
FROM (
    SELECT cs.contributor_id, cs.skill_id, 1 AS is_listed, cs.created_at AS listed_at,
           CAST(NULL AS DATETIME) AS verified_at
    FROM contributor_skill cs
    UNION ALL
    SELECT a.contributor_id, os.skill_id, 0, NULL, wv.verified_at
    FROM application a
    JOIN work_submission ws ON ws.application_id = a.application_id
    JOIN work_verification wv
         ON wv.submission_id = ws.submission_id AND wv.decision = 'approved'
    JOIN opportunity_skill os ON os.opportunity_id = a.opportunity_id
) k
GROUP BY k.contributor_id, k.skill_id;
```

## Consequences

- Contributors' profiles show everything their work has proved, and the SDG 8.6 measure can count acquired skills from one view.
- Verification can't be lost by editing the profile.
- `created_at` in the view is now nullable. Nothing in the API read it.
- An earned skill can't be hidden from the contributor's own profile. That's acceptable, because it records verified work, like verified hours.
