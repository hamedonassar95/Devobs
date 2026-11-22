"""Deterministic offline projection of existing milestone and task authorities."""
from __future__ import annotations

import html
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _shared():
    from scripts import agentdust_readonly_adapter as reader
    from scripts import check_two_agent_tasks as contract
    from scripts import milestone_ledger as ledger
    from scripts.ci_failure_intelligence import SECRET_PATTERNS
    from tools import agent_output_guard as guard
    from tools import agent_task_status_report as tasks
    return SimpleNamespace(reader=reader, contract=contract, ledger=ledger,
                           patterns=SECRET_PATTERNS, guard=guard, tasks=tasks)


def _failure(code):
    return {"schema_version": 1, "report_type": "development_progress", "offline": True,
            "advisory": True, "status": "FAIL", "input_validation": "FAIL",
            "live_evidence_status": "UNVERIFIED", "summary": None,
            "completed_milestones": [], "pending_milestones": [], "blocked_milestones": [],
            "agent_tasks": [], "available_verification": [], "outstanding_owner_approvals": [],
            "next_recommended_task": {"kind": "REPAIR_INPUT_EVIDENCE", "id": None,
                                      "evidence_status": "BLOCKED", "advisory": True},
            "errors": [code]}


def _clean(value, shared):
    if isinstance(value, str):
        if shared.guard._credential_like(value, shared.patterns):
            return "[REDACTED]"
        return shared.tasks.sanitize_display(value, limit=1000)
    if isinstance(value, dict):
        return {key: _clean(item, shared) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean(item, shared) for item in value]
    return value


def _recorded_match(task, repository, by_pr):
    if task["repository"] != repository or not isinstance(task["pr_reference"], str):
        return False
    reference = task["pr_reference"]
    prefix = f"https://github.com/{repository}/pull/"
    number = reference[1:] if reference.startswith("#") else (
        reference[len(prefix):] if reference.startswith(prefix) else "")
    if not 1 <= len(number) <= 20 or not number.isascii() or not number.isdecimal():
        return False
    record = by_pr.get(number)
    return bool(record and task["source_sha"] in (record["pr_head_sha"], record["merge_sha"]))


def _recommend(rows, repository, blocked, pending):
    local = [row for row in rows if row["repository"] == repository and not row["blocked"]]
    for state, kind in (("in_progress", "CONTINUE_TASK"), ("evidence_ready", "REVIEW_LOCAL_EVIDENCE"),
                        ("complete", "VERIFY_MERGE_EVIDENCE"), ("planned", "PLAN_TASK")):
        candidates = [row for row in local if row["status"] == state and
                      (state != "complete" or row["merge_reference_state"] == "UNVERIFIED")]
        if candidates:
            return {"kind": kind, "id": candidates[0]["task_id"],
                    "evidence_status": "UNVERIFIED", "advisory": True}
    gates = blocked or pending
    return {"kind": "REVIEW_BLOCKED_GATE" if blocked else "REVIEW_OPEN_GATE",
            "id": gates[0]["id"] if gates else None,
            "evidence_status": "BLOCKED" if blocked else "UNVERIFIED", "advisory": True}


