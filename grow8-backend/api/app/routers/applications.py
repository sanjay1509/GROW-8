from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.dependencies.auth import CurrentContributor, CurrentCreator, CurrentUser, DbSession
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationListParams,
    ApplicationRead,
)
from app.schemas.common import Page
from app.services import application_service

router = APIRouter(tags=["applications"])

OpportunityId = Annotated[int, Path(ge=1)]
ApplicationId = Annotated[int, Path(ge=1)]


@router.post(
    "/opportunities/{opportunity_id}/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_opportunity(
    opportunity_id: OpportunityId,
    body: ApplicationCreate,
    session: DbSession,
    contributor: CurrentContributor,
    publisher: Publisher,
    request_id: RequestId,
) -> ApplicationRead:
    """Apply to an open opportunity before its deadline while places are left."""
    return application_service.apply(
        session, contributor, opportunity_id, body, publisher, request_id
    )


@router.get("/opportunities/{opportunity_id}/applications", response_model=Page[ApplicationRead])
def list_opportunity_applications(
    opportunity_id: OpportunityId,
    params: Annotated[ApplicationListParams, Query()],
    session: DbSession,
    creator: CurrentCreator,
) -> Page[ApplicationRead]:
    """Applications to an opportunity you own, newest first."""
    return application_service.list_for_opportunity(session, creator, opportunity_id, params)


@router.get("/applications/mine", response_model=Page[ApplicationRead])
def list_my_applications(
    params: Annotated[ApplicationListParams, Query()],
    session: DbSession,
    contributor: CurrentContributor,
) -> Page[ApplicationRead]:
    """Your applications in any status, newest first."""
    return application_service.list_mine(session, contributor, params)


@router.get("/applications/{application_id}", response_model=ApplicationRead)
def get_application(
    application_id: ApplicationId, session: DbSession, user: CurrentUser
) -> ApplicationRead:
    """Visible to the applicant and to the creator who owns the opportunity."""
    return application_service.get_visible(session, user, application_id)


@router.post("/applications/{application_id}/decision", response_model=ApplicationRead)
def decide_application(
    application_id: ApplicationId,
    body: ApplicationDecision,
    session: DbSession,
    creator: CurrentCreator,
    publisher: Publisher,
    request_id: RequestId,
) -> ApplicationRead:
    """Accept or reject a pending application to an opportunity you own."""
    return application_service.decide(
        session, creator, application_id, body.decision, publisher, request_id
    )


@router.post("/applications/{application_id}/withdraw", response_model=ApplicationRead)
def withdraw_application(
    application_id: ApplicationId, session: DbSession, contributor: CurrentContributor
) -> ApplicationRead:
    """Withdraw your pending or accepted application (not once work is submitted)."""
    return application_service.withdraw(session, contributor, application_id)
