"""A contributor's verified experience: totals from v_contributor_verified_hours and the
approved work behind them. The totals come from the view, so there is one definition of
"verified hours" for the profile, the leaderboard and badges (decision 7)."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ExperienceTotals:
    verified_hours: Decimal
    completed_opportunities: int


@dataclass(frozen=True)
class CompletedWorkRow:
    application_id: int
    submission_id: int
    opportunity_id: int
    opportunity_title: str
    organization_id: int
    organization_name: str
    description: str
    verified_hours: Decimal
    comment: str | None
    verified_at: datetime


def totals(session: Session, contributor_id: int) -> ExperienceTotals:
    """Verified hours and completed opportunities. A contributor without a profile row
    has no row in the view, which means nothing verified yet."""
    row = session.execute(
        text(
            "SELECT verified_hours, completed_opportunities "
            "FROM v_contributor_verified_hours WHERE contributor_id = :contributor_id"
        ),
        {"contributor_id": contributor_id},
    ).first()
    if row is None:
        return ExperienceTotals(Decimal("0.00"), 0)
    return ExperienceTotals(Decimal(row.verified_hours), int(row.completed_opportunities))


def completed_work(session: Session, contributor_id: int) -> list[CompletedWorkRow]:
    """Every piece of approved work, most recently verified first. Same joins as the view,
    so the rows add up to its totals."""
    rows = session.execute(
        text(
            "SELECT a.application_id, ws.submission_id, o.opportunity_id, o.title, "
            "       org.organization_id, org.name AS organization_name, ws.description, "
            "       wv.verified_hours, wv.comment, wv.verified_at "
            "FROM application a "
            "JOIN work_submission ws ON ws.application_id = a.application_id "
            "JOIN work_verification wv "
            "     ON wv.submission_id = ws.submission_id AND wv.decision = 'approved' "
            "JOIN opportunity o ON o.opportunity_id = a.opportunity_id "
            "JOIN creator_organization org ON org.organization_id = o.organization_id "
            "WHERE a.contributor_id = :contributor_id "
            "ORDER BY wv.verified_at DESC, wv.verification_id DESC"
        ),
        {"contributor_id": contributor_id},
    ).all()
    return [
        CompletedWorkRow(
            r.application_id,
            r.submission_id,
            r.opportunity_id,
            r.title,
            r.organization_id,
            r.organization_name,
            r.description,
            Decimal(r.verified_hours),
            r.comment,
            r.verified_at,
        )
        for r in rows
    ]