def build_progress_report(ledger, manifest):
    """Project validated records without changing their state or accepting claims."""
    try:
        shared = _shared()
        try:
            summary = shared.ledger.validate(ledger)
        except shared.ledger.InvalidLedger:
            return _failure("INVALID_LEDGER")
        view = shared.tasks.build_report(manifest, source_label="approved local task manifest")
        if view["effective_decision"] == "FAIL":
            return _failure("INVALID_TASK_MANIFEST")
        if view["effective_decision"] not in {"PASS", "BLOCKED"}:
            return _failure("TASK_REPORT_UNAVAILABLE")
        repository = ledger["repository"]
        if repository not in manifest["repositories"]:
            return _failure("REPOSITORY_NOT_IN_MANIFEST")
        by_id = {task["id"]: task for task in manifest["tasks"]}
        by_pr = {str(record["pr_number"]): record for record in ledger["milestones"]}
        completed, evidence, rows = [], [], []
        for record in ledger["milestones"]:
            completed.append({key: record[key] for key in ("id", "title", "pr_number", "merge_sha")})
            completed[-1].update(recorded_state="merged", evidence_status="UNVERIFIED")
            evidence.append({"id": record["id"], "kind": "LEDGER_CI_REFERENCE",
                             "repository": repository,
                             "source_sha": record["pr_head_sha"], "merge_sha": record["merge_sha"],
                             "ci_run_id": record["ci_run_id"], "evidence_status": "UNVERIFIED"})
        for row in sorted(view["tasks"], key=lambda item: item["task_id"]):
            original = by_id[row["task_id"]]
            item = {key: row[key] for key in ("task_id", "assigned_worker", "repository", "branch",
                                             "status", "blocked", "evidence_state", "evidence_note")}
            for key in ("dependencies", "blocked_reasons", "unresolved_dependencies"):
                item[key] = sorted(set(row[key]))
            item.update(pr_reference=original["pr_reference"], source_sha=original["source_sha"],
                        merge_reference_state="RECORDED_MATCH" if
                        _recorded_match(original, repository, by_pr) else "UNVERIFIED")
            rows.append(item)
            verification = original["verification"]
            evidence.append({"id": row["task_id"], "kind": "TASK_VERIFICATION_STATE",
                             "repository": original["repository"],
                             "source_sha": original["source_sha"],
                             "recorded_result": verification["result"],
                             "commands_count": len(verification["commands"]),
                             "evidence_present": bool(verification["evidence"].strip()),
                             "evidence_status": "UNVERIFIED"})
        gates = [{"id": gate["id"], "status": gate["status"], "source": gate["source"],
                  "recorded_reason": gate["reason"],
                  "evidence_status": "BLOCKED" if gate["status"] == "BLOCKED" else "UNVERIFIED"}
                 for gate in sorted(ledger["gates"], key=lambda item: item["id"])]
        blocked = [gate for gate in gates if gate["status"] == "BLOCKED"]
        pending = [gate for gate in gates if gate["status"] == "OPEN"]
        approvals = [{"action": action, "status": value, "evidence_status": "BLOCKED"}
                     for action, value in sorted(manifest["approval"].items())]
        status = "BLOCKED" if blocked or view["effective_decision"] == "BLOCKED" else "UNVERIFIED"
        report = {"schema_version": 1, "report_type": "development_progress", "repository": repository,
                  "offline": True, "advisory": True, "input_validation": "VERIFIED", "status": status,
                  "live_evidence_status": "UNVERIFIED", "errors": [],
                  "summary": {"recorded_completed_milestones": summary["merged_milestones"],
                              "latest_recorded_pr": summary["latest_pr"], "pending_milestones": len(pending),
                              "blocked_milestones": len(blocked), "agent_tasks": len(rows),
                              "completed_task_claims": sum(row["status"] == "complete" for row in rows),
                              "blocked_tasks": sum(row["blocked"] for row in rows)},
                  "completed_milestones": completed, "pending_milestones": pending,
                  "blocked_milestones": blocked, "agent_tasks": rows,
                  "available_verification": sorted(evidence, key=lambda item: (item["kind"], item["id"])),
                  "outstanding_owner_approvals": approvals,
                  "next_recommended_task": _recommend(rows, repository, blocked, pending)}
        return _clean(report, shared)
    except Exception:
        return _failure("INTERNAL_ERROR")


