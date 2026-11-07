from fastapi import APIRouter

from app.dependencies.auth import DbSession
from app.schemas.reference import CategoryRead, SkillRead
from app.services import reference_service

router = APIRouter(tags=["reference"])


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(session: DbSession) -> list[CategoryRead]:
    return [CategoryRead.model_validate(c) for c in reference_service.list_categories(session)]


@router.get("/skills", response_model=list[SkillRead])
def list_skills(session: DbSession) -> list[SkillRead]:
    return [SkillRead.model_validate(s) for s in reference_service.list_skills(session)]
