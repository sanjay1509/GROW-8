"""Who runs an organization.

Used by creator_service when it consumes OPPORTUNITY_CREATED. It lives in the shared
package so the API's integration tests can run it against the seeded test database.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from grow8_common.models import CreatorOrganization, UserAccount


def find_active_owner(session: Session, organization_id: int) -> int | None:
    """user_id of the organization's owner, or None if the organization is gone or its
    owner's account is inactive."""
    return session.scalar(
        select(UserAccount.user_id)
        .join(CreatorOrganization, CreatorOrganization.owner_user_id == UserAccount.user_id)
        .where(
            CreatorOrganization.organization_id == organization_id,
            UserAccount.is_active.is_(True),
        )
    )
