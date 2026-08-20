"""GitHub REST API client with retry and circuit breaker (§3.1, L8)."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from backend.core.exceptions import GitHubAPIError, RetryableError
from backend.reliability.retry import retry_async
from backend.settings import settings

logger = structlog.get_logger(__name__)


class GitHubClient:
    """Async GitHub REST API client for PR operations."""

    BASE_URL = "https://api.github.com"

    def __init__(self) -> None:
        self._token: str | None = None

    async def _get_headers(self) -> dict[str, str]:
        """Build authorization headers.

        In production this would use GitHub App installation tokens.
        For development, falls back to a personal access token if set.
        """
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "WARD-PR-Review-Agent/0.1",
        }
        if settings.github_app_id:
            headers["Authorization"] = f"Bearer {settings.github_app_id}"
        return headers

    @retry_async(max_retries=3, base_delay_ms=1000)
    async def get_pull_request_diff(self, repo: str, pr_number: int) -> str:
        """Fetch the diff for a pull request.

        Args:
            repo: Full repo name (e.g. "org/repo").
            pr_number: PR number.

        Returns:
            The unified diff as a string.
        """
        url = f"{self.BASE_URL}/repos/{repo}/pulls/{pr_number}"
        headers = await self._get_headers()
        headers["Accept"] = "application/vnd.github.v3.diff"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)

        if response.status_code == 200:
            return response.text

        if response.status_code in (429, 502, 503, 504):
            raise RetryableError(f"GitHub API returned {response.status_code}")

        raise GitHubAPIError(response.status_code, response.text[:500])

    @retry_async(max_retries=2, base_delay_ms=1000)
    async def post_review(
        self,
        repo: str,
        pr_number: int,
        *,
        body: str,
        event: str = "COMMENT",
        comments: list[dict[str, Any]] | None = None,
    ) -> int:
        """Post a review to a pull request.

        Args:
            repo: Full repo name.
            pr_number: PR number.
            body: Review summary text.
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES).
            comments: Inline review comments.

        Returns:
            The GitHub review ID.
        """
        url = f"{self.BASE_URL}/repos/{repo}/pulls/{pr_number}/reviews"
        headers = await self._get_headers()

        payload: dict[str, Any] = {"body": body, "event": event}
        if comments:
            payload["comments"] = comments

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code in (200, 201):
            data = response.json()
            review_id = data.get("id", 0)
            logger.info(
                "github.review_posted",
                repo=repo,
                pr_number=pr_number,
                review_id=review_id,
            )
            return review_id

        if response.status_code in (429, 502, 503, 504):
            raise RetryableError(f"GitHub API returned {response.status_code}")

        raise GitHubAPIError(response.status_code, response.text[:500])
