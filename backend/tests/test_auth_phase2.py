import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.main import create_application
from app.models.auth import OrganizationMember, Role, User
from app.schemas.auth import UserLoginRequest, UserRegisterRequest, UserResponse
from app.services.auth import auth_service
from app.services.auth.dependencies import get_current_user, require_role
from app.services.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)

# ==============================================================================
# Security & Hashing Unit Tests
# ==============================================================================


def test_password_hashing_and_verification():
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)

    assert hashed != password
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_token_creation_and_decoding():
    user_id = str(uuid.uuid4())
    token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(minutes=15),
        claims={"email": "alice@example.com"},
    )

    payload = decode_access_token(token)
    assert payload is not None
    assert payload["sub"] == user_id
    assert payload["email"] == "alice@example.com"
    assert "exp" in payload


def test_jwt_access_token_expired():
    user_id = str(uuid.uuid4())
    expired_token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-10),
    )

    payload = decode_access_token(expired_token)
    assert payload is None


def test_refresh_token_sha256_hashing():
    raw_token = "random_refresh_token_string_abc123"
    hashed_1 = hash_refresh_token(raw_token)
    hashed_2 = hash_refresh_token(raw_token)

    assert hashed_1 == hashed_2
    assert len(hashed_1) == 64  # SHA-256 hex string


# ==============================================================================
# Auth Service Unit Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_register_user_creates_owner_and_org():
    mock_db = AsyncMock()

    # DB returns None for existing user query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    req = UserRegisterRequest(
        email="developer@company.com",
        password="ValidPassword123!",
        full_name="Dev User",
        organization_name="Acme Engineering",
    )

    user, tokens = await auth_service.register_user(mock_db, req)

    assert user.email == "developer@company.com"
    assert user.full_name == "Dev User"
    assert verify_password("ValidPassword123!", user.hashed_password)
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None
    assert mock_db.flush.called


@pytest.mark.asyncio
async def test_register_user_duplicate_email_conflict():
    mock_db = AsyncMock()

    existing_user = User(
        id=uuid.uuid4(),
        email="duplicate@company.com",
        hashed_password="hash",
        full_name="Existing",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_db.execute.return_value = mock_result

    req = UserRegisterRequest(
        email="duplicate@company.com",
        password="ValidPassword123!",
        full_name="Existing User",
    )

    with pytest.raises(DCPException) as exc_info:
        await auth_service.register_user(mock_db, req)

    assert exc_info.value.status_code == 409
    assert exc_info.value.code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_authenticate_user_success_and_failure():
    mock_db = AsyncMock()

    pwd_hash = hash_password("ValidPassword123!")
    user = User(
        id=uuid.uuid4(),
        email="valid@company.com",
        hashed_password=pwd_hash,
        full_name="Valid User",
        is_active=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    mock_db.execute.return_value = mock_result

    # Success case
    authenticated_user, tokens = await auth_service.authenticate_user(
        mock_db,
        UserLoginRequest(email="valid@company.com", password="ValidPassword123!"),
    )
    assert authenticated_user.id == user.id
    assert tokens.access_token is not None

    # Wrong password case
    with pytest.raises(DCPException) as exc_info:
        await auth_service.authenticate_user(
            mock_db,
            UserLoginRequest(email="valid@company.com", password="WrongPassword123!"),
        )
    assert exc_info.value.status_code == 401
    assert exc_info.value.code == "INVALID_CREDENTIALS"


# ==============================================================================
# RBAC & Multi-tenant Authorization Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_require_role_hierarchy():
    owner_member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=Role.OWNER,
    )
    admin_member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=Role.ADMIN,
    )
    viewer_member = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role=Role.VIEWER,
    )

    admin_gate = require_role(Role.ADMIN)

    # OWNER passes ADMIN requirement
    assert await admin_gate(membership=owner_member) == owner_member

    # ADMIN passes ADMIN requirement
    assert await admin_gate(membership=admin_member) == admin_member

    # VIEWER fails ADMIN requirement with 403
    with pytest.raises(DCPException) as exc_info:
        await admin_gate(membership=viewer_member)
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "INSUFFICIENT_PERMISSIONS"


# ==============================================================================
# Fast-API Endpoints Integration with Dependency Overrides
# ==============================================================================


@pytest.mark.asyncio
async def test_api_auth_me_endpoint():
    app = create_application()
    user_id = uuid.uuid4()

    test_user = User(
        id=user_id,
        email="testme@example.com",
        full_name="Test Profile",
        hashed_password="hash",
        is_active=True,
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: test_user
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_user_dto = UserResponse(
        id=user_id,
        email="testme@example.com",
        full_name="Test Profile",
        avatar_url=None,
        is_active=True,
        created_at=datetime.now(UTC),
        memberships=[],
    )

    with patch(
        "app.api.v1.endpoints.auth.get_user_profile",
        new_callable=AsyncMock,
        return_value=mock_user_dto,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "testme@example.com"
            assert data["full_name"] == "Test Profile"


@pytest.mark.asyncio
async def test_api_organization_multitenant_forbidden():
    app = create_application()

    user_a = User(
        id=uuid.uuid4(),
        email="usera@example.com",
        full_name="User A",
        hashed_password="hash",
        is_active=True,
    )
    org_b_id = uuid.uuid4()

    mock_db = AsyncMock()
    # Mock membership check returning None for org_b_id
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_current_user] = lambda: user_a
    app.dependency_overrides[get_db] = lambda: mock_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # User A attempts to access Org B
        response = await client.get(
            f"/api/v1/organizations/{org_b_id}",
            headers={"X-Organization-ID": str(org_b_id)},
        )
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == "FORBIDDEN_ORGANIZATION"
