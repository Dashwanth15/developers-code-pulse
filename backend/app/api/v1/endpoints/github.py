import json
import os
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DCPException
from app.database.session import get_db
from app.models.auth import OrganizationMember, Role
from app.models.github import WebhookDelivery
from app.schemas.github import DiscoveredRepoResponse, WebhookIngestResponse
from app.services.auth.dependencies import require_role
from app.services.github.github_service import discover_repositories, ingest_webhook_delivery
from app.services.github.webhook import verify_github_signature

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/integrations/github", tags=["GitHub Integration"])


@router.get(
    "/install",
    status_code=status.HTTP_200_OK,
    summary="GitHub App Installation Info",
    description="Returns GitHub App setup details and authorization link.",
)
async def get_github_install_info(
    _membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
) -> dict[str, str]:
    app_id = os.getenv("GITHUB_APP_ID", "")
    webhook_secret_set = bool(os.getenv("GITHUB_WEBHOOK_SECRET"))
    token_set = bool(os.getenv("GITHUB_TOKEN"))

    install_url = (
        "https://github.com/apps/developers-code-pulse/installations/new"
        if app_id
        else "https://github.com/settings/tokens"
    )

    return {
        "status": "CONFIGURED" if (app_id or token_set) else "PENDING_SETUP",
        "app_id": app_id,
        "install_url": install_url,
        "token_configured": str(token_set),
        "webhook_secret_configured": str(webhook_secret_set),
    }


@router.get(
    "/repositories",
    response_model=list[DiscoveredRepoResponse],
    status_code=status.HTTP_200_OK,
    summary="Discover Authorized GitHub Repositories",
    description="Lists repositories accessible via GitHub App or configured integration token.",
)
async def get_discovered_repositories(
    membership: Annotated[OrganizationMember, Depends(require_role(Role.MEMBER))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DiscoveredRepoResponse]:
    return await discover_repositories(db, membership.organization_id)


@router.post(
    "/webhooks",
    response_model=WebhookIngestResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        status.HTTP_200_OK: {
            "model": WebhookIngestResponse,
            "description": "Duplicate delivery skipped.",
        },
        status.HTTP_401_UNAUTHORIZED: {"description": "Invalid HMAC signature."},
    },
    summary="GitHub Webhook Ingestion",
    description="Receives GitHub webhooks, verifies HMAC signature, deduplicates delivery, and queues for Celery processing.",
)
async def receive_github_webhook(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_github_delivery: Annotated[str | None, Header()] = None,
    x_github_event: Annotated[str | None, Header()] = None,
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> WebhookIngestResponse:
    if not x_github_delivery:
        raise DCPException(
            title="Missing Delivery Header",
            detail="Header 'X-GitHub-Delivery' is required.",
            status_code=400,
            code="MISSING_DELIVERY_HEADER",
        )

    event_type = x_github_event or "unknown"
    raw_payload_bytes = await request.body()

    # Verify HMAC signature if GITHUB_WEBHOOK_SECRET is configured
    webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
    if webhook_secret and not verify_github_signature(
        raw_payload_bytes, webhook_secret, x_hub_signature_256
    ):
        logger.warning("webhook_invalid_signature_rejected", delivery_id=x_github_delivery)
        raise DCPException(
            title="Unauthorized Webhook",
            detail="HMAC-SHA256 signature verification failed.",
            status_code=401,
            code="INVALID_WEBHOOK_SIGNATURE",
        )

    try:
        payload = json.loads(raw_payload_bytes.decode("utf-8")) if raw_payload_bytes else {}
    except ValueError as exc:
        raise DCPException(
            title="Malformed JSON",
            detail="Unable to parse webhook payload as JSON.",
            status_code=400,
            code="MALFORMED_WEBHOOK_PAYLOAD",
        ) from exc

    result, status_code = await ingest_webhook_delivery(
        db=db,
        delivery_id=x_github_delivery,
        event_type=event_type,
        payload=payload,
    )

    response.status_code = status_code
    return result


@router.get(
    "/deliveries",
    status_code=status.HTTP_200_OK,
    summary="List Webhook Deliveries",
    description="Audit trail of received webhook deliveries.",
)
async def list_webhook_deliveries(
    _membership: Annotated[OrganizationMember, Depends(require_role(Role.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict]:
    query = select(WebhookDelivery).order_by(WebhookDelivery.received_at.desc()).limit(50)
    result = await db.execute(query)
    deliveries = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "delivery_id": d.delivery_id,
            "event_type": d.event_type,
            "status": d.status,
            "repository_id": str(d.repository_id) if d.repository_id else None,
            "received_at": d.received_at.isoformat(),
            "processed_at": d.processed_at.isoformat() if d.processed_at else None,
        }
        for d in deliveries
    ]
