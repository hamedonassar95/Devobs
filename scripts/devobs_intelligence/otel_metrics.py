"""Optional, local-only request-duration metrics for the staging WSGI app.

This module deliberately does not inspect request metadata or create traces,
logs, or metric attributes. The only exported measurement is elapsed time.
"""
from __future__ import annotations

import logging
import os
import re
import stat
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import requests
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics import (
    AlwaysOffExemplarFilter,
    Histogram,
    MeterProvider,
)
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.metrics.view import (
    ExplicitBucketHistogramAggregation,
    View,
)
from opentelemetry.sdk.resources import Resource


_LOG = logging.getLogger(__name__)
LOCAL_OTLP_ENDPOINT = "https://127.0.0.1:4318/v1/metrics"
REQUEST_DURATION_METRIC = "devobs.api.request.duration"
_TOKEN_PATTERN = re.compile(rb"[0-9a-f]{64}\n?\Z")
_NON_LOCAL_RUNTIME_MARKERS = (
    "RENDER",
    "RENDER_SERVICE_ID",
    "K_SERVICE",
    "KUBERNETES_SERVICE_HOST",
    "WEBSITE_SITE_NAME",
    "AWS_LAMBDA_FUNCTION_NAME",
    "FLY_APP_NAME",
    "DYNO",
)
_OTEL_ENV_OVERRIDES = (
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_EXPORTER_OTLP_METRICS_HEADERS",
    "OTEL_EXPORTER_OTLP_CLIENT_KEY",
    "OTEL_EXPORTER_OTLP_CLIENT_CERTIFICATE",
    "OTEL_EXPORTER_OTLP_METRICS_CLIENT_KEY",
    "OTEL_EXPORTER_OTLP_METRICS_CLIENT_CERTIFICATE",
)


class LocalMetricsConfigurationError(ValueError):
    """Safe configuration failure; never includes a path or credential value."""


def _regular_file(settings: Mapping[str, str], key: str) -> Path:
    value = settings.get(key)
    if type(value) is not str or not value or not Path(value).is_absolute():
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    path = Path(value)
    try:
        metadata = path.lstat()
    except (OSError, ValueError):
        raise LocalMetricsConfigurationError("invalid_local_metrics_config") from None
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    return path


def _validated_local_paths(settings: Mapping[str, str]) -> tuple[Path, Path, str]:
    cert_file = _regular_file(settings, "DEVOBS_OTEL_TLS_CERT_FILE")
    token_value = settings.get("DEVOBS_OTEL_APP_TOKEN_FILE")
    if (type(token_value) is not str or not token_value
            or not Path(token_value).is_absolute()):
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    token_file = Path(token_value)
    fd = None
    try:
        fd = os.open(token_file, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
        metadata = os.fstat(fd)
        if (not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077
                or metadata.st_size not in {64, 65}):
            raise LocalMetricsConfigurationError("invalid_local_metrics_config")
        raw_token = os.read(fd, 66)
    except (OSError, ValueError):
        raise LocalMetricsConfigurationError("invalid_local_metrics_config") from None
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass
    if _TOKEN_PATTERN.fullmatch(raw_token) is None:
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    token = raw_token.rstrip(b"\n").decode("ascii")
    return cert_file, token_file, token


def _metrics_are_enabled(settings: Mapping[str, str]) -> bool:
    enabled = settings.get("DEVOBS_OTEL_METRICS_ENABLED", "false")
    local_only = settings.get("DEVOBS_OTEL_METRICS_LOCAL_ONLY", "false")
    if enabled not in {"true", "false"} or local_only not in {"true", "false"}:
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    if enabled != "true":
        return False
    if local_only != "true":
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    for marker in _NON_LOCAL_RUNTIME_MARKERS:
        if settings.get(marker):
            raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    if any(settings.get(name, "").strip().lower() not in {"", "false", "0"}
           for name in ("CI", "GITHUB_ACTIONS")):
        raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    for name in _OTEL_ENV_OVERRIDES:
        if settings.get(name):
            raise LocalMetricsConfigurationError("invalid_local_metrics_config")
    return True


@dataclass
class LocalRequestMetrics:
    """The single meter provider and WSGI wrapper used by the local API."""

    provider: MeterProvider
    histogram: Histogram

    def instrument(self, application: Callable) -> Callable:
        return instrument_wsgi_application(application, self.histogram)

    def shutdown(self) -> None:
        self.provider.shutdown()


class _TimedIterable:
    def __init__(self, iterable, histogram: Histogram, started: float):
        self._iterable = iterable
        self._iterator = None
        self._histogram = histogram
        self._started = started
        self._finished = False
        self._closed = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._finished:
            raise StopIteration
        try:
            if self._iterator is None:
                self._iterator = iter(self._iterable)
            return next(self._iterator)
        except StopIteration:
            self._finish()
            raise
        except BaseException:
            self._finish()
            raise

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            close = getattr(self._iterator, "close", None)
            if close is None:
                close = getattr(self._iterable, "close", None)
            if close is not None:
                close()
        finally:
            self._finish()

    def _finish(self) -> None:
        if self._finished:
            return
        self._finished = True
        duration_seconds = max(0.0, time.perf_counter() - self._started)
        try:
            # No attributes or request context are passed to the SDK.
            self._histogram.record(duration_seconds)
        except Exception:
            # Optional telemetry must not change application responses.
            _LOG.warning("optional_otlp_metric_record_failed")


def instrument_wsgi_application(application: Callable, histogram: Histogram) -> Callable:
    """Measure server-side WSGI response iteration without reading request data."""

    def wrapped(environ, start_response):
        started = time.perf_counter()
        try:
            iterable = application(environ, start_response)
        except BaseException:
            duration_seconds = max(0.0, time.perf_counter() - started)
            try:
                histogram.record(duration_seconds)
            except Exception:
                _LOG.warning("optional_otlp_metric_record_failed")
            raise
        return _TimedIterable(iterable, histogram, started)

    return wrapped


def create_local_metrics(settings: Mapping[str, str]) -> LocalRequestMetrics | None:
    """Create one TLS-authenticated OTLP histogram only after explicit local opt-in."""
    if not _metrics_are_enabled(settings):
        return None

    cert_file, _token_file, token = _validated_local_paths(settings)

    # Do not inherit proxy or netrc behavior from the process environment. The
    # endpoint and certificate are fixed to the local Collector contract.
    session = requests.Session()
    session.trust_env = False
    exporter = OTLPMetricExporter(
        endpoint=LOCAL_OTLP_ENDPOINT,
        certificate_file=str(cert_file),
        headers={"Authorization": f"Bearer {token}"},
        timeout=2,
        compression=None,
        max_export_batch_size=1,
        max_request_size=32768,
        session=session,
    )
    reader = PeriodicExportingMetricReader(
        exporter,
        export_interval_millis=15000,
        export_timeout_millis=3000,
    )
    view = View(
        instrument_type=Histogram,
        instrument_name=REQUEST_DURATION_METRIC,
        instrument_unit="s",
        attribute_keys=set(),
        aggregation=ExplicitBucketHistogramAggregation(
            boundaries=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 30],
            record_min_max=False,
        ),
    )
    provider = MeterProvider(
        metric_readers=[reader],
        resource=Resource({"service.name": "devobs"}),
        exemplar_filter=AlwaysOffExemplarFilter(),
        shutdown_on_exit=False,
        views=[view],
    )
    histogram = provider.get_meter("devobs.staging_api").create_histogram(
        REQUEST_DURATION_METRIC,
        unit="s",
        description="",
    )
    return LocalRequestMetrics(provider=provider, histogram=histogram)
