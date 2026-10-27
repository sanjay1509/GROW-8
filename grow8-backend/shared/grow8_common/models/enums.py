from enum import StrEnum


class UserRole(StrEnum):
    CREATOR = "creator"
    CONTRIBUTOR = "contributor"
    ADMIN = "admin"


class OrganizationType(StrEnum):
    SMALL_BUSINESS = "small_business"
    NONPROFIT = "nonprofit"
    EVENT_ORGANIZER = "event_organizer"
    OTHER = "other"


class WorkMode(StrEnum):
    ON_SITE = "on_site"
    REMOTE = "remote"
    HYBRID = "hybrid"


class CompensationType(StrEnum):
    PAID = "paid"
    STIPEND = "stipend"
    UNPAID = "unpaid"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class SkillSource(StrEnum):
    SELF_REPORTED = "self_reported"
    VERIFIED = "verified"


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ReviewDecision(StrEnum):
    """Used by both work_verification.decision and admin_review.decision."""

    APPROVED = "approved"
    REJECTED = "rejected"


class PointSource(StrEnum):
    WORK_VERIFIED = "work_verified"
    BADGE_AWARDED = "badge_awarded"


class NotificationType(StrEnum):
    """One value per kind of notification (one event can produce several kinds)."""

    OPPORTUNITY_CREATED = "opportunity_created"  # to matching contributors
    OPPORTUNITY_PUBLISHED = "opportunity_published"  # to the creator who published it
