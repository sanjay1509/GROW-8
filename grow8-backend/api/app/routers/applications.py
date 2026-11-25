import json
from typing import Annotated

from fastapi import APIRouter, File, Form, Path, Query, UploadFile, status
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.dependencies.auth import CurrentContributor, CurrentCreator, CurrentUser, DbSession
from app.dependencies.request import RequestId
from app.dependencies.storage import Storage
from app.events.publisher import Publisher
from app.schemas.application import (
    ApplicationCreate,
    ApplicationDecision,
    ApplicationListParams,
    ApplicationRead,
    ReceivedApplicationParams,
)
from app.schemas.common import Page
from app.services import application_service

router = APIRouter(tags=["applications"])


def _invalid(errors: list[dict]) -> RequestValidationError:
    """Form fields are validated here, not by FastAPI, so report problems the way
    FastAPI does: 422 VALIDATION_ERROR with one {loc, message, type} per problem."""
    return RequestValidationError([{**e, "loc": ("body", *e["loc"])} for e in errors])


def _application_body(motivation: str | None, application_details: str) -> ApplicationCreate:
    """Build the apply body from the multipart form fields. An empty motivation field means
    no motivation, as in any HTML form; application_details is a JSON object of strings."""
    try:
        details = json.loads(application_details)
    except json.JSONDecodeError:
        raise _invalid(
            [{"loc": ("application_details",), "msg": "must be valid JSON", "type": "json_invalid"}]
        ) from None
    try:
        return ApplicationCreate(
            motivation=(motivation or "").strip() or None, application_details=details
        )
    except ValidationError as exc:
        raise _invalid(exc.errors(include_url=False, include_context=False)) from None


OpportunityId = Annotated[int, Path(ge=1)]
ApplicationId = Annotated[int, Path(ge=1)]


@router.post(
    "/opportunities/{opportunity_id}/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def apply_to_opportunity(
    opportunity_id: OpportunityId,
    session: DbSession,
    contributor: CurrentContributor,
    publisher: Publisher,
    request_id: RequestId,
    storage: Storage,
    motivation: Annotated[str | None, Form()] = None,
    application_details: Annotated[str, Form()] = "{}",
    resume: Annotated[
        UploadFile | None, File(description="Optional PDF resume, at most 10 MB")
    ] = None,
) -> ApplicationRead:
    """Apply to an open opportunity before its deadline while places are left."""
    body = _application_body(motivation, application_details)
    return application_service.apply(
        session,
        contributor,
        opportunity_id,
        body,
        publisher,
        request_id,
        storage,
        resume.file if resume else None,
        resume.filename if resume else None,
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


# Declared before /applications/{application_id}, which would otherwise try to read
# "received" as an id.
@router.get("/applications/received", response_model=Page[ApplicationRead])
def list_received_applications(
    params: Annotated[ReceivedApplicationParams, Query()],
    session: DbSession,
    creator: CurrentCreator,
) -> Page[ApplicationRead]:
    """Applications to all your opportunities, newest first; filter by opportunity_id
    and status."""
    return application_service.list_received(session, creator, params)


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
    application_id: ApplicationId,
    session: DbSession,
    contributor: CurrentContributor,
    publisher: Publisher,
    request_id: RequestId,
) -> ApplicationRead:
    """Withdraw your pending or accepted application (not once work is submitted).
    The creator who owns the opportunity is notified."""
    return application_service.withdraw(session, contributor, application_id, publisher, request_id)
