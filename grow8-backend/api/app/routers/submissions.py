from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import StreamingResponse
from pydantic import ValidationError

from app.dependencies.auth import CurrentContributor, CurrentUser, DbSession
from app.dependencies.request import RequestId
from app.dependencies.storage import Storage
from app.events.publisher import Publisher
from app.routers._files import stream_download
from app.schemas.submission import SubmissionCreate, SubmissionRead
from app.services import submission_service
from app.services.submission_service import UploadedFile

router = APIRouter(tags=["submissions"])

SUBMISSION_PATH = "/applications/{application_id}/submission"
ApplicationId = Annotated[int, Path(ge=1)]
SubmissionId = Annotated[int, Path(ge=1)]
AttachmentId = Annotated[int, Path(ge=1)]


def _submission_form(
    description: Annotated[str, Form(description="What you did (1–5000 characters)")],
    hours_claimed: Annotated[str, Form(description="Hours you worked, e.g. 6.5")],
) -> SubmissionCreate:
    """The form fields, validated by SubmissionCreate. Its errors become the usual 422
    VALIDATION_ERROR, located in the body like any other request field."""
    try:
        return SubmissionCreate(description=description, hours_claimed=hours_claimed)
    except ValidationError as exc:
        raise RequestValidationError(
            [{**e, "loc": ("body", *e["loc"])} for e in exc.errors(include_url=False)]
        ) from None


@router.post(SUBMISSION_PATH, response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def submit_work(
    application_id: ApplicationId,
    data: Annotated[SubmissionCreate, Depends(_submission_form)],
    session: DbSession,
    storage: Storage,
    contributor: CurrentContributor,
    publisher: Publisher,
    request_id: RequestId,
    files: Annotated[
        list[UploadFile],
        File(description="Up to 5 files, 5 MB each: PDF, PNG, JPEG, DOCX, XLSX, CSV or TXT"),
    ] = [],  # noqa: B006 - FastAPI copies the default per request
) -> SubmissionRead:
    """Submit your work for your accepted application. The creator is notified."""
    uploads = [UploadedFile(f.file, f.filename) for f in files]
    return submission_service.submit(
        session, storage, contributor, application_id, data, uploads, publisher, request_id
    )


@router.get(SUBMISSION_PATH, response_model=SubmissionRead)
def get_submission(
    application_id: ApplicationId, session: DbSession, user: CurrentUser
) -> SubmissionRead:
    """The work submitted for an application, for the applicant or the owning creator."""
    return submission_service.get_for_application(session, user, application_id)


@router.get(
    "/submissions/{submission_id}/attachments/{attachment_id}",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def download_attachment(
    submission_id: SubmissionId,
    attachment_id: AttachmentId,
    session: DbSession,
    storage: Storage,
    user: CurrentUser,
) -> StreamingResponse:
    """Download an attachment, for the applicant or the owning creator."""
    attachment = submission_service.open_attachment(
        session, storage, user, submission_id, attachment_id
    )
    return stream_download(attachment, fallback_name="attachment")
