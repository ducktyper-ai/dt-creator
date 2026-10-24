"""Public examples are executable, deterministic, and credential-free."""

import runpy
import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLES = tuple(
    path for path in sorted(Path("examples").glob("*.py")) if path.name != "__init__.py"
)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda path: path.stem)
def test_public_example_runs(example: Path, capsys: pytest.CaptureFixture[str]) -> None:
    if example.stem == "email_marketing":
        # Keep the full proof in the gate without a hardware-dependent per-example deadline.
        runpy.run_path(str(example), run_name="__main__")
        output = capsys.readouterr().out.lower()
    else:
        completed = subprocess.run(
            [sys.executable, str(example)], check=False, capture_output=True, text=True, timeout=20
        )
        assert completed.returncode == 0, completed.stderr
        output = completed.stdout.lower()
    assert "access_token" not in output
    assert "api_key" not in output
    assert "password" not in output


def test_expected_example_set_is_present() -> None:
    assert {path.name for path in EXAMPLES} == {
        "assess_performance.py",
        "email_marketing.py",
        "complete_content_portfolio.py",
        "create_content_brief.py",
        "inspect_capabilities.py",
        "research_connector.py",
        "runtime_portfolio.py",
        "validate_and_prepare.py",
    }
