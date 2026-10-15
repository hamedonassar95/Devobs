#!/usr/bin/env python3
"""Create a privacy-minimal deployment record and send optional alerts."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
from datetime import datetime, timezone
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def value(name: str, fallback: str = "") -> str:
    return os.environ.get(name, fallback).strip()


def parse_time(raw: str) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def duration_seconds(start: str, end: str) -> int | None:
    started = parse_time(start)
    finished = parse_time(end)
    if started is None or finished is None:
        return None
    seconds = int((finished - started).total_seconds())
    return seconds if seconds >= 0 else None


def send_slack(text: str) -> str:
    webhook = value("SLACK_WEBHOOK_URL")
    if not webhook:
        return "not-configured"
    parsed = urlparse(webhook)
    if parsed.scheme != "https" or parsed.hostname != "hooks.slack.com":
        return "invalid-config"
    body = json.dumps({"text": text}).encode("utf-8")
    request = Request(webhook, data=body, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=15) as response:
            if 200 <= response.status < 300:
                return "sent"
            return "failed"
    except Exception as exc:  # Never log exception details that could contain a webhook URL.
        print(f"::warning::Slack alert failed ({type(exc).__name__}).")
        return "failed"


def send_email(subject: str, body: str) -> str:
    names = (
        "DEPLOY_SMTP_HOST",
        "DEPLOY_SMTP_USERNAME",
        "DEPLOY_SMTP_PASSWORD",
        "DEPLOY_EMAIL_FROM",
        "DEPLOY_EMAIL_TO",
    )
    configured = [bool(value(name)) for name in names]
    if not any(configured):
        return "not-configured"
    if not all(configured):
        print("::warning::Email alert settings are incomplete; email was not sent.")
        return "incomplete-config"

    host = value("DEPLOY_SMTP_HOST")
    username = value("DEPLOY_SMTP_USERNAME")
    password = value("DEPLOY_SMTP_PASSWORD")
    sender = value("DEPLOY_EMAIL_FROM")
    recipients = [item.strip() for item in value("DEPLOY_EMAIL_TO").split(",") if item.strip()]
    if not recipients or any("\n" in item or "\r" in item for item in [sender, *recipients]):
        print("::warning::Email alert addresses are invalid; email was not sent.")
        return "invalid-config"

    try:
        port = int(value("DEPLOY_SMTP_PORT", "587"))
        if not 1 <= port <= 65535:
            raise ValueError("port out of range")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message.set_content(body)
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls(context=context)
            server.ehlo()
            server.login(username, password)
            server.send_message(message)
        return "sent"
    except Exception as exc:  # Never log server, address, or credential details.
        print(f"::warning::Email alert failed ({type(exc).__name__}).")
        return "failed"


def main() -> int:
    upstream = value("UPSTREAM_CONCLUSION", "manual")
    health = value("HEALTH_CHECK_RESULT", "skipped")
    result = "success" if upstream in ("success", "manual") and health == "success" else "failure"
    duration = duration_seconds(value("UPSTREAM_STARTED_AT"), value("UPSTREAM_UPDATED_AT"))
    sha = value("SOURCE_SHA")
    run_id = value("WORKFLOW_RUN_ID")
    run_url = value("WORKFLOW_RUN_URL")
    site_url = value("SITE_URL")

    report = {
        "schema_version": 1,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": value("GITHUB_REPOSITORY"),
        "workflow_run_id": run_id,
        "workflow_run_url": run_url,
        "workflow_attempt": value("GITHUB_RUN_ATTEMPT"),
        "source_workflow": value("UPSTREAM_WORKFLOW"),
        "source_event": value("UPSTREAM_EVENT"),
        "source_result": upstream,
        "source_branch": value("SOURCE_BRANCH"),
        "source_sha": sha,
        "deployment_duration_seconds": duration,
        "health_check_result": health,
        "result": result,
        "site_url": site_url,
    }

    commit = sha[:12] if sha else "unknown"
    message = (
        f"Devobs deployment {result.upper()}\n"
        f"Workflow: {report['source_workflow']} ({upstream})\n"
        f"Health check: {health}\n"
        f"Commit: {commit}\n"
        f"Duration: {duration if duration is not None else 'unavailable'} seconds\n"
        f"Site: {site_url}\n"
        f"Run: {run_url}"
    )
    subject = f"[Devobs] Deployment {result.upper()} - {commit}"
    slack_state = send_slack(message)
    email_state = send_email(subject, message)
    report["notification_status"] = {"slack": slack_state, "email": email_state}

    Path("deployment-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    summary_path = value("GITHUB_STEP_SUMMARY")
    if summary_path:
        lines = [
            "## Deployment report",
            "",
            f"- Result: **{result.upper()}**",
            f"- Source workflow: {report['source_workflow']} ({upstream})",
            f"- Health check: {health}",
            f"- Source commit: {commit}",
            f"- Deployment workflow duration: {duration if duration is not None else 'unavailable'} seconds",
            f"- Site: {site_url}",
            f"- Run: {run_url}",
            f"- Notifications: Slack {slack_state}, email {email_state}",
            "",
            "Duration is the GitHub Actions run duration, not a before/after business-impact measurement.",
        ]
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")

    print(f"Deployment report recorded. Slack={slack_state}; email={email_state}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
