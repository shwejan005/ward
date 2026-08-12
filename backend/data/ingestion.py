"""AST-aware code chunking and indexing pipeline for WARD memory lane (§2.2, §3.5)."""

from __future__ import annotations

import ast
import re
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


class CodeChunk:
    """A single chunk of source code ready for embedding."""

    def __init__(
        self,
        repo: str,
        path: str,
        content: str,
        chunk_index: int,
        symbol: str | None = None,
        line_start: int | None = None,
        line_end: int | None = None,
    ) -> None:
        self.repo = repo
        self.path = path
        self.content = content
        self.chunk_index = chunk_index
        self.symbol = symbol
        self.line_start = line_start
        self.line_end = line_end


class CodeChunker:
    """Chunks source code using AST when available, falling back to line-window chunking."""

    def __init__(self, max_chunk_lines: int = 60, overlap_lines: int = 10) -> None:
        self.max_chunk_lines = max_chunk_lines
        self.overlap_lines = overlap_lines

    def chunk_file(self, repo: str, path: str, content: str) -> list[CodeChunk]:
        """Chunk a file based on file type and syntax structure."""
        if path.endswith(".py"):
            try:
                return self._chunk_python(repo, path, content)
            except Exception as e:
                logger.debug("chunker.ast_fallback", path=path, error=str(e))
                return self._chunk_sliding_window(repo, path, content)
        return self._chunk_sliding_window(repo, path, content)

    def _chunk_python(self, repo: str, path: str, content: str) -> list[CodeChunk]:
        """Extract top-level functions and classes via Python AST."""
        tree = ast.parse(content)
        lines = content.splitlines()
        chunks: list[CodeChunk] = []
        chunk_idx = 0

        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                start = node.lineno - 1
                end = getattr(node, "end_lineno", start + self.max_chunk_lines)
                symbol_name = node.name
                chunk_text = "\n".join(lines[start:end])
                chunks.append(
                    CodeChunk(
                        repo=repo,
                        path=path,
                        content=chunk_text,
                        chunk_index=chunk_idx,
                        symbol=symbol_name,
                        line_start=start + 1,
                        line_end=end,
                    )
                )
                chunk_idx += 1

        if not chunks:
            return self._chunk_sliding_window(repo, path, content)

        return chunks

    def _chunk_sliding_window(self, repo: str, path: str, content: str) -> list[CodeChunk]:
        """Sliding window chunking with line overlap."""
        lines = content.splitlines()
        if not lines:
            return []

        chunks: list[CodeChunk] = []
        step = max(1, self.max_chunk_lines - self.overlap_lines)
        chunk_idx = 0

        for i in range(0, len(lines), step):
            window = lines[i : i + self.max_chunk_lines]
            chunk_text = "\n".join(window)
            chunks.append(
                CodeChunk(
                    repo=repo,
                    path=path,
                    content=chunk_text,
                    chunk_index=chunk_idx,
                    symbol=None,
                    line_start=i + 1,
                    line_end=min(i + self.max_chunk_lines, len(lines)),
                )
            )
            chunk_idx += 1

        return chunks
