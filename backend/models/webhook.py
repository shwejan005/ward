"""GitHub webhook payload models.

Typed Pydantic models for the GitHub pull_request webhook event payload.
Only the fields WARD actually uses are modeled; the rest are ignored.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    """Minimal GitHub user representation."""

    login: str
    id: int


class GitHubRepo(BaseModel):
    """Minimal GitHub repository representation."""

    full_name: str
    clone_url: str | None = None
    default_branch: str = "main"


class PullRequestHead(BaseModel):
    """The head (source) ref of a pull request."""

    sha: str
    ref: str
    repo: GitHubRepo | None = None


class PullRequestBase(BaseModel):
    """The base (target) ref of a pull request."""

    sha: str
    ref: str


class PullRequest(BaseModel):
    """A GitHub pull request object from the webhook payload."""

    number: int
    title: str
    body: str | None = None
    state: str = "open"
    user: GitHubUser
    head: PullRequestHead
    base: PullRequestBase
    diff_url: str | None = None
    html_url: str | None = None
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0


class WebhookEvent(BaseModel):
    """The top-level GitHub webhook event payload for pull_request events."""

    action: str  # opened, synchronize, reopened, closed, etc.
    number: int
    pull_request: PullRequest
    repository: GitHubRepo
    sender: GitHubUser
    installation: dict | None = None

    # Injected by our validator from the HTTP header
    delivery_id: str = Field(default="", description="X-GitHub-Delivery UUID")

    @property
    def repo_full_name(self) -> str:
        return self.repository.full_name

    @property
    def head_sha(self) -> str:
        return self.pull_request.head.sha

    @property
    def base_sha(self) -> str:
        return self.pull_request.base.sha

    @property
    def pr_number(self) -> int:
        return self.pull_request.number

    @property
    def is_reviewable(self) -> bool:
        """Only review opened, synchronize, and reopened actions."""
        return self.action in ("opened", "synchronize", "reopened")
