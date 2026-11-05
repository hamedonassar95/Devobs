#!/usr/bin/env python3
"""Send five fixed synthetic error logs to an explicitly supplied live endpoint.

This script makes exactly five requests, has no retry path, never accepts or
reads an OpenAI key, never prints bearer tokens, and writes a mode-0600 JSON
report only to a new path selected by the operator.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import getpass
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


_PATH = re.compile(
    r"/v1/tenants/[A-Za-z0-9][A-Za-z0-9_-]{0,63}/projects/"
    r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}/services/"
    r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}/diagnostics\Z"
)
_MAX_RESPONSE_BYTES = 32_768
_REQUEST_TIMEOUT_SECONDS = 120
_CASES = (
    {
        "case_id": "upstream-timeout-502",
        "error_log": (
            "2026-11-05T10:15:00Z gateway returned HTTP 502 for GET /v1/orders; "
            "upstream request exceeded the configured 3 second timeout; "
            "health checks for the application process were passing"
        ),
    },
    {
        "case_id": "postgres-pool-exhaustion",
        "error_log": (
            "2026-11-05T10:16:00Z POST /v1/checkout returned HTTP 503; "
            "database pool had 20 of 20 connections checked out for 45 seconds; "
            "no database credentials or query parameters are present"
        ),
    },
    {
        "case_id": "container-out-of-memory",
        "error_log": (
            "2026-11-05T10:17:00Z worker container restarted after exit code 137; "
            "memory reached 512 MiB; request queue grew during image processing; "
            "no customer payload is included"
        ),
    },
    {
        "case_id": "disk-full-write-failure",
        "error_log": (
            "2026-11-05T10:18:00Z background job failed with ENOSPC while writing "
            "a temporary report; available filesystem space was 0 bytes; "
            "the service remained healthy and did not retry"
        ),
    },
    {
        "case_id": "tls-handshake-certificate-expiry",
        "error_log": (
            "2026-11-05T10:19:00Z outbound HTTPS request failed during TLS handshake; "
            "peer certificate validation reported that the certificate had expired; "
            "the client rejected the connection before sending application data"
        ),
    },
)


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _validate_endpoint(endpoint: str) -> str:
    if type(endpoint) is not str or len(endpoint) > 2048:
        raise ValueError("invalid_endpoint")
    try:
        parsed = urlsplit(endpoint)
        valid = (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.hostname.lower().endswith(".onrender.com")
            and not parsed.hostname.endswith(".")
            and parsed.username is None
            and parsed.password is None
            and parsed.query == ""
            and parsed.fragment == ""
            and _PATH.fullmatch(parsed.path) is not None
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError("invalid_endpoint")
    return endpoint


def _validate_token(token: str) -> str:
    if (type(token) is not str or not token or len(token) > 16_384
            or any(ord(char) < 33 or ord(char) == 127 for char in token)):
        raise ValueError("invalid_staging_token")
    return token


def _parse_response(raw: bytes) -> dict | None:
    if len(raw) > _MAX_RESPONSE_BYTES:
        return None
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return None
    if type(value) is not dict:
        return None
    return value


def _report_output(value: dict | None, token: str) -> dict | None:
    """Keep only the public response contract and redact accidental token echoes."""
    if type(value) is not dict:
        return None
    safe = {}
    for key in ("diagnosis", "recommendation", "severity", "confidence", "model", "error"):
        item = value.get(key)
        if type(item) is str:
            safe[key] = item.replace(token, "[REDACTED]")
    latency = value.get("latency_ms")
    if type(latency) is int and latency >= 0:
        safe["latency_ms"] = latency
    return safe or None


def run_cases(endpoint: str, token: str, *, opener=None, clock=time.perf_counter,
              wall_clock=None) -> dict:
    """Run the fixed five-case suite once and return a credential-free report."""
    endpoint = _validate_endpoint(endpoint)
    token = _validate_token(token)
    http = opener if opener is not None else build_opener(_NoRedirect())
    records = []
    for case in _CASES:
        payload = json.dumps(
            {"error_log": case["error_log"], "data_redacted": True},
            separators=(",", ":"),
        ).encode("utf-8")
        request = Request(
            endpoint,
            data=payload,
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        started = clock()
        status = None
        output = None
        error = None
        try:
            with http.open(request, timeout=_REQUEST_TIMEOUT_SECONDS) as response:
                status = response.status
                raw = response.read(_MAX_RESPONSE_BYTES + 1)
            output = _report_output(_parse_response(raw), token)
            if output is None:
                error = "invalid_or_oversized_response"
        except HTTPError as response:
            status = response.code
            try:
                output = _report_output(
                    _parse_response(response.read(_MAX_RESPONSE_BYTES + 1)), token
                )
            except OSError:
                output = None
            if output is None:
                error = "http_error"
        except (URLError, TimeoutError, OSError):
            error = "network_error"
        except Exception:
            # Keep failures non-sensitive: never serialize exception text or
            # the request object, both of which may contain operator data.
            error = "request_error"
        latency_ms = max(0, int(round((clock() - started) * 1000)))
        valid_output = (
            type(output) is dict
            and all(type(output.get(key)) is str and output[key]
                    for key in ("diagnosis", "recommendation", "severity", "confidence"))
            and type(output.get("model")) is str and bool(output["model"])
            and type(output.get("latency_ms")) is int and output["latency_ms"] >= 0
        )
        records.append({
            "case_id": case["case_id"],
            "input": case["error_log"],
            "http_status": status,
            "output": output,
            "client_latency_ms": latency_ms,
            "server_latency_ms": output.get("latency_ms") if type(output) is dict else None,
            "error": error,
            "passed": status == 200 and valid_output and error is None,
        })
    timestamp = (wall_clock or (lambda: datetime.now(timezone.utc)))()
    return {
        "report_version": 1,
        "created_at_utc": timestamp.astimezone(timezone.utc).isoformat(),
        "endpoint_host": urlsplit(endpoint).hostname,
        "cases_sent": len(records),
        "results": records,
    }


def write_report(path: Path, report: dict) -> None:
    """Create a new local report with owner-only permissions; never overwrite."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", required=True, type=Path,
        help="new local JSON report path; existing files are never overwritten",
    )
    args = parser.parse_args(argv)
    endpoint = os.environ.get("DEVOBS_DIAGNOSIS_ENDPOINT", "")
    if not endpoint:
        parser.error("DEVOBS_DIAGNOSIS_ENDPOINT is required")
    try:
        token = getpass.getpass("Paste the short-lived staging access token (input hidden): ")
        report = run_cases(endpoint, token)
        write_report(args.output, report)
    except (EOFError, OSError, ValueError):
        print("ERROR: live diagnosis run could not be completed safely", file=sys.stderr)
        return 2
    for result in report["results"]:
        status = result["http_status"] if result["http_status"] is not None else "network-error"
        outcome = "PASS" if result["passed"] else "FAIL"
        print(f"{outcome} {result['case_id']} status={status} latency_ms={result['client_latency_ms']}")
    print(f"report={args.output} cases={report['cases_sent']}")
    return 0 if all(result["passed"] for result in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
