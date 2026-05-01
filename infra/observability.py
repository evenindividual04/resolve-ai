from __future__ import annotations

import json
import logging
import os
import time
from contextvars import ContextVar
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

REQUEST_COUNT = Counter("api_requests_total", "Total API requests", ["path", "method", "status"])
REQUEST_LATENCY = Histogram("api_request_latency_seconds", "API request latency", ["path", "method"])
WORKFLOW_EVENTS = Counter("workflow_events_processed_total", "Workflow events processed", ["status"])


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "ts": int(time.time()),
            "trace_id": trace_id_ctx.get(),
        }
        return json.dumps(payload)


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def maybe_init_otel() -> None:
    if os.getenv("ENABLE_OTEL", "false").lower() != "true":
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        provider = TracerProvider(resource=Resource.create({"service.name": "durable-negotiation-agent"}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)
    except Exception:
        logging.getLogger(__name__).warning("otel_init_failed")


async def tracing_middleware(request: Request, call_next: Callable) -> Response:
    trace_id = request.headers.get("x-trace-id", str(uuid4()))
    token = trace_id_ctx.set(trace_id)
    start = time.perf_counter()
    try:
        response = await call_next(request)
    finally:
        trace_id_ctx.reset(token)
    duration = time.perf_counter() - start
    path = request.url.path
    REQUEST_LATENCY.labels(path=path, method=request.method).observe(duration)
    REQUEST_COUNT.labels(path=path, method=request.method, status=str(response.status_code)).inc()
    response.headers["x-trace-id"] = trace_id
    return response


def metrics_response() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
