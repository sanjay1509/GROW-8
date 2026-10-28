
from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from app.dependencies.auth import CurrentCreator, DbSession, OptionalUser
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.common import Page
from app.schemas.opportunity import (
    MyOpportunitySearchParams,
    OpportunityCreate,
    OpportunityRead,
    OpportunitySearchParams,
    OpportunityUpdate,
)
from app.services import opportunity_service


router = APIRouter(
    prefix="/opportunities",
    tags=["opportunities"],
)

OpportunityId = Annotated[int, Path(ge=1)]


@router.get("", response_model=Page[OpportunityRead])
def list_opportunities(
    params: Annotated[OpportunitySearchParams, Query()],
    session: DbSession,
) -> Page[OpportunityRead]:
    """Browse open opportunities that are still accepting applications."""
    return opportunity_service.list_public(session, params)


@router.get("/mine", response_model=Page[OpportunityRead])
def list_my_opportunities(
    params: Annotated[MyOpportunitySearchParams, Query()],
    session: DbSession,
    creator: CurrentCreator,
) -> Page[OpportunityRead]:
    """The calling creator's opportunities in any status, drafts included."""
    return opportunity_service.list_mine(
        session,
        creator,
        params,
    )


@router.get("/{opportunity_id}", response_model=OpportunityRead)
def get_opportunity(
    opportunity_id: OpportunityId,
    session: DbSession,
    user: OptionalUser,
) -> OpportunityRead:
    opportunity = opportunity_service.get_visible(
        session,
        opportunity_id,
        user,
    )
    return OpportunityRead.model_validate(opportunity)


@router.post(
    "",
    response_model=OpportunityRead,
    status_code=status.HTTP_201_CREATED,
)
def create_opportunity(
    body: OpportunityCreate,
    session: DbSession,
    creator: CurrentCreator,
) -> OpportunityRead:
    """Create a draft. Publish it when ready."""
    opportunity = opportunity_service.create_draft(
        session,
        creator,
        body,
    )
    return OpportunityRead.model_validate(opportunity)


@router.patch(
    "/{opportunity_id}",
    response_model=OpportunityRead,
)
def update_opportunity(
    opportunity_id: OpportunityId,
    body: OpportunityUpdate,
    session: DbSession,
    creator: CurrentCreator,
) -> OpportunityRead:
    """Edit a draft you own. Only the fields sent are changed."""
    opportunity = opportunity_service.update_draft(
        session,
        creator,
        opportunity_id,
        body,
    )
    return OpportunityRead.model_validate(opportunity)


@router.post(
    "/{opportunity_id}/publish",
    response_model=OpportunityRead,
)
def publish_opportunity(
    opportunity_id: OpportunityId,
    session: DbSession,
    creator: CurrentCreator,
    publisher: Publisher,
    request_id: RequestId,
) -> OpportunityRead:
    """Validate mandatory information and publish the opportunity."""
    opportunity = opportunity_service.publish(
        session,
        creator,
        opportunity_id,
        publisher,
        request_id,
    )
    return OpportunityRead.model_validate(opportunity)


@router.delete(
    "/{opportunity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_opportunity(
    opportunity_id: OpportunityId,
    session: DbSession,
    creator: CurrentCreator,
) -> Response:
    """Delete an opportunity owned by the authenticated creator."""
    opportunity_service.delete_opportunity(
        session,
        creator,
        opportunity_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
