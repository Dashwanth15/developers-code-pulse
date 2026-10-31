import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DCPException
from app.models.github import Repository, WebhookDelivery
from app.schemas.github import (
    ConnectRepositoryRequest,
    DiscoveredRepoResponse,
    RepositoryResponse,
    WebhookIngestResponse,
)
from app.services.github.github_client import GitHubClient

logger = structlog.get_logger(__name__)


async def list_organization_repositories(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> list[RepositoryResponse]:
    """Retrieves all monitored repositories for an organization."""
    query = (
        select(Repository)
        .where(Repository.organization_id == organization_id)
        .order_by(Repository.name.asc())
    )
    result = await db.execute(query)
    repos = result.scalars().all()
    return [RepositoryResponse.model_validate(r) for r in repos]


async def discover_repositories(
    db: AsyncSession,
    organization_id: uuid.UUID,
) -> list[DiscoveredRepoResponse]:
    """Discovers GitHub repositories and marks which are already connected in DCP."""
    client = GitHubClient()
    discovered = await client.get_user_repositories()

    # Query currently connected github_repo_ids for this org
    query = select(Repository.github_repo_id).where(Repository.organization_id == organization_id)
    result = await db.execute(query)
    connected_ids = set(result.scalars().all())

    for repo in discovered:
        repo.is_connected = repo.github_repo_id in connected_ids

    return discovered


async def connect_repository(
    db: AsyncSession,
    organization_id: uuid.UUID,
    request: ConnectRepositoryRequest,
) -> RepositoryResponse:
    """Connects an authorized repository to the organization for metric monitoring."""
    # Check if already connected in this organization
    query = select(Repository).where(
        Repository.organization_id == organization_id,
        Repository.github_repo_id == request.github_repo_id,
    )
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    if existing:
        raise DCPException(
            title="Repository Already Connected",
            detail=f"Repository '{request.full_name}' is already connected to this organization.",
            status_code=409,
            code="REPO_ALREADY_CONNECTED",
        )

    repo = Repository(
        organization_id=organization_id,
        github_repo_id=request.github_repo_id,
        name=request.name,
        full_name=request.full_name,
        default_branch=request.default_branch,
        is_private=request.is_private,
        is_monitored=True,
        primary_language=request.primary_language,
    )
    db.add(repo)
    await db.flush()
    return RepositoryResponse.model_validate(repo)


async def toggle_repository_monitoring(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository_id: uuid.UUID,
    is_monitored: bool,
) -> RepositoryResponse:
    """Enables or disables telemetry collection for a connected repository."""
    query = select(Repository).where(
        Repository.id == repository_id,
        Repository.organization_id == organization_id,
    )
    result = await db.execute(query)
    repo = result.scalar_one_or_none()
    if not repo:
        raise DCPException(
            title="Repository Not Found",
            detail=f"Repository '{repository_id}' does not exist in this organization.",
            status_code=404,
            code="REPOSITORY_NOT_FOUND",
        )

    repo.is_monitored = is_monitored
    await db.flush()
    return RepositoryResponse.model_validate(repo)


async def ingest_webhook_delivery(
    db: AsyncSession,
    delivery_id: str,
    event_type: str,
    payload: dict,
) -> tuple[WebhookIngestResponse, int]:
    """
    Idempotent webhook ingestion:
    1. Checks if delivery_id is already recorded.
    2. If duplicate, returns status 'duplicate' with HTTP 200.
    3. If new, records delivery and delegates async processing to Celery.
    """
    query = select(WebhookDelivery).where(WebhookDelivery.delivery_id == delivery_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        logger.info("duplicate_webhook_delivery_skipped", delivery_id=delivery_id)
        return (
            WebhookIngestResponse(
                status="duplicate",
                delivery_id=delivery_id,
                event_type=event_type,
                message="Duplicate delivery identifier already processed or in-flight.",
            ),
            200,
        )

    # Resolve target repository if present in payload
    repo_id = None
    raw_repo = payload.get("repository")
    if raw_repo and "id" in raw_repo:
        repo_query = select(Repository.id).where(Repository.github_repo_id == raw_repo["id"])
        repo_res = await db.execute(repo_query)
        repo_id = repo_res.scalar_one_or_none()

    delivery = WebhookDelivery(
        delivery_id=delivery_id,
        event_type=event_type,
        repository_id=repo_id,
        payload=payload,
        status="PENDING",
    )
    db.add(delivery)
    await db.flush()

    # Enqueue processing in Celery
    try:
        from app.workers.tasks import process_github_webhook

        process_github_webhook.delay(delivery_id)
    except Exception as exc:
        logger.error("failed_to_enqueue_celery_task", error=str(exc))

    return (
        WebhookIngestResponse(
            status="queued",
            delivery_id=delivery_id,
            event_type=event_type,
            message="Webhook verified and queued for asynchronous processing.",
        ),
        202,
    )
