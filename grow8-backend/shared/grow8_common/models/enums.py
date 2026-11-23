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


class ApplicationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ReviewDecision(StrEnum):
    """Used by both work_verification.decision and admin_review.decision."""

    APPROVED = "approved"
    REJECTED = "rejected"


class ReportReason(StrEnum):
    """Why a contributor reports an opportunity (opportunity_report.reason, ADR 0016)."""

    MISLEADING_TERMS = "misleading_terms"
    UNSAFE_CONDITIONS = "unsafe_conditions"
    DISCRIMINATORY = "discriminatory"
    SCAM_OR_SPAM = "scam_or_spam"
    OTHER = "other"


class ReportDecision(StrEnum):
    """report_review.decision: upheld means the opportunity was taken down."""

    UPHELD = "upheld"
    DISMISSED = "dismissed"


class PointSource(StrEnum):
    WORK_VERIFIED = "work_verified"
    BADGE_AWARDED = "badge_awarded"


class NotificationType(StrEnum):
    """One value per kind of notification (one event can produce several kinds)."""

    OPPORTUNITY_CREATED = "opportunity_created"  # to matching contributors
    OPPORTUNITY_PUBLISHED = "opportunity_published"  # to the creator who published it
    APPLICATION_SUBMITTED = "application_submitted"  # to the creator who owns the opportunity
    APPLICATION_DECIDED = "application_decided"  # to the contributor who applied
    APPLICATION_WITHDRAWN = "application_withdrawn"  # to the creator who owns the opportunity
    OPPORTUNITY_CANCELLED = "opportunity_cancelled"  # to its pending and accepted applicants
    WORK_SUBMITTED = "work_submitted"  # to the creator who owns the opportunity
    WORK_VERIFIED = "work_verified"  # to the contributor whose work was approved
    WORK_REJECTED = "work_rejected"  # to the contributor whose work was rejected
    FEEDBACK_SUBMITTED = "feedback_submitted"  # to every active admin
    FEEDBACK_APPROVED = "feedback_approved"  # to the author and the subject
    FEEDBACK_REJECTED = "feedback_rejected"  # to the author only
    OPPORTUNITY_REPORTED = "opportunity_reported"  # to every active admin
    OPPORTUNITY_TAKEN_DOWN = "opportunity_taken_down"  # to the owner, applicants and reporters
    REPORT_DISMISSED = "report_dismissed"  # to the contributor who reported
