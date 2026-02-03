"""
F1 Search - Observability Module

OTEL tracing and metrics.
"""

import os
import logging

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

logger = logging.getLogger(__name__)

_initialized = False


def init_otel(service_name: str = "celeste-api"):
    """
    Initialize OpenTelemetry tracing.

    Requires OTEL_EXPORTER_OTLP_ENDPOINT env var.
    """
    global _initialized

    if _initialized:
        return

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.warning("[OTEL] OTEL_EXPORTER_OTLP_ENDPOINT not set, tracing disabled")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)

    _initialized = True
    logger.info(f"[OTEL] Tracing initialized, exporting to {endpoint}")


def get_tracer(name: str = "f1.search"):
    """Get a tracer instance."""
    return trace.get_tracer(name)


__all__ = ["init_otel", "get_tracer"]
