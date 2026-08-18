"""Unit tests for the WARD CLI."""

from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import patch

from backend.cli import main


def test_cli_status(capsys):
    with patch.object(sys, "argv", ["ward", "status"]):
        main()
        captured = capsys.readouterr()
        assert "WARD PR Review System" in captured.out
        assert "Modular Monolith" in captured.out


def test_cli_index_file(tmp_path, capsys):
    code_file = tmp_path / "calc.py"
    code_file.write_text("def add(a, b):\n    return a + b\n")

    with patch.object(sys, "argv", ["ward", "index", str(code_file)]):
        main()
        captured = capsys.readouterr()
        assert "Extracted" in captured.out
        assert "calc.py" in captured.out
