import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.auth import Role


class UserRegisterRequest(BaseModel):
    """Payload for user registration & initial organization bootstrapping."""

    email: EmailStr
    password: str = Field(min_length=8, description="Minimum 8 characters password")
    full_name: str = Field(min_length=2, max_length=100)
    organization_name: str | None = Field(default=None, description="Optional organization name")


class UserLoginRequest(BaseModel):
    """Payload for user login."""

    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Access token and refresh token response."""

    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    refresh_token: str


class RefreshTokenRequest(BaseModel):
    """Payload for refreshing an access token."""

    refresh_token: str


class OrganizationMemberResponse(BaseModel):
    """Summary of member's role within an organization."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    role: Role


class UserResponse(BaseModel):
    """Authenticated user profile with active organization memberships."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool
    created_at: datetime
    memberships: list[OrganizationMemberResponse] = []


class OrganizationCreateRequest(BaseModel):
    """Payload to create a new organization."""

    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=100)


class OrganizationResponse(BaseModel):
    """Organization metadata details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    avatar_url: str | None
    created_at: datetime
