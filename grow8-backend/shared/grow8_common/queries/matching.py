"""Which contributors should hear about an opportunity.

Used by contributor_service when it consumes OPPORTUNITY_CREATED. It lives in the shared
package so the API's integration tests can run it against the seeded test database.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from grow8_common.models import (
    ContributorProfile,
    ContributorSkill,
    Opportunity,
    OpportunityStatus,
    Skill,
    UserAccount,
    UserRole,
)


@dataclass(frozen=True)
class ContributorMatch:
    user_id: int
    full_name: str
    matched_skill_codes: list[str] = field(default_factory=list)


def _active_contributors():
    return (
        select(UserAccount.user_id, UserAccount.full_name)
        .join(ContributorProfile, ContributorProfile.user_id == UserAccount.user_id)
        .where(UserAccount.is_active.is_(True), UserAccount.role == UserRole.CONTRIBUTOR)
    )


def find_matching_contributors(
    session: Session, skill_codes: Sequence[str]
) -> list[ContributorMatch]:
    """Active contributors with at least one of `skill_codes`, best match first
    (most matched skills, then lowest user_id). An opportunity that lists no skills
    is relevant to every active contributor."""
    if not skill_codes:
        rows = session.execute(_active_contributors().order_by(UserAccount.user_id)).all()
        return [ContributorMatch(user_id=r.user_id, full_name=r.full_name) for r in rows]

    stmt = (
        _active_contributors()
        .join(ContributorSkill, ContributorSkill.contributor_id == ContributorProfile.user_id)
        .join(Skill, Skill.skill_id == ContributorSkill.skill_id)
        .add_columns(Skill.code)
        .where(Skill.code.in_(list(skill_codes)))
        .order_by(UserAccount.user_id, Skill.code)
    )
    matches: dict[int, ContributorMatch] = {}
    for row in session.execute(stmt):
        match = matches.setdefault(
            row.user_id, ContributorMatch(user_id=row.user_id, full_name=row.full_name)
        )
        match.matched_skill_codes.append(row.code)
    return sorted(matches.values(), key=lambda m: (-len(m.matched_skill_codes), m.user_id))


def is_opportunity_open(session: Session, opportunity_id: int) -> bool:
    """True while the opportunity is still published. Events can arrive late, so the
    consumer re-checks instead of trusting the snapshot in the event."""
    status = session.scalar(
        select(Opportunity.status).where(Opportunity.opportunity_id == opportunity_id)
    )
    return status == OpportunityStatus.OPEN
