"""Command-line interface for WARD developers and CI environments."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from backend.orchestrator.langgraph_engine import LangGraphEngine
from backend.data.ingestion import CodeChunker


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ward",
        description="WARD: Autonomous Multi-Agent PR Review System",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ── Review Command ──
    review_parser = subparsers.add_parser("review", help="Review a unified diff file")
    review_parser.add_argument("diff_file", type=Path, help="Path to the unified diff file")
    review_parser.add_argument("--repo", default="local/repo", help="Repository name")
    review_parser.add_argument("--pr", type=int, default=1, help="Pull request number")

    # ── Index Command ──
    index_parser = subparsers.add_parser("index", help="Chunk and inspect code for vector memory")
    index_parser.add_argument("file_path", type=Path, help="Source code file to chunk")
    index_parser.add_argument("--repo", default="local/repo", help="Repository name")

    # ── Status Command ──
    subparsers.add_parser("status", help="Check system status and configuration")

    args = parser.parse_args()

    if args.command == "status":
        print("WARD PR Review System v0.1.0")
        print("Status: Ready")
        print("Architecture: Modular Monolith (ADR-002)")
        print("Specialists: Security, Quality, Tests, Docs")
        return

    if args.command == "review":
        if not args.diff_file.exists():
            print(f"Error: Diff file not found: {args.diff_file}", file=sys.stderr)
            sys.exit(1)

        diff_content = args.diff_file.read_text(encoding="utf-8")
        engine = LangGraphEngine()

        print(f"Running multi-agent review on {args.repo} PR #{args.pr}...")
        review = asyncio.run(
            engine.start_review(
                repo=args.repo,
                pr_number=args.pr,
                head_sha="local-sha",
                diff=diff_content,
            )
        )

        print("\n=== Review Summary ===")
        print(f"Outcome: {review.outcome.upper() if review.outcome else 'N/A'}")
        print(f"Confidence: {round(review.overall_confidence * 100)}%")
        print(f"Active Findings: {len(review.active_findings)}")
        print(f"Estimated Cost: ${review.total_cost_usd:.4f}")

        for f in review.active_findings:
            print(f"\n[{f.severity.upper()}] {f.title} ({f.agent_type})")
            print(f"  Location: {f.file_path}:{f.line_start or 1}")
            print(f"  Description: {f.description}")
            if f.suggestion:
                print(f"  Suggestion:\n    {f.suggestion}")
        return

    if args.command == "index":
        if not args.file_path.exists():
            print(f"Error: File not found: {args.file_path}", file=sys.stderr)
            sys.exit(1)

        content = args.file_path.read_text(encoding="utf-8")
        chunker = CodeChunker()
        chunks = chunker.chunk_file(args.repo, str(args.file_path), content)

        print(f"Extracted {len(chunks)} code chunk(s) from {args.file_path}:")
        for c in chunks:
            print(f"  - Chunk {c.chunk_index}: symbol='{c.symbol or 'none'}', lines={c.line_start}-{c.line_end}")


if __name__ == "__main__":
    main()
