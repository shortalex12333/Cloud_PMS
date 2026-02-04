"""
F1 Search - Observability Module

OTEL tracing and metrics.
Gracefully degrades if opentelemetry is not installed.
"""

import os
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_initialized = False
_otel_available = False

# Try to import opentelemetry, gracefully degrade if not available
try:
    from opentelemetry import trace
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _otel_available = True
except ImportError:
    logger.info("[OTEL] opentelemetry not installed, tracing disabled")
    trace = None


class NoOpSpan:
    """No-op span for when OTEL is disabled."""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def set_attribute(self, key, value):
        pass
    def add_event(self, name, attributes=None):
        pass
    def set_status(self, status):
        pass
    def record_exception(self, exception):
        pass


class NoOpTracer:
    """No-op tracer for when OTEL is disabled."""
    @contextmanager
    def start_as_current_span(self, name, **kwargs):
        yield NoOpSpan()

    def start_span(self, name, **kwargs):
        return NoOpSpan()


_noop_tracer = NoOpTracer()


def init_otel(service_name: str = "celeste-api"):
    """
    Initialize OpenTelemetry tracing.

    Requires OTEL_EXPORTER_OTLP_ENDPOINT env var.
    """
    global _initialized

    if _initialized:
        return

    if not _otel_available:
        logger.info("[OTEL] opentelemetry not installed, skipping init")
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
    """Get a tracer instance. Returns no-op tracer if OTEL not available."""
    if _otel_available and trace:
        return trace.get_tracer(name)
    return _noop_tracer


__all__ = ["init_otel", "get_tracer"]
