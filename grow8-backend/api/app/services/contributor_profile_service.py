"""The signed-in contributor's own profile and listed skills (ADR 0017).

Saving always runs with the profile row locked (it is created first if missing), so two
tabs saving at once run one after the other. No events: nothing else needs to react, and
opportunity matching reads the current skills when each event is handled."""

from grow8_common.models import ContributorProfile, UserAccount
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.repositories import resume_repository, user_repository
from app.schemas.contributor_profile import (
    ContributorProfileRead,
    ProfileSkill,
    ProfileUpdate,
    SkillsReplace,
)
from app.services import reference_service

_PROFILE_FIELDS = ("headline", "bio", "institution", "city")


def get_mine(session: Session, contributor: UserAccount) -> ContributorProfileRead:
    """Your profile. Without a profile row yet, the fields are empty and updated_at is None."""
    profile = user_repository.get_contributor_profile(session, contributor.user_id)
    return _read(session, contributor, profile)


def update_mine(
    session: Session, contributor: UserAccount, data: ProfileUpdate
) -> ContributorProfileRead:
    """Change only the fields sent. full_name is stored on the account."""
    profile = user_repository.lock_contributor_profile(session, contributor.user_id)
    sent = data.model_fields_set
    if data.full_name is not None:  # sent; the schema refuses null
        contributor.full_name = data.full_name
    for field in _PROFILE_FIELDS:
        if field in sent:
            setattr(profile, field, getattr(data, field))
    return _commit_and_read(session, contributor, profile)


def replace_skills(
    session: Session, contributor: UserAccount, data: SkillsReplace
) -> ContributorProfileRead:
    """Make your listed skills exactly these. Skills you keep are left alone (their
    listed-since date stays); unknown codes are a 422 UNKNOWN_SKILL listing them. Skills
    earned through approved work aren't listed skills, so this never removes them."""
    skills = reference_service.resolve_skills(session, data.skill_codes)
    wanted = {skill.skill_id for skill in skills}
    profile = user_repository.lock_contributor_profile(session, contributor.user_id)
    current = user_repository.listed_skill_ids(session, contributor.user_id)
    if current != wanted:
        user_repository.remove_skills(session, contributor.user_id, sorted(current - wanted))
        user_repository.add_skills(session, contributor.user_id, sorted(wanted - current))
        # Skills live in their own table, so mark the profile changed too. The database's
        # clock, as for its own ON UPDATE.
        profile.updated_at = func.current_timestamp()
    return _commit_and_read(session, contributor, profile)


def _commit_and_read(
    session: Session, contributor: UserAccount, profile: ContributorProfile
) -> ContributorProfileRead:
    session.commit()
    # updated_at is set by MySQL (ON UPDATE CURRENT_TIMESTAMP), and the session keeps
    # objects after commit, so read the row back.
    session.refresh(profile)
    return _read(session, contributor, profile)


def _read(
    session: Session, contributor: UserAccount, profile: ContributorProfile | None
) -> ContributorProfileRead:
    # Listed and earned skills alike (ADR 0019). Without a profile row there are none:
    # applications, and so approved work, need one.
    skills = [
        ProfileSkill(
            code=s.code,
            name=s.name,
            listed=s.is_listed,
            verified=s.is_verified,
            verified_at=s.verified_at,
        )
        for s in user_repository.skills_of(session, contributor.user_id)
    ]
    return ContributorProfileRead(
        user_id=contributor.user_id,
        full_name=contributor.full_name,
        email=contributor.email,
        headline=profile.headline if profile else None,
        bio=profile.bio if profile else None,
        institution=profile.institution if profile else None,
        city=profile.city if profile else None,
        skills=skills,
        has_resume=resume_repository.get(session, contributor.user_id) is not None,
        updated_at=profile.updated_at if profile else None,
    )
