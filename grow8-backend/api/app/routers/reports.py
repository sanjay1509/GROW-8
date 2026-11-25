from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.dependencies.auth import CurrentContributor, CurrentCreator, DbSession
from app.dependencies.request import RequestId
from app.events.publisher import Publisher
from app.schemas.common import Page
from app.schemas.report import MyReportParams, ReportCreate, ReportRead, TakedownRead
from app.services import report_service

router = APIRouter(tags=["reports"])

OpportunityId = Annotated[int, Path(ge=1)]


@router.post(
    "/opportunities/{opportunity_id}/reports",
    response_model=ReportRead,
    status_code=status.HTTP_201_CREATED,
)
def report_opportunity(
    opportunity_id: OpportunityId,
    body: ReportCreate,
    session: DbSession,
    contributor: CurrentContributor,
    publisher: Publisher,
    request_id: RequestId,
) -> ReportRead:
    """Report a published opportunity as misleading, unsafe, discriminatory or a scam.
    Once per opportunity. The creator never learns who reported."""
    return report_service.submit(session, contributor, opportunity_id, body, publisher, request_id)


@router.get("/reports/mine", response_model=Page[ReportRead])
def list_my_reports(
    params: Annotated[MyReportParams, Query()], session: DbSession, contributor: CurrentContributor
) -> Page[ReportRead]:
    """Your reports and what the admins decided, newest first."""
    return report_service.list_mine(session, contributor, params)


@router.get("/opportunities/{opportunity_id}/takedown", response_model=TakedownRead)
def get_takedown(
    opportunity_id: OpportunityId, session: DbSession, creator: CurrentCreator
) -> TakedownRead:
    """For the owning creator: when and why an admin took the opportunity down. Never says
    who reported or what they wrote. Not taken down: 404 TAKEDOWN_NOT_FOUND."""
    return report_service.takedown_for_creator(session, creator, opportunity_id)
