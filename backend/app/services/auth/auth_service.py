import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.exceptions import DCPException
from app.models.auth import Organization, OrganizationMember, RefreshToken, Role, User
from app.schemas.auth import (
    OrganizationMemberResponse,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth.security import (
    create_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

settings = get_settings()


def slugify(text: str) -> str:
    """Generates a clean URL slug from input text."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


async def register_user(
    db: AsyncSession, request: UserRegisterRequest
) -> tuple[User, TokenResponse]:
    """Registers a new user account, bootstraps their primary organization, and issues tokens."""
    # Check for existing email
    query = select(User).where(User.email == request.email.lower().strip())
    result = await db.execute(query)
    if result.scalar_one_or_none():
        raise DCPException(
            title="Email Already Registered",
            detail=f"An account with email '{request.email}' already exists.",
            status_code=409,
            code="EMAIL_ALREADY_EXISTS",
        )

    # Create User
    user = User(
        email=request.email.lower().strip(),
        hashed_password=hash_password(request.password),
        full_name=request.full_name.strip(),
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # Bootstrap default Organization
    org_name = request.organization_name or f"{user.full_name}'s Team"
    base_slug = slugify(org_name) or "team"
    unique_slug = f"{base_slug}-{uuid.uuid4().hex[:6]}"

    org = Organization(
        name=org_name,
        slug=unique_slug,
    )
    db.add(org)
    await db.flush()

    # Assign user as Organization Owner
    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=Role.OWNER,
    )
    db.add(member)
    await db.flush()

    # Issue Tokens
    tokens = await issue_tokens_for_user(db, user.id)
    return user, tokens


async def authenticate_user(
    db: AsyncSession, request: UserLoginRequest
) -> tuple[User, TokenResponse]:
    """Validates user credentials and issues token pair."""
    query = select(User).where(User.email == request.email.lower().strip())
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        raise DCPException(
            title="Invalid Credentials",
            detail="Incorrect email or password.",
            status_code=401,
            code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise DCPException(
            title="Account Inactive",
            detail="This user account has been deactivated.",
            status_code=403,
            code="ACCOUNT_INACTIVE",
        )

    tokens = await issue_tokens_for_user(db, user.id)
    return user, tokens


async def issue_tokens_for_user(db: AsyncSession, user_id: uuid.UUID) -> TokenResponse:
    """Generates an access token and persists a rotating hashed refresh token."""
    access_token = create_access_token(subject=user_id)
    raw_refresh_token = secrets.token_urlsafe(48)
    token_hash = hash_refresh_token(raw_refresh_token)

    refresh_entity = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        revoked=False,
    )
    db.add(refresh_entity)
    await db.flush()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in_seconds=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        refresh_token=raw_refresh_token,
    )


async def refresh_user_token(db: AsyncSession, raw_refresh_token: str) -> TokenResponse:
    """Validates an incoming refresh token, revokes it, and issues a rotated pair."""
    token_hash = hash_refresh_token(raw_refresh_token)
    query = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await db.execute(query)
    stored_token = result.scalar_one_or_none()

    if not stored_token or stored_token.revoked:
        raise DCPException(
            title="Invalid Refresh Token",
            detail="The refresh token is invalid or has been revoked.",
            status_code=401,
            code="INVALID_REFRESH_TOKEN",
        )

    if stored_token.expires_at < datetime.now(UTC):
        raise DCPException(
            title="Expired Refresh Token",
            detail="The refresh token has expired. Please log in again.",
            status_code=401,
            code="EXPIRED_REFRESH_TOKEN",
        )

    # Revoke old refresh token (Strict Token Rotation)
    stored_token.revoked = True
    await db.flush()

    # Issue new pair
    return await issue_tokens_for_user(db, stored_token.user_id)


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> UserResponse:
    """Fetches user profile along with all active organization memberships."""
    query = (
        select(User)
        .options(selectinload(User.memberships).selectinload(OrganizationMember.organization))
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise DCPException(
            title="User Not Found",
            detail="User account does not exist.",
            status_code=404,
            code="USER_NOT_FOUND",
        )

    memberships_data = [
        OrganizationMemberResponse(
            id=m.id,
            organization_id=m.organization_id,
            organization_name=m.organization.name,
            organization_slug=m.organization.slug,
            role=m.role,
        )
        for m in user.memberships
    ]

    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        created_at=user.created_at,
        memberships=memberships_data,
    )
