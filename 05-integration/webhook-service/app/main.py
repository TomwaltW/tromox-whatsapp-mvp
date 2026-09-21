"""FastAPI application factory.

Run:  uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
(The factory form keeps imports side-effect free: no database is touched at import time.)
"""
from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import BackgroundTasks, FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from . import __version__
from .config import Settings, get_settings
from .logging_setup import setup_logging
from .notify import Notifier, build_notifiers
from .pipeline import Pipeline
from .retry import RetryPolicy
from .security import TOKEN_HEADER, ip_allowed, verify_token
from .store import LeadSink, SqliteStore, build_sinks

log = logging.getLogger(__name__)
MAX_BODY_BYTES = 1_000_000


def create_app(settings: Settings | None = None, *, notifiers: list[Notifier] | None = None,
               sinks: list[LeadSink] | None = None, retry_policy: RetryPolicy | None = None,
               pipeline: Pipeline | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    if pipeline is None:
        store = SqliteStore(settings.database_path)
        pipeline = Pipeline(
            settings, store,
            sinks if sinks is not None else build_sinks(settings.storage_backend_list, store, settings.csv_export_path),
            notifiers if notifiers is not None else build_notifiers(settings),
            retry_policy=retry_policy or RetryPolicy(),
        )
    if not settings.botmaker_webhook_token:
        log.error("BOTMAKER_WEBHOOK_TOKEN is not set: /webhooks/botmaker will answer 503 until it is configured")

    app = FastAPI(title="Tromox Botmaker webhook service", version=__version__,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.pipeline = pipeline
    app.state.settings = settings

    @app.get("/health")
    def health() -> JSONResponse:
        db_ok = pipeline.store.ping()
        body = {
            "status": "ok" if db_ok else "degraded",
            "version": __version__,
            "database": "ok" if db_ok else "error",
            "webhook_token_configured": bool(settings.botmaker_webhook_token),
            "storage": ["sqlite", *[s.name for s in pipeline.sinks]],
            "notifiers": [n.name for n in pipeline.notifiers],
        }
        return JSONResponse(body, status_code=200 if db_ok else 503)

    @app.post("/webhooks/botmaker")
    async def botmaker_webhook(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
        client_ip = request.client.host if request.client else None
        if not settings.botmaker_webhook_token:
            log.error("webhook rejected: BOTMAKER_WEBHOOK_TOKEN is not configured", extra={"status_code": 503})
            return JSONResponse({"detail": "webhook token not configured"}, status_code=503)
        if not verify_token(request.headers.get(TOKEN_HEADER), settings.botmaker_webhook_token):
            log.warning("webhook rejected: bad or missing token", extra={"status_code": 401, "client_ip": client_ip})
            return JSONResponse({"detail": "invalid token"}, status_code=401)
        if not ip_allowed(client_ip, settings.allowed_ip_list):
            log.warning("webhook rejected: caller not in ALLOWED_IPS", extra={"status_code": 403, "client_ip": client_ip})
            return JSONResponse({"detail": "forbidden"}, status_code=403)

        declared = request.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "payload too large"}, status_code=413)
        raw = await request.body()
        if len(raw) > MAX_BODY_BYTES:
            return JSONResponse({"detail": "payload too large"}, status_code=413)
        try:
            payload: Any = json.loads(raw)
        except ValueError:
            return JSONResponse({"detail": "body is not valid JSON"}, status_code=400)
        if not isinstance(payload, dict):
            return JSONResponse({"detail": "body must be a JSON object"}, status_code=400)

        try:
            result = await run_in_threadpool(pipeline.handle, payload)
        except Exception as exc:  # could not even persist the raw event: let the sender retry
            log.exception("webhook could not be persisted", extra={"status_code": 500, "error_type": type(exc).__name__})
            return JSONResponse({"detail": "temporary storage error"}, status_code=500)

        if result.notification_id is not None:
            background_tasks.add_task(pipeline.deliver, result.notification_id)
        return JSONResponse(
            {"status": result.outcome, "kind": result.kind, "lead_id": result.lead_id,
             "notification_queued": result.notification_id is not None},
            background=background_tasks,
        )

    return app
