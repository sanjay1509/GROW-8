import unicodedata
from collections.abc import Iterator
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Path, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.dependencies.auth import CurrentContributor, CurrentUser, DbSession
from app.dependencies.storage import Storage
from app.schemas.resume import ResumeRead
from app.services import resume_service
from app.services.resume_service import ResumeFile

router = APIRouter(tags=["resumes"])

RESUME_PATH = "/contributors/me/resume"
ApplicationId = Annotated[int, Path(ge=1)]
_CHUNK = 64 * 1024


def _content_disposition(file_name: str) -> str:
    """attachment with an ASCII fallback name plus the exact UTF-8 name (RFC 6266/5987)."""
    decomposed = unicodedata.normalize("NFKD", file_name)  # é -> e + accent, then drop the accent
    ascii_name = decomposed.encode("ascii", "ignore").decode().replace('"', "") or "resume.pdf"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(file_name)}"


def _stream(resume: ResumeFile) -> StreamingResponse:
    def chunks() -> Iterator[bytes]:
        with resume.stream as stream:
            while chunk := stream.read(_CHUNK):
                yield chunk

    return StreamingResponse(
        chunks(),
        media_type=resume.content_type,
        headers={
            "Content-Disposition": _content_disposition(resume.file_name),
            "Content-Length": str(resume.size_bytes),
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


@router.put(RESUME_PATH, response_model=ResumeRead)
def upload_resume(
    file: Annotated[UploadFile, File(description="PDF, at most 10 MB")],
    session: DbSession,
    storage: Storage,
    contributor: CurrentContributor,
) -> ResumeRead:
    """Upload your resume, replacing the previous one if any."""
    resume = resume_service.upload(session, storage, contributor, file.file, file.filename)
    return ResumeRead.model_validate(resume)


@router.get(RESUME_PATH, response_model=ResumeRead)
def get_my_resume(session: DbSession, contributor: CurrentContributor) -> ResumeRead:
    """Your resume's metadata (404 if you have none)."""
    return ResumeRead.model_validate(resume_service.get_mine(session, contributor))


@router.get(
    RESUME_PATH + "/file",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_my_resume(
    session: DbSession, storage: Storage, contributor: CurrentContributor
) -> StreamingResponse:
    """Download your resume."""
    return _stream(resume_service.open_mine(session, storage, contributor))


@router.delete(RESUME_PATH, status_code=status.HTTP_204_NO_CONTENT)
def delete_my_resume(
    session: DbSession, storage: Storage, contributor: CurrentContributor
) -> Response:
    """Delete your resume."""
    resume_service.delete_mine(session, storage, contributor)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/applications/{application_id}/resume",
    response_class=StreamingResponse,
    responses={200: {"content": {"application/pdf": {}}}},
)
def download_applicant_resume(
    application_id: ApplicationId, session: DbSession, storage: Storage, user: CurrentUser
) -> StreamingResponse:
    """The applicant's current resume, for the creator who owns the opportunity."""
    return _stream(resume_service.open_for_application(session, storage, user, application_id))
