import uuid
from typing import Annotated

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role, User
from app.services.auth.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY: dict[Role, int] = {
    Role.OWNER: 40,
    Role.ADMIN: 30,
    Role.MEMBER: 20,
    Role.VIEWER: 10,
}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Dependency extracting and verifying the authenticated user from the Bearer JWT."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise DCPException(
            title="Authentication Required",
            detail="Missing or invalid Bearer authentication token.",
            status_code=401,
            code="UNAUTHENTICATED",
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or not payload.get("sub"):
        raise DCPException(
            title="Invalid Token",
            detail="Authentication token is expired, invalid, or malformed.",
            status_code=401,
            code="INVALID_TOKEN",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise DCPException(
            title="Invalid Token Subject",
            detail="Token subject cannot be parsed.",
            status_code=401,
            code="INVALID_TOKEN",
        ) from None

    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise DCPException(
            title="User Unavailable",
            detail="User account does not exist or has been disabled.",
            status_code=401,
            code="USER_INACTIVE",
        )

    return user


async def get_current_org_membership(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    x_organization_id: Annotated[str | None, Header()] = None,
) -> OrganizationMember:
    """
    Resolves the organization context and validates caller's membership.
    If X-Organization-ID header is provided, it validates membership in that specific organization.
    Otherwise, it defaults to the user's primary/first organization membership.
    """
    if x_organization_id:
        try:
            target_org_id = uuid.UUID(x_organization_id)
        except ValueError:
            raise DCPException(
                title="Invalid Organization Header",
                detail="X-Organization-ID must be a valid UUID.",
                status_code=400,
                code="INVALID_ORG_ID",
            ) from None
        query = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.organization))
            .where(
                OrganizationMember.user_id == current_user.id,
                OrganizationMember.organization_id == target_org_id,
            )
        )
    else:
        # Default to first organization membership
        query = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.organization))
            .where(OrganizationMember.user_id == current_user.id)
            .order_by(OrganizationMember.created_at.asc())
        )

    result = await db.execute(query)
    membership = result.scalar_one_or_none()

    if not membership:
        raise DCPException(
            title="Organization Access Denied",
            detail="You do not have membership in the requested organization context.",
            status_code=403,
            code="FORBIDDEN_ORGANIZATION",
        )

    return membership


def require_role(min_role: Role):
    """
    RBAC dependency factory enforcing minimum role level within current organization.
    Hierarchy: OWNER (40) > ADMIN (30) > MEMBER (20) > VIEWER (10).
    """

    async def role_checker(
        membership: Annotated[OrganizationMember, Depends(get_current_org_membership)],
    ) -> OrganizationMember:
        user_rank = ROLE_HIERARCHY.get(Role(membership.role), 0)
        required_rank = ROLE_HIERARCHY.get(min_role, 0)

        if user_rank < required_rank:
            raise DCPException(
                title="Insufficient Permissions",
                detail=f"This operation requires role '{min_role.value}'. Current role is '{membership.role}'.",
                status_code=403,
                code="INSUFFICIENT_PERMISSIONS",
            )
        return membership

    return role_checker
