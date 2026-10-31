import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import Organization, OrganizationMember, Role, User
from app.schemas.auth import (
    OrganizationCreateRequest,
    OrganizationMemberResponse,
    OrganizationResponse,
)
from app.services.auth.auth_service import slugify
from app.services.auth.dependencies import (
    get_current_org_membership,
    get_current_user,
    require_role,
)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get(
    "",
    response_model=list[OrganizationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organizations",
    description="Lists all organizations the authenticated user belongs to.",
)
async def list_organizations(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationResponse]:
    query = (
        select(Organization)
        .join(OrganizationMember)
        .where(OrganizationMember.user_id == current_user.id)
        .order_by(Organization.name.asc())
    )
    result = await db.execute(query)
    orgs = result.scalars().all()
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Organization",
    description="Creates a new organization tenant and assigns the creator as Owner.",
)
async def create_organization(
    request: OrganizationCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationResponse:
    base_slug = request.slug or slugify(request.name) or "team"
    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=request.name.strip(),
        slug=unique_slug,
    )
    db.add(org)
    await db.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role=Role.OWNER,
    )
    db.add(member)
    await db.flush()

    return OrganizationResponse.model_validate(org)


@router.get(
    "/{organization_id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Organization Details",
    description="Retrieves organization metadata (enforcing tenant authorization).",
)
async def get_organization(
    organization_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationResponse:
    if membership.organization_id != organization_id:
        raise DCPException(
            title="Access Denied",
            detail="You are not authorized to view this organization.",
            status_code=403,
            code="FORBIDDEN_ORGANIZATION",
        )

    query = select(Organization).where(Organization.id == organization_id)
    result = await db.execute(query)
    org = result.scalar_one_or_none()
    return OrganizationResponse.model_validate(org)


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List Organization Members",
    description="Lists members and roles in the organization.",
)
async def list_members(
    organization_id: uuid.UUID,
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationMemberResponse]:
    if membership.organization_id != organization_id:
        raise DCPException(
            title="Access Denied",
            detail="You are not authorized to view members of this organization.",
            status_code=403,
            code="FORBIDDEN_ORGANIZATION",
        )

    query = (
        select(OrganizationMember)
        .options(selectinload(OrganizationMember.organization))
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.created_at.asc())
    )
    result = await db.execute(query)
    members = result.scalars().all()
    return [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            role=m.role,
        )
        for m in members
    ]
