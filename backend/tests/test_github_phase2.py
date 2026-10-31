import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db
from app.main import create_application
from app.models.auth import Organization, OrganizationMember, Role, User
from app.schemas.github import RepositoryResponse, WebhookIngestResponse
from app.services.auth.dependencies import get_current_org_membership, get_current_user
from app.services.github.webhook import verify_github_signature

# ==============================================================================
# Webhook Signature Verification Tests
# ==============================================================================


def test_verify_github_signature_valid():
    secret = "my_webhook_secret_key"
    payload = b'{"action": "opened", "pull_request": {"id": 12345}}'
    mac = hmac.new(secret.encode("utf-8"), msg=payload, digestmod=hashlib.sha256)
    valid_signature = f"sha256={mac.hexdigest()}"

    assert verify_github_signature(payload, secret, valid_signature) is True


def test_verify_github_signature_invalid():
    secret = "my_webhook_secret_key"
    payload = b'{"action": "opened"}'
    invalid_signature = "sha256=0000000000000000000000000000000000000000000000000000000000000000"

    assert verify_github_signature(payload, secret, invalid_signature) is False
    assert verify_github_signature(payload, secret, None) is False
    assert verify_github_signature(payload, secret, "invalid_prefix_hash") is False
    assert verify_github_signature(payload, "", signature_header="sha256=123") is False


# ==============================================================================
# Webhook Ingestion API Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_webhook_ingest_missing_delivery_header():
    app = create_application()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/integrations/github/webhooks",
            json={"action": "ping"},
        )
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "MISSING_DELIVERY_HEADER"


@pytest.mark.asyncio
async def test_webhook_ingest_first_delivery_accepted():
    app = create_application()
    mock_db = AsyncMock()

    delivery_id = str(uuid.uuid4())
    mock_response = WebhookIngestResponse(
        status="queued",
        delivery_id=delivery_id,
        event_type="push",
        message="Webhook verified and queued for asynchronous processing.",
    )

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.github.ingest_webhook_delivery",
        new_callable=AsyncMock,
        return_value=(mock_response, 202),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/integrations/github/webhooks",
                headers={
                    "X-GitHub-Delivery": delivery_id,
                    "X-GitHub-Event": "push",
                },
                json={"ref": "refs/heads/main"},
            )
            assert response.status_code == 202
            data = response.json()
            assert data["delivery_id"] == delivery_id
            assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_webhook_ingest_duplicate_delivery_deduplicated():
    app = create_application()
    mock_db = AsyncMock()

    delivery_id = str(uuid.uuid4())
    mock_response = WebhookIngestResponse(
        status="duplicate",
        delivery_id=delivery_id,
        event_type="push",
        message="Duplicate delivery identifier already processed or in-flight.",
    )

    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.github.ingest_webhook_delivery",
        new_callable=AsyncMock,
        return_value=(mock_response, 200),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/integrations/github/webhooks",
                headers={
                    "X-GitHub-Delivery": delivery_id,
                    "X-GitHub-Event": "push",
                },
                json={"ref": "refs/heads/main"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["delivery_id"] == delivery_id
            assert data["status"] == "duplicate"


# ==============================================================================
# Repository Management API Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_repositories_list_and_toggle_monitoring():
    app = create_application()

    org_id = uuid.uuid4()
    user = User(
        id=uuid.uuid4(),
        email="admin@dcp.io",
        full_name="Admin User",
        hashed_password="hash",
    )
    org = Organization(id=org_id, name="Test Org", slug="test-org")
    membership = OrganizationMember(
        id=uuid.uuid4(),
        organization_id=org_id,
        user_id=user.id,
        role=Role.ADMIN,
        organization=org,
    )

    repo_id = uuid.uuid4()
    repo_dto = RepositoryResponse(
        id=repo_id,
        organization_id=org_id,
        github_repo_id=123456,
        name="backend-service",
        full_name="test-org/backend-service",
        default_branch="main",
        is_private=True,
        is_monitored=True,
        primary_language="Python",
        last_synced_at=None,
        created_at="2026-10-31T12:00:00Z",
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_org_membership] = lambda: membership
    app.dependency_overrides[get_db] = lambda: mock_db

    # Test listing repositories
    with patch(
        "app.api.v1.endpoints.repositories.list_organization_repositories",
        new_callable=AsyncMock,
        return_value=[repo_dto],
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/repositories")
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "backend-service"
            assert data[0]["is_monitored"] is True

    # Test toggling monitoring
    repo_dto_paused = RepositoryResponse(
        id=repo_id,
        organization_id=org_id,
        github_repo_id=123456,
        name="backend-service",
        full_name="test-org/backend-service",
        default_branch="main",
        is_private=True,
        is_monitored=False,
        primary_language="Python",
        last_synced_at=None,
        created_at="2026-10-31T12:00:00Z",
    )
    with patch(
        "app.api.v1.endpoints.repositories.toggle_repository_monitoring",
        new_callable=AsyncMock,
        return_value=repo_dto_paused,
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.patch(
                f"/api/v1/repositories/{repo_id}",
                json={"is_monitored": False},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["is_monitored"] is False
