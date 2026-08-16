"""Golden PR evaluation dataset for benchmark testing & regression gating."""

from __future__ import annotations

from typing import Any
from backend.models.enums import AgentType, FindingCategory, Severity


GOLDEN_PRS: list[dict[str, Any]] = [
    {
        "id": "golden-pr-001",
        "title": "Add user authentication and lookup endpoint",
        "repo": "acme/auth-service",
        "diff": """
--- a/auth.py
+++ b/auth.py
@@ -10,6 +10,12 @@ def get_user_profile(db_conn, user_id: str):
+    # Raw query with string interpolation
+    query = f"SELECT * FROM users WHERE id = '{user_id}' AND is_active = 1"
+    return db_conn.execute(query).fetchone()
+
+def reset_password(email: str):
+    # Missing rate limit and token expiration validation
+    pass
""",
        "expected_findings": [
            {
                "agent_type": AgentType.SECURITY,
                "severity": Severity.CRITICAL,
                "category": FindingCategory.INJECTION,
                "file_path": "auth.py",
                "keywords": ["sql", "injection", "interpolation", "parameterized"],
            },
            {
                "agent_type": AgentType.TESTS,
                "severity": Severity.HIGH,
                "category": FindingCategory.MISSING_TEST,
                "keywords": ["test", "untested"],
            },
        ],
    },
    {
        "id": "golden-pr-002",
        "title": "Add billing calculation helper without null checks",
        "repo": "acme/billing-service",
        "diff": """
--- a/billing.py
+++ b/billing.py
@@ -5,4 +5,8 @@
+def compute_discount(customer, amount: float) -> float:
+    tier = customer.tier.name.lower()
+    if tier == "vip":
+        return amount * 0.20
+    return 0.0
""",
        "expected_findings": [
            {
                "agent_type": AgentType.QUALITY,
                "severity": Severity.HIGH,
                "category": FindingCategory.NULL_SAFETY,
                "file_path": "billing.py",
                "keywords": ["null", "none", "attributeerror", "tier"],
            },
            {
                "agent_type": AgentType.DOCS,
                "severity": Severity.LOW,
                "category": FindingCategory.MISSING_DOCSTRING,
                "file_path": "billing.py",
                "keywords": ["docstring", "document"],
            },
        ],
    },
]
