from typing import Annotated

from fastapi import APIRouter, File, Path, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.dependencies.auth import CurrentContributor, CurrentUser, DbSession
from app.dependencies.storage import Storage
from app.routers._files import stream_download
from app.schemas.contributor_profile import ContributorProfileRead, ProfileUpdate, SkillsReplace
from app.schemas.experience import ExperienceRead
from app.schemas.resume import ResumeRead
from app.services import contributor_profile_service, experience_service, resume_service
from app.services.resume_service import ResumeFile

router = APIRouter(tags=["resumes"])

PROFILE_PATH = "/contributors/me/profile"
RESUME_PATH = "/contributors/me/resume"
ApplicationId = Annotated[int, Path(ge=1)]


def _stream(resume: ResumeFile) -> StreamingResponse:
    return stream_download(resume, fallback_name="resume.pdf")


@router.get(PROFILE_PATH, response_model=ContributorProfileRead, tags=["profile"])
def get_my_profile(session: DbSession, contributor: CurrentContributor) -> ContributorProfileRead:
    """Your profile, with your skills (listed, and whether approved work verified them)."""
    return contributor_profile_service.get_mine(session, contributor)


@router.patch(PROFILE_PATH, response_model=ContributorProfileRead, tags=["profile"])
def update_my_profile(
    body: ProfileUpdate, session: DbSession, contributor: CurrentContributor
) -> ContributorProfileRead:
    """Change your name, headline, bio, institution or city; only the fields sent change."""
    return contributor_profile_service.update_mine(session, contributor, body)


@router.get("/contributors/me/experience", response_model=ExperienceRead, tags=["profile"])
def get_my_experience(session: DbSession, contributor: CurrentContributor) -> ExperienceRead:
    """Your verified record: approved hours and opportunities (from
    v_contributor_verified_hours), the work behind them, and your verified skills."""
    return experience_service.get_mine(session, contributor)


@router.put("/contributors/me/skills", response_model=ContributorProfileRead, tags=["profile"])
def replace_my_skills(
    body: SkillsReplace, session: DbSession, contributor: CurrentContributor
) -> ContributorProfileRead:
    """Replace the skills you list with exactly these codes (from GET /skills)."""
    return contributor_profile_service.replace_skills(session, contributor, body)


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
    """The resume submitted with the application, for its creator or applicant."""
    return _stream(resume_service.open_for_application(session, storage, user, application_id))
