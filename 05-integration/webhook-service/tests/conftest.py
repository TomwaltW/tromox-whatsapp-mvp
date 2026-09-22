"""Shared pytest fixtures. No network, no real SMTP, SQLite lives in tmp_path."""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from webhook_test_helpers import NO_WAIT, TOKEN, RecordingNotifier

TRUTHY = {"1", "true", "yes"}


def fast_tests_enabled() -> bool:
    """开发时的快速测试开关：TROMOX_FAST_TESTS=1 跳过带 slow 标记的用例（这里是起 uvicorn 子进程的并发压测）。"""
    return os.environ.get("TROMOX_FAST_TESTS", "").strip().lower() in TRUTHY


def pytest_collection_modifyitems(config, items):
    if not fast_tests_enabled():
        return
    skip = pytest.mark.skip(reason="TROMOX_FAST_TESTS=1")
    for item in items:
        if item.get_closest_marker("slow") is not None:
            item.add_marker(skip)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, botmaker_webhook_token=TOKEN,
                    database_path=tmp_path / "data" / "leads.db", csv_export_path=tmp_path / "data" / "leads.csv")


@pytest.fixture
def notifier() -> RecordingNotifier:
    return RecordingNotifier()


@pytest.fixture
def app(settings: Settings, notifier: RecordingNotifier):
    return create_app(settings, notifiers=[notifier], retry_policy=NO_WAIT)


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)
