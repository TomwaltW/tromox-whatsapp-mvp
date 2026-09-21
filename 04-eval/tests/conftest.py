"""Shared fixtures for the eval tool tests. No test here talks to a real API."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

EVAL_ROOT = Path(__file__).resolve().parents[1]
if str(EVAL_ROOT) not in sys.path:  # allow running pytest from the repo root as well
    sys.path.insert(0, str(EVAL_ROOT))

@pytest.fixture()
def eval_root() -> Path:
    return EVAL_ROOT


@pytest.fixture(autouse=True)
def _no_real_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make sure a developer's real keys can never leak into a test request."""
    for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN",
                 "ANTHROPIC_BASE_URL", "ANTHROPIC_PROFILE", "EVAL_PRICE_INPUT_PER_1M", "EVAL_PRICE_OUTPUT_PER_1M"):
        monkeypatch.delenv(name, raising=False)
