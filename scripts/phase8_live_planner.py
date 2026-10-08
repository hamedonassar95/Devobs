#!/usr/bin/env python3
"""Read-only Phase 8A planner fed by live, trusted GitHub evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from scripts.investigation_contract import MARKER_V2, parse as parse_contract
from scripts.recovery_planner import evaluate as evaluate_plan

BOT = "github-actions[bot]"
MONITORED_WORKFLOWS = {"CI", "Deploy Pages", "Deployment Health Check"}
RUN_MARKER = re.compile(r"<!-- incident-run-id:([0-9]+) -->")
SHA_LINE = re.compile(r"- \*\*Head SHA:\*\* `([0-9a-f]{40})`")
RECOVERY_BRANCH = re.compile(r"^recovery/incident-([1-9][0-9]*)-[a-z0-9][a-z0-9-]{0,47}$")
REQUIRED_CHECKS = [
    "validate",
    "CodeQL",
    "Analyze (actions)",
    "Analyze (python)",
    "Analyze (javascript-typescript)",
]


def _result(status: str, reason: str, *, evidence: dict | None = None,
            risk: str = "unknown", proposal: dict | None = None) -> dict:
    proposal = proposal or {}
    return {
        "eligible": status == "ELIGIBLE",
        "status": status,
        "reason": reason,
        "risk": risk,
        "final_state": "PENDING HUMAN APPROVAL",
        "repository_write_authority": False,
        "proposal": {
            "branch": proposal.get("branch"),
            "pr_title": proposal.get("pr_title"),
            "files_to_change": [],
            "files_note": "Phase 8A authorizes no paths. Phase 8B requires a separately approved allowlist.",
            "required_checks": REQUIRED_CHECKS,
        },
        "evidence": evidence or {},
    }


def _recommended_tests(workflow: str) -> list[str]:
    common = [
        "python3 -m unittest discover -s tests -v",
        "node --test tests/incident_guard.test.cjs",
        "python3 scripts/check_site.py",
    ]
    if workflow == "Deployment Health Check":
        return common + ["Run the production health check only after an approved deployment."]
    if workflow == "Deploy Pages":
        return common + ["Verify the Pages deployment from its actual workflow run."]
    return common


def evaluate_live(record: dict) -> dict:
    """Evaluate live evidence and produce a proposal only; never grants write authority."""
    if not isinstance(record, dict):
        return _result("NOT_ELIGIBLE", "input must be an object")

    errors = record.get("evidence_errors", [])
    if not isinstance(errors, list) or errors:
        return _result("NOT_ELIGIBLE", "GitHub evidence is incomplete or unreadable; failing closed",
                       evidence={"evidence_error_count": len(errors) if isinstance(errors, list) else "unknown"})

    issue = record.get("issue")
    if not isinstance(issue, dict):
        return _result("NOT_ELIGIBLE", "incident issue evidence is missing")
    body = issue.get("body")
    if not isinstance(body, str):
        return _result("NOT_ELIGIBLE", "incident body is missing")
    markers = RUN_MARKER.findall(body)
    if len(markers) != 1:
        return _result("NOT_ELIGIBLE", "exactly one numeric trusted incident run marker is required")

    incident_number = issue.get("number")
    run_id = markers[0]
    evidence = {"incident_number": incident_number, "incident_run_id": run_id}
    if type(incident_number) is not int or incident_number < 1:
        return _result("NOT_ELIGIBLE", "incident number is invalid", evidence=evidence)
    if issue.get("state") != "open":
        return _result("NOT_ELIGIBLE", "incident is not open", evidence=evidence)
    if issue.get("user") != BOT or not str(issue.get("title", "")).startswith("incident:"):
        return _result("NOT_ELIGIBLE", "incident trust gate failed", evidence=evidence)

    head_match = SHA_LINE.search(body)
    if not head_match:
        return _result("NOT_ELIGIBLE", "incident head SHA is missing or malformed", evidence=evidence)
    expected_sha = head_match.group(1)

    run = record.get("workflow_run")
    if not isinstance(run, dict):
        return _result("NOT_ELIGIBLE", "source workflow run could not be verified", evidence=evidence)
    if run.get("id") != int(run_id):
        return _result("NOT_ELIGIBLE", "source workflow run does not match the incident marker", evidence=evidence)
    if run.get("name") not in MONITORED_WORKFLOWS:
        return _result("NOT_ELIGIBLE", "source workflow is not monitored for recovery", evidence=evidence)
    if run.get("status") != "completed" or run.get("conclusion") not in {"failure", "timed_out"}:
        return _result("NOT_ELIGIBLE", "source workflow conclusion is not eligible", evidence=evidence)
    if run.get("head_branch") != "main" or run.get("head_sha") != expected_sha:
        return _result("NOT_ELIGIBLE", "source run is not bound to the incident's main-branch SHA", evidence=evidence)

    comments = record.get("comments")
    if not isinstance(comments, list):
        return _result("NOT_ELIGIBLE", "investigation evidence is unreadable", evidence=evidence)
    candidates = []
    for comment in comments:
        if not isinstance(comment, dict) or comment.get("user") != BOT:
            continue
        text = comment.get("body")
        if not isinstance(text, str):
            continue
        if ("## AI Incident Investigation" in text
                and "workflow_id: incident-investigator" in text
                and MARKER_V2 in text):
            candidates.append(text)
    evidence["trusted_investigation_count"] = len(candidates)
    if len(candidates) != 1:
        return _result("NOT_ELIGIBLE", "exactly one trusted v2 investigation is required", evidence=evidence)

    contract = parse_contract(candidates[0], expected_incident_number=incident_number, expected_run_id=run_id)
    if not contract.valid or not isinstance(contract.data, dict):
        return _result("NOT_ELIGIBLE", f"investigation contract rejected: {contract.reason}", evidence=evidence)

    recovery_prs = record.get("open_pull_requests")
    if not isinstance(recovery_prs, list):
        return _result("NOT_ELIGIBLE", "open recovery PR status is unknown", evidence=evidence)
    existing = False
    for pr in recovery_prs:
        if not isinstance(pr, dict):
            return _result("NOT_ELIGIBLE", "open PR evidence is malformed", evidence=evidence)
        branch = pr.get("head_ref", "")
        pr_body = pr.get("body", "") or ""
        branch_match = RECOVERY_BRANCH.fullmatch(branch) if isinstance(branch, str) else None
        marker = f"<!-- devobs-recovery-incident:{incident_number} -->"
        if (branch_match and branch_match.group(1) == str(incident_number)) or marker in pr_body:
            existing = True
            break

    data = contract.data
    planner_input = {
        "trusted_incident": True,
        "incident_open": True,
        "conclusion": run["conclusion"],
        "investigation_count": len(candidates),
        "decision": data["decision"],
        "confidence": data["confidence"],
        "reversible": data["reversible"],
        "repository_scoped": data["repository_scoped"],
        "existing_recovery_pr": existing,
        "proposed_change": data["proposed_change"],
    }
    plan = evaluate_plan(planner_input)
    jobs = run.get("jobs", [])
    failed_jobs = [
        job.get("name", "unknown")
        for job in jobs
        if isinstance(job, dict) and job.get("conclusion") not in {"success", "skipped", None}
    ]
    evidence.update({
        "source_workflow": run["name"],
        "source_conclusion": run["conclusion"],
        "source_sha": run["head_sha"],
        "failed_jobs": failed_jobs,
        "trusted_investigation_count": 1,
        "decision": data["decision"],
        "confidence": data["confidence"],
        "existing_recovery_pr": existing,
    })
    if not plan.eligible:
        return _result(plan.status, plan.reason, evidence=evidence, risk=plan.risk)

    slug = re.sub(r"[^a-z0-9]+", "-", data["proposed_change"].lower()).strip("-")[:48].strip("-")
    slug = slug or "review"
    proposal = {
        "branch": f"recovery/incident-{incident_number}-{slug}",
        "pr_title": f"[RECOVERY] Incident #{incident_number}: {data['proposed_change'][:100]}",
        "recommended_tests": _recommended_tests(run["name"]),
    }
    evidence["proposed_change"] = data["proposed_change"]
    return _result(plan.status, plan.reason, evidence=evidence, risk=plan.risk, proposal=proposal)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    args = parser.parse_args()
    try:
        record = json.loads(args.record.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print(json.dumps(_result("NOT_ELIGIBLE", "invalid evidence input"), sort_keys=True))
        return 0
    print(json.dumps(evaluate_live(record), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
