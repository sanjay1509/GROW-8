from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.dependencies.auth import CurrentAdmin, DbSession
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.common import Page
from app.schemas.feedback import AdminFeedbackParams, FeedbackRead, ReviewCreate
from app.schemas.report import AdminReportParams, AdminReportRead, ReportReviewCreate
from app.services import feedback_service, report_service

router = APIRouter(prefix="/admin", tags=["admin"])

FeedbackId = Annotated[int, Path(ge=1)]
ReportId = Annotated[int, Path(ge=1)]


@router.get("/feedback", response_model=Page[FeedbackRead])
def list_feedback(
    params: Annotated[AdminFeedbackParams, Query()], session: DbSession, admin: CurrentAdmin
) -> Page[FeedbackRead]:
    """The review queue: discrepancy reports first, then oldest first. Filter by status
    (pending, approved, rejected) and discrepancy."""
    return feedback_service.list_for_admin(session, params)


@router.post("/feedback/{feedback_id}/review", response_model=FeedbackRead)
def review_feedback(
    feedback_id: FeedbackId,
    body: ReviewCreate,
    session: DbSession,
    admin: CurrentAdmin,
    publisher: Publisher,
    request_id: RequestId,
) -> FeedbackRead:
    """Approve feedback (it then counts toward the subject's rating) or reject it with a
    reason. Once per feedback."""
    return feedback_service.review(session, admin, feedback_id, body, publisher, request_id)


@router.get("/reports", response_model=Page[AdminReportRead])
def list_reports(
    params: Annotated[AdminReportParams, Query()], session: DbSession, admin: CurrentAdmin
) -> Page[AdminReportRead]:
    """Reported opportunities: the most-reported first, then the oldest report. Filter
    by status (pending, upheld, dismissed) and opportunity_id."""
    return report_service.list_for_admin(session, params)


@router.post("/reports/{report_id}/review", response_model=AdminReportRead)
def review_report(
    report_id: ReportId,
    body: ReportReviewCreate,
    session: DbSession,
    admin: CurrentAdmin,
    publisher: Publisher,
    request_id: RequestId,
) -> AdminReportRead:
    """Dismiss the report, or uphold it: the opportunity is taken down (cancelled) and
    every pending report on it is upheld. Once per report."""
    return report_service.review(session, admin, report_id, body, publisher, request_id)
