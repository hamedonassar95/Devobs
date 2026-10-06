"""Deterministic incident triage for the Devobs GitHub Actions pipeline.

The classifier prepares evidence and a recommendation. It never executes a
rollback or modifies production state.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

UNUSABLE_CONCLUSIONS = {"cancelled", "neutral", "skipped", "stale"}
FAILURE_CONCLUSIONS = {"failure", "timed_out", "action_required", "startup_failure"}


def _failed_jobs(jobs: dict[str, Any]) -> list[str]:
    names = []
    for job in jobs.get("jobs", []):
        conclusion = (job.get("conclusion") or "").lower()
        if conclusion and conclusion not in {"success", "skipped", "neutral"}:
            names.append(job.get("name") or f"job-{job.get('id', 'unknown')}")
    return names


def build_incident(
    *,
    workflow: str,
    conclusion: str,
    run_id: str,
    sha: str,
    run_url: str,
    repository: str,
    jobs: dict[str, Any],
) -> dict[str, Any]:
    """Return a machine-readable triage record for one completed workflow run."""
    normalized = conclusion.lower().strip()
    category = "unknown"
    severity = "medium"
    action = "MANUAL_REVIEW"
    rationale = "The workflow state is not safe for an automated recovery decision."

    if normalized == "success":
        category = "healthy"
        severity = "info"
        action = "NONE"
        rationale = "The monitored workflow completed successfully."
    elif normalized in UNUSABLE_CONCLUSIONS:
        rationale = "The run did not produce a trustworthy failure signal; review it manually."
    elif workflow == "CI" and normalized in FAILURE_CONCLUSIONS:
        category = "validation"
        severity = "high"
        action = "FIX_FORWARD"
        rationale = (
            "CI failed before production deployment, so fixing the validation or code failure "
            "is safer than reverting production."
        )
    elif workflow == "Deploy Pages" and normalized in FAILURE_CONCLUSIONS:
        category = "deployment"
        severity = "high"
        action = "MANUAL_REVIEW"
        rationale = (
            "Deployment failed after CI; determine whether the cause is GitHub Pages, workflow "
            "configuration, or the release before choosing fix-forward or rollback."
        )
    elif workflow == "Deployment Health Check" and normalized in FAILURE_CONCLUSIONS:
        category = "production-verification"
        severity = "critical"
        action = "ROLLBACK_CANDIDATE"
        rationale = (
            "Production verification failed after deployment. The current release is a rollback "
            "candidate, but rollback still requires human approval and the protected PR flow."
        )

    failed_jobs = _failed_jobs(jobs)
    return {
        "schema_version": 1,
        "repository": repository,
        "workflow": workflow,
        "conclusion": normalized,
        "run_id": str(run_id),
        "run_url": run_url,
        "head_sha": sha,
        "category": category,
        "severity": severity,
        "recommended_action": action,
        "rationale": rationale,
        "failed_jobs": failed_jobs,
        "automation_policy": {
            "allow_automatic_rollback": False,
            "allow_direct_push_to_main": False,
            "require_protected_pr_flow": True,
        },
        "ai_handoff": {
            "status": "ready",
            "allowed": [
                "summarize evidence",
                "suggest likely root causes",
                "propose diagnostic steps",
                "recommend fix-forward or rollback for human approval",
            ],
            "prohibited": [
                "merge pull requests",
                "push directly to main",
                "disable protections",
                "execute rollback without approval",
            ],
        },
    }


def render_markdown(incident: dict[str, Any]) -> str:
    failed = incident.get("failed_jobs") or []
    failed_text = "\n".join(f"- `{name}`" for name in failed) or "- None reported"
    rollback = "enabled" if incident["automation_policy"]["allow_automatic_rollback"] else "disabled"
    return f"""# Automated Incident Triage

- **Repository:** `{incident['repository']}`
- **Workflow:** `{incident['workflow']}`
- **Conclusion:** `{incident['conclusion']}`
- **Severity:** `{incident['severity']}`
- **Category:** `{incident['category']}`
- **Run ID:** `{incident['run_id']}`
- **Head SHA:** `{incident['head_sha']}`
- **Run:** {incident['run_url']}

## Failed jobs

{failed_text}

## Recommended action

**{incident['recommended_action']}**

{incident['rationale']}

## Guardrails

- Automatic rollback: {rollback}
- Direct push to `main`: disabled
- Protected PR flow: required

## AI handoff

The evidence bundle may be given to an approved AI agent for diagnosis and recommendations only. The agent must not merge, push to `main`, disable protections, or execute a rollback without explicit approval.

<!-- incident-run-id:{incident['run_id']} -->
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify a failed GitHub Actions workflow run")
    parser.add_argument("--workflow", required=True)
    parser.add_argument("--conclusion", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--sha", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--jobs-json", required=True)
    parser.add_argument("--out-json", default="incident.json")
    parser.add_argument("--out-markdown", default="incident.md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    jobs = json.loads(Path(args.jobs_json).read_text(encoding="utf-8"))
    incident = build_incident(
        workflow=args.workflow,
        conclusion=args.conclusion,
        run_id=args.run_id,
        sha=args.sha,
        run_url=args.run_url,
        repository=args.repository,
        jobs=jobs,
    )
    Path(args.out_json).write_text(json.dumps(incident, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    Path(args.out_markdown).write_text(render_markdown(incident), encoding="utf-8")
    print(f"{incident['severity']} {incident['category']} -> {incident['recommended_action']}")


if __name__ == "__main__":
    main()
