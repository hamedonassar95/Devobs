"""Send optional Slack and SMTP notifications for a deployment result."""

from __future__ import annotations

import json
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import getaddresses
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def deployment_message(environment: dict[str, str]) -> tuple[str, str]:
    status = environment.get("DEPLOYMENT_STATUS", "unknown")
    repository = environment.get("DEPLOYMENT_REPOSITORY", "repository unavailable")
    commit = environment.get("DEPLOYMENT_COMMIT", "unknown")
    rollback_tag = environment.get("DEPLOYMENT_ROLLBACK_TAG", "unknown")
    run_url = environment.get("DEPLOYMENT_RUN_URL", "")
    site_url = environment.get("DEPLOYMENT_SITE_URL", "")
    rollback_run_url = environment.get("DEPLOYMENT_ROLLBACK_RUN_URL", "")

    subject = f"Devobs deployment {status}: {repository}"
    lines = [
        f"Deployment status: {status}",
        f"Repository: {repository}",
        f"Candidate commit: {commit}",
        f"Automatic rollback release: {rollback_tag}",
    ]
    if site_url:
        lines.append(f"Site: {site_url}")
    if rollback_run_url:
        lines.append(f"Rollback workflow: {rollback_run_url}")
    if run_url:
        lines.append(f"GitHub Actions report: {run_url}")
    return subject, "\n".join(lines)


def send_slack(webhook_url: str, message: str) -> None:
    parsed = urlparse(webhook_url)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Slack webhook URL has an invalid port") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in {"hooks.slack.com", "hooks.slack-gov.com"}
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Slack webhook must use an official HTTPS Slack host")

    request = Request(
        webhook_url,
        data=json.dumps({"text": message}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:  # nosec B310: HTTPS host is allowlisted above.
        if response.status != 200 or response.read().strip() != b"ok":
            raise RuntimeError("Slack webhook returned an unsuccessful response")


def send_email(environment: dict[str, str], subject: str, body: str) -> None:
    host = environment.get("SMTP_HOST", "").strip()
    username = environment.get("SMTP_USERNAME", "").strip()
    password = environment.get("SMTP_PASSWORD", "")
    recipients_raw = environment.get("DEPLOYMENT_EMAIL_TO", "").strip()
    sender = environment.get("DEPLOYMENT_EMAIL_FROM", "").strip() or username
    port_raw = environment.get("SMTP_PORT", "587").strip()

    if not any((host, username, password, recipients_raw, sender)):
        raise LookupError("Email notification is not configured")
    if not all((host, username, password, recipients_raw, sender)):
        raise ValueError("SMTP settings are incomplete")

    try:
        port = int(port_raw)
    except ValueError as exc:
        raise ValueError("SMTP_PORT must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("SMTP_PORT is outside the valid range")

    recipients = [address for _, address in getaddresses([recipients_raw]) if address]
    if not recipients:
        raise ValueError("DEPLOYMENT_EMAIL_TO contains no valid email address")

    email = EmailMessage()
    email["Subject"] = subject
    email["From"] = sender
    email["To"] = ", ".join(recipients)
    email.set_content(body)

    client = None
    try:
        context = ssl.create_default_context()
        if port == 465:
            client = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
        else:
            client = smtplib.SMTP(host, port, timeout=20)
            client.ehlo()
            client.starttls(context=context)
            client.ehlo()
        client.login(username, password)
        client.send_message(email)
    finally:
        if client is not None:
            try:
                client.quit()
            except (OSError, smtplib.SMTPException):
                pass


def resolve_status(environment: dict[str, str]) -> str:
    if environment.get("DEPLOYMENT_STATUS"):
        return environment["DEPLOYMENT_STATUS"]
    validation_result = environment.get("VALIDATION_RESULT", "unknown")
    deployment_result = environment.get("DEPLOYMENT_RESULT", "unknown")
    if validation_result == "failure":
        return "validation_failed"
    if validation_result == "cancelled" or deployment_result == "cancelled":
        return "cancelled"
    if validation_result == "skipped" and deployment_result == "skipped":
        return "not_run"
    if validation_result == "success" and deployment_result == "failure":
        return "deployment_failed"
    if validation_result == "success" and deployment_result == "cancelled":
        return "cancelled"
    return "deployment_not_completed"

def notify(environment: dict[str, str]) -> list[tuple[str, str]]:
    environment = dict(environment)
    environment["DEPLOYMENT_STATUS"] = resolve_status(environment)
    if environment["DEPLOYMENT_STATUS"] == "not_run":
        return [("Slack", "not sent (deployment not confirmed)"),
                ("Email", "not sent (deployment not confirmed)")]

    subject, body = deployment_message(environment)
    message = f"{subject}\n{body}"
    outcomes: list[tuple[str, str]] = []

    webhook = environment.get("SLACK_WEBHOOK_URL", "").strip()
    if webhook:
        try:
            send_slack(webhook, message)
            outcomes.append(("Slack", "sent"))
        except (OSError, URLError, ValueError, RuntimeError) as exc:
            outcomes.append(("Slack", f"failed ({type(exc).__name__})"))
    else:
        outcomes.append(("Slack", "not configured"))

    try:
        send_email(environment, subject, body)
        outcomes.append(("Email", "sent"))
    except LookupError:
        outcomes.append(("Email", "not configured"))
    except (OSError, smtplib.SMTPException, ValueError) as exc:
        outcomes.append(("Email", f"failed ({type(exc).__name__})"))

    return outcomes


def main() -> int:
    environment = dict(os.environ)
    outcomes = notify(environment)
    for channel, outcome in outcomes:
        print(f"{channel} notification: {outcome}")

    summary_path = environment.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Deployment integration report\n\n")
            summary.write(f"- Result: {resolve_status(environment)}\n")
            summary.write(f"- Commit: {environment.get('DEPLOYMENT_COMMIT', 'unknown')}\n")
            summary.write(f"- Rollback release: {environment.get('DEPLOYMENT_ROLLBACK_TAG', 'unknown')}\n")
            if environment.get("DEPLOYMENT_RUN_URL"):
                summary.write(f"- GitHub run: {environment['DEPLOYMENT_RUN_URL']}\n")
            if environment.get("DEPLOYMENT_SITE_URL"):
                summary.write(f"- Site: {environment['DEPLOYMENT_SITE_URL']}\n")
            if environment.get("DEPLOYMENT_ROLLBACK_RUN_URL"):
                summary.write(f"- Rollback workflow: {environment['DEPLOYMENT_ROLLBACK_RUN_URL']}\n")
            summary.write("\n## Notification status\n\n")
            for channel, outcome in outcomes:
                summary.write(f"- {channel}: {outcome}\n")

    return 1 if any("failed" in outcome for _, outcome in outcomes) else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Notification delivery interrupted.", file=sys.stderr)
        raise SystemExit(130)