def load_report(milestones_path, tasks_path):
    """Read only the two explicit JSON files; no discovery or command execution."""
    try:
        shared = _shared()
        documents = []
        for supplied, limit in ((milestones_path, shared.reader.MAX_REPORT_BYTES),
                                (tasks_path, shared.contract.MAX_MANIFEST_BYTES)):
            path = Path(supplied)
            if path.suffix.lower() != ".json":
                return _failure("UNSUPPORTED_INPUT_TYPE")
            descriptor = shared.reader._open_explicit_regular_file(path)
            try:
                if os.fstat(descriptor).st_size > limit:
                    return _failure("INPUT_TOO_LARGE")
                raw = shared.reader._read_bounded_report(descriptor)
            finally:
                shared.reader._quiet_close(descriptor)
            if len(raw) > limit:
                return _failure("INPUT_TOO_LARGE")
            normalized = shared.guard._strict_json(raw.decode("utf-8"), shared.reader)
            documents.append(json.loads(normalized))
        return build_progress_report(*documents)
    except Exception:
        return _failure("INPUT_UNAVAILABLE_OR_INVALID")


def _markdown(value):
    if isinstance(value, list):
        value = ", ".join(str(item) for item in value) or "none"
    text = html.escape(str(value), quote=True).replace("\n", " ").replace("\r", " ")
    return "".join("\\" + char if char in "\\`*_{}[]()#!|~" else char for char in text)


def render_markdown(report):
    lines = ["# Development progress", "", "Offline advisory report; no approval or live GitHub verification.",
             "", "Status: " + report["status"], "Input structure: " + report["input_validation"],
             "Live evidence: UNVERIFIED", "Repository: " + _markdown(report.get("repository", "unavailable")), ""]

    def table(title, items, columns):
        lines.extend(["## " + title, "", "| " + " | ".join(columns) + " |",
                      "| " + " | ".join("---" for _ in columns) + " |"])
        for item in items:
            lines.append("| " + " | ".join(_markdown(item.get(column, "none")) for column in columns) + " |")
        if not items:
            lines.append("| " + " | ".join("none" for _ in columns) + " |")
        lines.append("")

    table("Summary", [{"metric": key, "value": value} for key, value in sorted((report["summary"] or {}).items())],
          ("metric", "value"))
    table("Completed milestones (recorded only)", report["completed_milestones"],
          ("id", "pr_number", "title", "evidence_status"))
    for key, title in (("pending_milestones", "Pending milestones (OPEN gates)"),
                       ("blocked_milestones", "Blocked milestones")):
        table(title, report[key], ("id", "status", "recorded_reason", "evidence_status"))
    table("Agent task claims", report["agent_tasks"],
          ("task_id", "repository", "assigned_worker", "status", "blocked", "blocked_reasons",
           "unresolved_dependencies", "evidence_state", "merge_reference_state"))
    table("Available verification references", report["available_verification"],
          ("id", "repository", "kind", "ci_run_id", "commands_count", "evidence_present", "evidence_status"))
    table("Outstanding owner approvals", report["outstanding_owner_approvals"],
          ("action", "status", "evidence_status"))
    table("Next recommended task (advisory)", [report["next_recommended_task"]],
          ("kind", "id", "evidence_status", "advisory"))
    if report["errors"]:
        lines.extend(["Errors: " + ", ".join(report["errors"]), ""])
    return "\n".join(lines)


def main(argv=None):
    output_format = "json"
    try:
        shared = _shared()
        parser = shared.guard.QuietParser(prog="development_progress_report.py", description=__doc__, allow_abbrev=False)
        parser.add_argument("--milestones", required=True, help="Explicit approved milestone-ledger JSON")
        parser.add_argument("--tasks", required=True, help="Explicit approved task-manifest JSON")
        parser.add_argument("--format", choices=("json", "markdown"), default="json")
        arguments = parser.parse_args(argv)
        output_format = arguments.format
        report = load_report(arguments.milestones, arguments.tasks)
    except Exception:
        report = _failure("INVALID_INVOCATION_OR_DEPENDENCY")
    print(render_markdown(report) if output_format == "markdown" else
          json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":")))
    return 3 if report["status"] == "FAIL" else 1 if report["status"] == "BLOCKED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
