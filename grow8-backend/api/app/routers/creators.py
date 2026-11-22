from fastapi import APIRouter

from app.dependencies.auth import CurrentCreator, DbSession
from app.schemas.organization import OrganizationRead, OrganizationUpdate
from app.services import organization_service

router = APIRouter(prefix="/creators/me", tags=["organization"])


@router.get("/organization", response_model=OrganizationRead)
def get_my_organization(session: DbSession, creator: CurrentCreator) -> OrganizationRead:
    """Your organization (404 if you have none yet)."""
    return organization_service.get_mine(session, creator)


@router.patch("/organization", response_model=OrganizationRead)
def update_my_organization(
    body: OrganizationUpdate, session: DbSession, creator: CurrentCreator
) -> OrganizationRead:
    """Change your organization's name, type, description, website or city; only the
    fields sent change. Without one yet, send name and organization_type to create it."""
    return organization_service.update_mine(session, creator, body)
