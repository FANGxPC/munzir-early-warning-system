"""Integration tests for PRAHARI CLI interface."""

import subprocess
import sys


def test_cli_help():
    result = subprocess.run(
        ["./bin/py", "-m", "prahari", "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "backfill" in result.stdout
    assert "run-daily" in result.stdout
    assert "train-nlp" in result.stdout
    assert "inspect" in result.stdout


def test_cli_inspect():
    result = subprocess.run(
        ["./bin/py", "-m", "prahari", "inspect"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Bronze Lakehouse Inspection" in result.stdout

