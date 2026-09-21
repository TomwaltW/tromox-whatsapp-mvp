"""Shared pytest fixtures. No network, no real SMTP, SQLite lives in tmp_path."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from webhook_test_helpers import NO_WAIT, TOKEN, RecordingNotifier


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
