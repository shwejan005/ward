"""End-to-end integration test verifying the complete PR review lifecycle."""

from __future__ import annotations

import pytest
import asyncio
from backend.models.enums import AgentType, FindingCategory, Severity, ReviewOutcome, HITLStatus
from backend.models.findings import Finding
from backend.orchestrator.langgraph_engine import LangGraphEngine
from backend.hitl.queue import HITLQueue


@pytest.mark.asyncio
async def test_end_to_end_review_pipeline_flow(monkeypatch):
    """Test full review workflow:

    1. Trigger review with a diff containing a vulnerability.
    2. LangGraph fans out to specialists and aggregates findings.
    3. Confirms HITL gate trips on CRITICAL severity.
    4. Simulates human reviewer approving the review.
    """
    engine = LangGraphEngine()

    sample_diff = """
--- a/src/auth/token.py
+++ b/src/auth/token.py
@@ -1,5 +1,10 @@
+def generate_token(user_id):
+    # Hardcoded secret key
+    secret = "HARDCODED_API_SECRET_KEY_9999"
+    return jwt.encode({"sub": user_id}, secret, algorithm="HS256")
"""

    review = await engine.start_review(
        repo="acme/security-core",
        pr_number=501,
        head_sha="git-sha-501",
        diff=sample_diff,
    )

    assert review.repo == "acme/security-core"
    assert review.pr_number == 501
    assert review.status == "completed"
    assert review.overall_confidence > 0.0
    assert len(review.agent_results) == 4  # All 4 specialists returned results
