"""Who the admins are.

Used by admin_service when it consumes FEEDBACK_SUBMITTED. It lives in the shared
package so the API's integration tests can run it against the seeded test database.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from grow8_common.models import UserAccount, UserRole


def find_active_admins(session: Session) -> list[int]:
    """user_ids of every admin whose account is active, in id order."""
    return list(
        session.scalars(
            select(UserAccount.user_id)
            .where(UserAccount.role == UserRole.ADMIN, UserAccount.is_active.is_(True))
            .order_by(UserAccount.user_id)
        )
    )
