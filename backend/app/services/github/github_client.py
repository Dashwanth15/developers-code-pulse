import os

import httpx
import structlog

from app.core.config import get_settings
from app.core.exceptions import DCPException
from app.schemas.github import DiscoveredRepoResponse

logger = structlog.get_logger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubClient:
    """Asynchronous client for querying GitHub REST APIs."""

    def __init__(self, token: str | None = None):
        self.token = token or get_settings().GITHUB_TOKEN or os.getenv("GITHUB_TOKEN")

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "DevelopersCodePulse/0.1.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def get_user_repositories(self) -> list[DiscoveredRepoResponse]:
        """Fetches accessible repositories for the configured GitHub token or app."""
        if not self.token:
            logger.warning("github_token_missing_for_repo_discovery")
            return []

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_BASE}/user/repos",
                    headers=self._get_headers(),
                    params={"per_page": 100, "sort": "updated"},
                )
                if response.status_code == 401:
                    raise DCPException(
                        title="GitHub Authentication Failed",
                        detail="The configured GitHub token or installation is invalid or expired.",
                        status_code=401,
                        code="GITHUB_UNAUTHORIZED",
                    )
                if response.status_code != 200:
                    logger.error(
                        "github_api_error", status=response.status_code, body=response.text
                    )
                    return []

                raw_repos = response.json()
                return [
                    DiscoveredRepoResponse(
                        github_repo_id=repo["id"],
                        name=repo["name"],
                        full_name=repo["full_name"],
                        default_branch=repo.get("default_branch", "main"),
                        is_private=repo.get("private", True),
                        primary_language=repo.get("language"),
                        html_url=repo.get("html_url", ""),
                        is_connected=False,
                    )
                    for repo in raw_repos
                ]
            except httpx.RequestError as exc:
                logger.error("github_client_network_error", error=str(exc))
                raise DCPException(
                    title="GitHub API Network Error",
                    detail=f"Failed to communicate with GitHub API: {str(exc)}",
                    status_code=502,
                    code="GITHUB_API_UNREACHABLE",
                ) from exc

    async def get_repository_details(self, full_name: str) -> dict | None:
        """Fetches metadata for a single repository."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_BASE}/repos/{full_name}",
                    headers=self._get_headers(),
                )
                if response.status_code == 200:
                    return response.json()
                return None
            except httpx.RequestError as exc:
                logger.error("github_client_error", full_name=full_name, error=str(exc))
                return None

    async def get_repository_commits(
        self, full_name: str, per_page: int = 100
    ) -> list[dict]:
        """Fetches recent commits for a repository."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{GITHUB_API_BASE}/repos/{full_name}/commits",
                    headers=self._get_headers(),
                    params={"per_page": min(per_page, 100)},
                )
                if response.status_code == 200:
                    return response.json()
                logger.warning(
                    "github_commits_fetch_failed",
                    status=response.status_code,
                    full_name=full_name,
                )
                return []
            except httpx.RequestError as exc:
                logger.error("github_client_error", full_name=full_name, error=str(exc))
                return []
