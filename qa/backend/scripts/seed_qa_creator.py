"""Add one development-only QA Creator to an already-running Grow8 database.

Run through the existing FastAPI container (do not reset MySQL):

    Get-Content -Raw <path-to-seed_qa_creator.py> |
      docker compose exec -T api python -

Run from GROW-8/grow8-backend in PowerShell. No migrations or schema changes.
"""

import os
import sys

from sqlalchemy import select
from grow8_common.db import get_sessionmaker
from grow8_common.models import CreatorOrganization, OrganizationType, UserAccount, UserRole
from app.core.security import hash_password, verify_password


TEST_EMAIL = "qa.creator@grow8.dev"
TEST_PASSWORD = "Grow8Dev!2026"  # local DEVELOPMENT ONLY, never production
TEST_NAME = "QA Automation Creator"
TEST_ORGANIZATION = "Grow8 QA Test Organization"


def main() -> None:
    if os.getenv("APP_ENV", "").lower() not in {"development", "dev", "test", "testing"}:
        sys.exit("REFUSED: this seed is for local development/test databases only.")

    with get_sessionmaker()() as session:
        existing = session.scalar(select(UserAccount).where(UserAccount.email == TEST_EMAIL))
        if existing is not None:
            is_valid = (
                existing.role == UserRole.CREATOR
                and existing.is_active
                and verify_password(TEST_PASSWORD, existing.password_hash)
                and session.scalar(
                    select(CreatorOrganization).where(
                        CreatorOrganization.owner_user_id == existing.user_id
                    )
                ) is not None
            )
            if not is_valid:
                sys.exit(
                    "REFUSED: QA creator email already exists, but its role, password, "
                    "active status, or organization does not match expectations. "
                    "No records were changed."
                )
            print(f"Already present; no changes made: {TEST_EMAIL} (user_id={existing.user_id})")
            return

        user = UserAccount(
            email=TEST_EMAIL,
            password_hash=hash_password(TEST_PASSWORD),
            role=UserRole.CREATOR,
            full_name=TEST_NAME,
            is_active=True,
        )
        session.add(user)
        session.flush()  # get auto-generated user_id within the same transaction
        session.add(
            CreatorOrganization(
                owner_user_id=user.user_id,
                name=TEST_ORGANIZATION,
                organization_type=OrganizationType.OTHER,
                description="Dedicated local account for Grow8 QA automation.",
                city="Calgary",
            )
        )
        session.commit()
        print(f"Created QA creator: {TEST_EMAIL} (user_id={user.user_id})")
        print("Password was hashed with the Grow8 backend's bcrypt utility.")
        print("Existing accounts and existing opportunity data were not changed.")


if __name__ == "__main__":
    main()
    