from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from grow8_common.models.base import (
    Base,
    UnsignedInt,
    created_at_column,
    enum_column,
    updated_at_column,
)
from grow8_common.models.enums import OrganizationType, UserRole


class UserAccount(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        UniqueConstraint("email", name="uq_user_account_email"),
        Index("ix_user_account_role", "role"),
    )

    user_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(enum_column(UserRole))
    full_name: Mapped[str] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    organization: Mapped["CreatorOrganization | None"] = relationship(back_populates="owner")


class ContributorProfile(Base):
    __tablename__ = "contributor_profile"

    user_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey("user_account.user_id", name="fk_contributor_profile_user", ondelete="CASCADE"),
        primary_key=True,
    )
    headline: Mapped[str | None] = mapped_column(String(150))
    bio: Mapped[str | None] = mapped_column(Text)
    institution: Mapped[str | None] = mapped_column(String(150))
    city: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()


class CreatorOrganization(Base):
    __tablename__ = "creator_organization"
    __table_args__ = (UniqueConstraint("owner_user_id", name="uq_creator_organization_owner"),)

    organization_id: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    owner_user_id: Mapped[int] = mapped_column(
        UnsignedInt,
        ForeignKey(
            "user_account.user_id", name="fk_creator_organization_owner", ondelete="CASCADE"
        ),
    )
    name: Mapped[str] = mapped_column(String(150))
    organization_type: Mapped[OrganizationType] = mapped_column(enum_column(OrganizationType))
    description: Mapped[str | None] = mapped_column(Text)
    website: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    owner: Mapped[UserAccount] = relationship(back_populates="organization")
