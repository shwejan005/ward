"""Unit tests for AST and window-based code chunking."""

from __future__ import annotations

from backend.data.freshness import FreshnessTracker
from backend.data.ingestion import CodeChunker


def test_chunk_python_file():
    code = """
def calculate_metrics(data):
    total = sum(data)
    return total / len(data) if data else 0

class DataProcessor:
    def process(self, item):
        return item.strip()
"""
    chunker = CodeChunker(max_chunk_lines=20)
    chunks = chunker.chunk_file("org/repo", "src/metrics.py", code)
    assert len(chunks) >= 1
    assert any("calculate_metrics" in (c.symbol or "") or "DataProcessor" in (c.symbol or "") for c in chunks)


def test_chunk_generic_file():
    text = "\n".join([f"line {i}" for i in range(100)])
    chunker = CodeChunker(max_chunk_lines=30, overlap_lines=5)
    chunks = chunker.chunk_file("org/repo", "docs/guide.md", text)
    assert len(chunks) >= 3


def test_freshness_tracker():
    tracker = FreshnessTracker()
    assert tracker.get_last_indexed_sha("org/repo") is None
    tracker.record_indexed_sha("org/repo", "commit-abc")
    assert tracker.get_last_indexed_sha("org/repo") == "commit-abc"

    diff = """
--- a/auth.py
+++ b/auth.py
@@ -1 +1 @@
-old
+new
--- a/test.py
+++ b/test.py
@@ -1 +1 @@
"""
    changed = tracker.compute_changed_files(diff)
    assert "auth.py" in changed
    assert "test.py" in changed
