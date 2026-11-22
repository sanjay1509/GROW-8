from typing import Annotated

from fastapi import APIRouter, Path, status

from app.dependencies.auth import CurrentUser, DbSession
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.feedback import ApplicationFeedback, FeedbackCreate, FeedbackRead, UserRating
from app.services import feedback_service

router = APIRouter(tags=["feedback"])

FEEDBACK_PATH = "/applications/{application_id}/feedback"
ApplicationId = Annotated[int, Path(ge=1)]
UserId = Annotated[int, Path(ge=1)]


@router.post(FEEDBACK_PATH, response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
def give_feedback(
    application_id: ApplicationId,
    body: FeedbackCreate,
    session: DbSession,
    user: CurrentUser,
    publisher: Publisher,
    request_id: RequestId,
) -> FeedbackRead:
    """Rate the other participant once the work is verified. Once per application; an
    admin reviews it before it counts."""
    return feedback_service.submit(session, user, application_id, body, publisher, request_id)


@router.get(FEEDBACK_PATH, response_model=ApplicationFeedback)
def get_feedback(
    application_id: ApplicationId, session: DbSession, user: CurrentUser
) -> ApplicationFeedback:
    """Your feedback on the application (any status), and theirs about you once approved."""
    return feedback_service.for_application(session, user, application_id)


@router.get("/users/{user_id}/rating", response_model=UserRating)
def get_rating(user_id: UserId, session: DbSession) -> UserRating:
    """Public: the average and count of approved feedback about this user."""
    return feedback_service.rating(session, user_id)
