"""Repository freshness tracker to keep vector memory updated with minimal re-indexing."""

from __future__ import annotations

import structlog

logger = structlog.get_logger(__name__)


class FreshnessTracker:
    """Tracks indexed commit SHAs per repo to calculate delta files."""

    def __init__(self) -> None:
        self._repo_shas: dict[str, str] = {}

    def get_last_indexed_sha(self, repo: str) -> str | None:
        return self._repo_shas.get(repo)

    def record_indexed_sha(self, repo: str, sha: str) -> None:
        self._repo_shas[repo] = sha
        logger.info("freshness.sha_updated", repo=repo, head_sha=sha)

    def compute_changed_files(self, diff_text: str) -> list[str]:
        """Extract list of modified or added files from unified diff headers."""
        changed = []
        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                filepath = line[6:].strip()
                if filepath and filepath != "/dev/null":
                    changed.append(filepath)
        return list(set(changed))
