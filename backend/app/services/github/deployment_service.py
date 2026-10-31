import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commits import Commit
from app.models.dora import Deployment, DeploymentIncident, Incident
from app.models.github import Repository

logger = structlog.get_logger(__name__)


def parse_github_datetime(val: str | None) -> datetime | None:
    """Safely converts ISO-8601 GitHub datetime strings to UTC datetime."""
    if not val:
        return None
    try:
        return datetime.fromisoformat(val.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def classify_environment(env_raw: str | None) -> str:
    """
    Categorizes raw environment strings into standard tiers:
    production, staging, or development.
    """
    if not env_raw:
        return "development"
    env_clean = env_raw.strip().lower()
    if env_clean in ("production", "prod", "live", "release", "prd"):
        return "production"
    if env_clean in ("staging", "stage", "uat", "qa", "pre-prod", "preprod"):
        return "staging"
    return "development"


async def calculate_deployment_lead_time(
    db: AsyncSession,
    organization_id: uuid.UUID,
    commit_sha: str | None,
    deployed_at: datetime,
) -> float | None:
    """
    Calculates lead time in seconds from initial commit authoring / PR merge to deployment.
    """
    if not commit_sha:
        return None

    # 1. Direct Commit match
    c_res = await db.execute(
        select(Commit)
        .join(Repository, Commit.repository_id == Repository.id)
        .where(
            Commit.commit_sha == commit_sha,
            Repository.organization_id == organization_id,
        )
    )
    commit = c_res.scalars().first()
    if commit and commit.committed_at:
        diff_sec = (deployed_at - commit.committed_at).total_seconds()
        if diff_sec >= 0:
            return round(diff_sec, 1)

    return None


async def link_incidents_to_deployment(
    db: AsyncSession,
    deployment: Deployment,
    window_hours: int = 4,
) -> list[DeploymentIncident]:
    """
    Auto-correlates incidents detected within window_hours following a production deployment.
    """
    if deployment.environment.lower() not in ("production", "prod"):
        return []

    cutoff_end = deployment.deployed_at + timedelta(hours=window_hours)
    query = select(Incident).where(
        Incident.organization_id == deployment.organization_id,
        Incident.started_at >= deployment.deployed_at,
        Incident.started_at <= cutoff_end,
    )
    if deployment.repository_id:
        query = query.where(
            (Incident.repository_id == deployment.repository_id) | (Incident.repository_id.is_(None))
        )

    res = await db.execute(query)
    matching_incidents = list(res.scalars().all())

    created_links: list[DeploymentIncident] = []
    for inc in matching_incidents:
        # Check if already linked
        existing_q = select(DeploymentIncident).where(
            DeploymentIncident.deployment_id == deployment.id,
            DeploymentIncident.incident_id == inc.id,
        )
        if (await db.execute(existing_q)).scalars().first():
            continue

        link = DeploymentIncident(
            id=uuid.uuid4(),
            deployment_id=deployment.id,
            incident_id=inc.id,
            relationship_type="DETECTED_AFTER",
            confidence="HIGH" if inc.repository_id == deployment.repository_id else "MEDIUM",
            provenance={
                "rule": "AUTO_TIME_PROXIMITY_CORRELATION",
                "delta_seconds": (inc.started_at - deployment.deployed_at).total_seconds(),
                "window_hours": window_hours,
            },
        )
        db.add(link)
        created_links.append(link)

    if created_links:
        await db.commit()
    return created_links


async def ingest_deployment_payload(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository: Repository | None,
    data: dict[str, Any],
) -> Deployment:
    """
    Ingests and normalizes a deployment event from GitHub Webhook, API, or external adapter.
    """
    external_id = str(data.get("id") or data.get("external_deployment_id") or "")
    if not external_id:
        external_id = f"ext-{uuid.uuid4().hex[:12]}"

    raw_env = data.get("environment") or "production"
    environment = classify_environment(raw_env)

    raw_status = (data.get("status") or data.get("state") or "SUCCESS").upper()
    status_map = {
        "SUCCESS": "SUCCESS",
        "COMPLETED": "SUCCESS",
        "FAILURE": "FAILURE",
        "FAILED": "FAILURE",
        "ERROR": "FAILURE",
        "CANCELLED": "CANCELLED",
        "IN_PROGRESS": "IN_PROGRESS",
        "QUEUED": "QUEUED",
        "PENDING": "IN_PROGRESS",
    }
    status = status_map.get(raw_status, "SUCCESS")

    deployed_at = parse_github_datetime(data.get("deployed_at") or data.get("created_at")) or datetime.now(UTC)
    completed_at = parse_github_datetime(data.get("completed_at") or data.get("updated_at"))

    commit_sha = data.get("commit_sha") or data.get("sha") or (data.get("head_commit") or {}).get("id")
    ref_name = data.get("ref_name") or data.get("ref")
    source = data.get("source") or "GITHUB_DEPLOYMENT"
    metadata_info = data.get("metadata") or {}

    # Check for existing record
    existing_q = select(Deployment).where(
        Deployment.organization_id == organization_id,
        Deployment.external_deployment_id == external_id,
        Deployment.source == source,
    )
    existing = (await db.execute(existing_q)).scalars().first()

    lead_time_sec = data.get("lead_time_seconds")
    if lead_time_sec is None and commit_sha:
        lead_time_sec = await calculate_deployment_lead_time(
            db, organization_id, commit_sha, deployed_at
        )

    if existing:
        existing.status = status
        existing.completed_at = completed_at
        if lead_time_sec is not None:
            existing.lead_time_seconds = lead_time_sec
        existing.metadata_payload = {**existing.metadata_payload, **metadata_info}
        await db.commit()
        await db.refresh(existing)
        target = existing
    else:
        new_dep = Deployment(
            id=uuid.uuid4(),
            organization_id=organization_id,
            repository_id=repository.id if repository else None,
            external_deployment_id=external_id,
            environment=environment,
            status=status,
            deployed_at=deployed_at,
            completed_at=completed_at,
            commit_sha=commit_sha,
            ref_name=ref_name,
            source=source,
            lead_time_seconds=lead_time_sec,
            metadata_payload=metadata_info,
        )
        db.add(new_dep)
        await db.commit()
        await db.refresh(new_dep)
        target = new_dep

    # Auto-link incidents if any match
    await link_incidents_to_deployment(db, target)
    return target


async def ingest_incident_record(
    db: AsyncSession,
    organization_id: uuid.UUID,
    repository: Repository | None,
    data: dict[str, Any],
) -> Incident:
    """
    Ingests and normalizes an incident record from monitoring tools or manual creation.
    """
    external_id = str(data.get("id") or data.get("external_incident_id") or "")
    if not external_id:
        external_id = f"inc-{uuid.uuid4().hex[:12]}"

    title = data.get("title") or "Production Degradation"
    severity = (data.get("severity") or "MEDIUM").upper()
    status = (data.get("status") or "OPEN").upper()

    started_at = parse_github_datetime(data.get("started_at")) or datetime.now(UTC)
    resolved_at = parse_github_datetime(data.get("resolved_at"))
    source = data.get("source") or "MANUAL"
    meta = data.get("metadata") or {}

    dur_sec = None
    if resolved_at and started_at:
        dur_sec = max((resolved_at - started_at).total_seconds(), 0.0)

    # Check for existing
    existing_q = select(Incident).where(
        Incident.organization_id == organization_id,
        Incident.external_incident_id == external_id,
    )
    existing = (await db.execute(existing_q)).scalars().first()

    if existing:
        existing.title = title
        existing.severity = severity
        existing.status = status
        existing.resolved_at = resolved_at
        existing.recovery_duration_seconds = dur_sec
        existing.metadata_payload = {**existing.metadata_payload, **meta}
        await db.commit()
        await db.refresh(existing)
        target = existing
    else:
        new_inc = Incident(
            id=uuid.uuid4(),
            organization_id=organization_id,
            repository_id=repository.id if repository else None,
            external_incident_id=external_id,
            title=title,
            severity=severity,
            status=status,
            started_at=started_at,
            resolved_at=resolved_at,
            recovery_duration_seconds=dur_sec,
            source=source,
            metadata_payload=meta,
        )
        db.add(new_inc)
        await db.commit()
        await db.refresh(new_inc)
        target = new_inc

    # If linked deployment specified
    dep_id = data.get("deployment_id")
    if dep_id:
        dep = await db.get(Deployment, dep_id)
        if dep and dep.organization_id == organization_id:
            link = DeploymentIncident(
                id=uuid.uuid4(),
                deployment_id=dep.id,
                incident_id=target.id,
                relationship_type="CAUSED_BY",
                confidence="HIGH",
                provenance={"source": "USER_LINKED"},
            )
            db.add(link)
            await db.commit()

    return target
