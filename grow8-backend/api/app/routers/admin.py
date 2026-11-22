from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.dependencies.auth import CurrentAdmin, DbSession
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.common import Page
from app.schemas.feedback import AdminFeedbackParams, FeedbackRead, ReviewCreate
from app.services import feedback_service

router = APIRouter(prefix="/admin", tags=["admin"])

FeedbackId = Annotated[int, Path(ge=1)]


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
