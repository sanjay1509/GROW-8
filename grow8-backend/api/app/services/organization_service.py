"""The signed-in creator's own organization (ADR 0018).

Saving locks the creator's account row first, so two saves at once run one after the
other, including two that both create a missing organization. No events: nothing else
needs to react, and opportunities read the organization when they're loaded, so an edit
shows on every posting straight away."""

from grow8_common.models import CreatorOrganization, UserAccount
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.repositories import user_repository
from app.schemas.organization import OrganizationRead, OrganizationUpdate

_FIELDS = ("name", "organization_type", "description", "website", "city")


def get_mine(session: Session, creator: UserAccount) -> OrganizationRead:
    organization = user_repository.get_organization_of(session, creator.user_id)
    if organization is None:
        raise NotFoundError("You have no organization yet", code="ORGANIZATION_NOT_FOUND")
    return OrganizationRead.model_validate(organization)


def update_mine(
    session: Session, creator: UserAccount, data: OrganizationUpdate
) -> OrganizationRead:
    """Change only the fields sent. Without an organization yet, the first save creates
    it, as long as it sends both name and organization_type."""
    organization = user_repository.lock_organization_of(session, creator.user_id)
    if organization is None:
        if not data.can_create():
            raise ConflictError(
                "You have no organization yet: send name and organization_type to create it",
                code="ORGANIZATION_REQUIRED",
            )
        organization = CreatorOrganization(owner_user_id=creator.user_id)
        user_repository.add_organization(session, organization)

    for field in _FIELDS:
        if field in data.model_fields_set:
            setattr(organization, field, getattr(data, field))
    session.commit()
    # created_at/updated_at are set by MySQL, and the session keeps objects after commit.
    session.refresh(organization)
    return OrganizationRead.model_validate(organization)
