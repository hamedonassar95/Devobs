"""Offline validator for a two-worker Devobs task manifest.

CODEX and OPENCODE are separate worker roles. This tool reads one local JSON
manifest, validates the contract, detects concurrent file or branch ownership,
blocks tasks with unresolved dependencies, and requires recorded evidence before
a task may be marked complete.

It never starts an agent, calls a network service, changes Git state, or grants
merge, deployment, billing or production authority. Those remain human gates.
"""
import argparse
import json
import pathlib
import re
import sys

SCHEMA_VERSION = 1
WORKER_ROLES = ("CODEX", "OPENCODE")
RESTRICTED_ACTIONS = ("merge", "deploy", "billing", "production")
APPROVAL_VALUE = "pending_human"
APPROVED_TASK_ACTIONS = ("code_change", "review", "test", "documentation")
STATUSES = ("planned", "in_progress", "evidence_ready", "complete", "blocked")
NO_STATUS = "none"
ALLOWED_TRANSITIONS = {
    NO_STATUS: ("planned",),
    "planned": ("planned", "in_progress", "blocked"),
    "in_progress": ("in_progress", "evidence_ready", "blocked"),
    "evidence_ready": ("evidence_ready", "complete", "in_progress", "blocked"),
    "blocked": ("blocked", "planned", "in_progress"),
    "complete": ("complete",),
}
OWNED_STATUSES = ("planned", "in_progress", "evidence_ready")
RUNNING_STATUSES = ("in_progress", "evidence_ready")
VERIFICATION_RESULTS = ("PENDING", "PASS", "FAIL")
MAX_MANIFEST_BYTES = 512 * 1024
TOP_LEVEL_KEYS = frozenset(
    {"schema_version", "repositories", "agents", "approval", "tasks"}
)
TASK_KEYS = frozenset(
    {
        "id", "repository", "assigned_agent", "branch", "affected_files",
        "dependencies", "status", "previous_status", "source_sha",
        "verification", "pr_reference", "requested_actions",
    }
)
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
ID_RE = re.compile(r"^[A-Z][A-Z0-9_-]{2,63}$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
BRANCH_RE = re.compile(r"^(feature|fix|docs|chore)/[A-Za-z0-9._/-]+$")
PR_RE = re.compile(
    r"^(?:#\d+|https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/pull/\d+)$"
)


def _text(value, limit=200):
    return isinstance(value, str) and 0 < len(value) <= limit


def _normal_path(value):
    """Return a safe repository-relative path, or None when it is not one."""
    if not _text(value, 500):
        return None
    candidate = value.replace("\\", "/")
    while candidate.startswith("./"):
        candidate = candidate[2:]
    if candidate.startswith("/") or re.match(r"^[A-Za-z]:", candidate):
        return None
    parts = candidate.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    return "/".join(parts)


def _depends_on(task_id, target, by_id):
    """True when task_id transitively declares target as a dependency."""
    seen = set()
    pending = list(by_id[task_id]["dependencies"])
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in seen or current not in by_id:
            continue
        seen.add(current)
        pending.extend(by_id[current]["dependencies"])
    return False


def _unresolved_dependencies(task_id, by_id):
    """Return every ancestor dependency that is not yet complete."""
    seen = set()
    pending = list(by_id[task_id]["_deps"])
    while pending:
        current = pending.pop()
        if current in seen or current not in by_id:
            continue
        seen.add(current)
        if by_id[current]["status"] != "complete":
            pending.extend(by_id[current]["_deps"])
    return sorted(current for current in seen
                  if by_id[current]["status"] != "complete")


def _has_cycle(by_id):
    for task_id in by_id:
        colour = {}
        stack = [(task_id, iter(by_id[task_id]["dependencies"]))]
        colour[task_id] = 1
        while stack:
            node, children = stack[-1]
            child = next(children, None)
            if child is None:
                colour[node] = 2
                stack.pop()
            elif child not in by_id:
                continue
            elif colour.get(child) == 1:
                return True
            elif colour.get(child) != 2:
                colour[child] = 1
                stack.append((child, iter(by_id[child]["dependencies"])))
    return False


def evaluate(manifest):
    """Return a fail-closed advisory decision; never an execution grant."""
    errors = []
    if not isinstance(manifest, dict) or set(manifest) != TOP_LEVEL_KEYS:
        return {"decision": "FAIL", "errors": ["invalid top-level manifest fields"],
                "blocked_tasks": [], "conflicts": [], "summary": {}}
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != SCHEMA_VERSION:
        errors.append("unsupported schema_version")
    repositories = manifest["repositories"]
    if not isinstance(repositories, list) or not 1 <= len(repositories) <= 50:
        errors.append("repositories must be a list of 1 to 50 entries")
        repositories = []
    else:
        for repo in repositories:
            if not _text(repo, 200) or not REPO_RE.fullmatch(repo):
                errors.append("invalid repository name")
        if len(set(repositories)) != len(repositories):
            errors.append("duplicate repository name")
    agents = manifest["agents"]
    if not isinstance(agents, dict) or not set(WORKER_ROLES) <= set(agents):
        errors.append("agents must register CODEX and OPENCODE")
        agents = {}
    else:
        for name, config in agents.items():
            if not _text(name, 40) or not isinstance(config, dict) or set(config) != {"enabled"}:
                errors.append("invalid agent registration")
            elif type(config["enabled"]) is not bool:
                errors.append("agent enabled flag must be a boolean")
            elif name in WORKER_ROLES and not config["enabled"]:
                errors.append("worker role must be enabled")
            elif name not in WORKER_ROLES and config["enabled"]:
                errors.append("new agents require a reviewed contract change before enablement")
    approval = manifest["approval"]
    if not isinstance(approval, dict) or set(approval) != set(RESTRICTED_ACTIONS):
        errors.append("approval must name merge, deploy, billing and production")
    elif any(value != APPROVAL_VALUE for value in approval.values()):
        errors.append("merge, deploy, billing and production stay pending_human")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 200:
        errors.append("tasks must be a list of 1 to 200 entries")
        tasks = []

    seen_ids = set()
    extras = []
    for task in tasks:
        record = {"_paths": set(), "_deps": []}
        extras.append(record)
        if not isinstance(task, dict) or set(task) != TASK_KEYS:
            errors.append("invalid task fields")
            continue
        task_id = task["id"]
        if not isinstance(task_id, str) or not ID_RE.fullmatch(task_id):
            errors.append("invalid task id")
        elif task_id in seen_ids:
            errors.append("duplicate task id")
        else:
            seen_ids.add(task_id)
        if task["repository"] not in repositories:
            errors.append("task repository is not authorized")
        agent = task["assigned_agent"]
        if not _text(agent, 40):
            errors.append("invalid assigned_agent")
        elif agent not in agents:
            errors.append("assigned_agent is not registered")
        if not _text(task["branch"], 200) or not BRANCH_RE.fullmatch(task["branch"]):
            errors.append("invalid task branch")
        paths = task["affected_files"]
        if not isinstance(paths, list) or not 1 <= len(paths) <= 100:
            errors.append("affected_files must be a non-empty bounded list")
        else:
            normalised = [_normal_path(path) for path in paths]
            if any(path is None for path in normalised) or len(set(normalised)) != len(normalised):
                errors.append("affected_files must be unique repository-relative paths")
            else:
                record["_paths"] = set(normalised)
        deps = task["dependencies"]
        if not isinstance(deps, list) or len(deps) > 50:
            errors.append("dependencies must be a bounded list")
        else:
            if any(not isinstance(dep, str) or not ID_RE.fullmatch(dep) for dep in deps):
                errors.append("invalid dependency id")
            if task_id in deps or len(set(deps)) != len(deps):
                errors.append("self or duplicate dependency")
            record["_deps"] = deps
        status = task["status"]
        previous = task["previous_status"]
        if status not in STATUSES or previous not in (NO_STATUS,) + STATUSES:
            errors.append("invalid status or previous_status")
        elif status not in ALLOWED_TRANSITIONS[previous]:
            errors.append("disallowed status transition")
        sha = task["source_sha"]
        if sha is not None and (not isinstance(sha, str) or not SHA_RE.fullmatch(sha)):
            errors.append("source_sha must be null or 40 lowercase hex characters")
        elif status in ("evidence_ready", "complete") and sha is None:
            errors.append("source_sha is required for reviewed work")
        verification = task["verification"]
        if (not isinstance(verification, dict)
                or set(verification) != {"commands", "result", "evidence"}):
            errors.append("invalid verification fields")
        else:
            result = verification["result"]
            commands = verification["commands"]
            evidence = verification["evidence"]
            if result not in VERIFICATION_RESULTS:
                errors.append("invalid verification result")
            if not isinstance(commands, list) or len(commands) > 20 or any(
                    not _text(command, 500) for command in commands):
                errors.append("verification commands must be bounded non-empty strings")
            if not isinstance(evidence, str) or len(evidence) > 4000:
                errors.append("verification evidence must be bounded text")
            if status == "complete" and (result != "PASS" or not commands
                                         or not isinstance(evidence, str) or not evidence.strip()):
                errors.append("complete requires PASS commands and evidence")
            if result == "PASS" and status not in ("evidence_ready", "complete"):
                errors.append("PASS evidence requires evidence_ready or complete status")
        pr = task["pr_reference"]
        if pr is not None and (not isinstance(pr, str) or not PR_RE.fullmatch(pr)):
            errors.append("invalid pr_reference")
        actions = task["requested_actions"]
        if not isinstance(actions, list) or any(
                not isinstance(action, str)
                or action not in APPROVED_TASK_ACTIONS + RESTRICTED_ACTIONS for action in actions):
            errors.append("invalid requested_actions")
        elif any(action in RESTRICTED_ACTIONS for action in actions):
            errors.append("merge, deploy, billing and production need separate human approval")

    by_id = {}
    for task, record in zip(tasks, extras):
        if (isinstance(task, dict) and isinstance(task.get("id"), str)
                and ID_RE.fullmatch(task["id"]) and task["id"] in seen_ids
                and task["id"] not in by_id):
            by_id[task["id"]] = {**task, **record}
    if len(by_id) != len(seen_ids):
        errors.append("task index incomplete")
    if not errors:
        for task_id, task in by_id.items():
            for dep in task.get("_deps", []):
                other = by_id.get(dep)
                if other is None:
                    errors.append("dependency references an unknown task")
                elif other["repository"] != task["repository"]:
                    errors.append("dependency must stay in the same repository")
        if _has_cycle(by_id):
            errors.append("dependency cycle")
    if errors:
        return {"decision": "FAIL", "errors": sorted(set(errors)),
                "blocked_tasks": [], "conflicts": [], "summary": {}}

    blocked_tasks = []
    conflicts = []
    for task_id, task in by_id.items():
        if task["status"] in ("complete", "blocked"):
            continue
        unresolved = _unresolved_dependencies(task_id, by_id)
        if task["assigned_agent"] not in agents or not agents[task["assigned_agent"]]["enabled"]:
            blocked_tasks.append({"task": task_id, "reason": "agent_not_enabled",
                                  "dependencies": unresolved})
        elif unresolved:
            blocked_tasks.append({"task": task_id, "reason": "unresolved_dependency",
                                  "dependencies": unresolved})

    ids = list(by_id)
    for index, first_id in enumerate(ids):
        first = by_id[first_id]
        if first["status"] not in OWNED_STATUSES:
            continue
        for second_id in ids[index + 1:]:
            second = by_id[second_id]
            if second["status"] not in OWNED_STATUSES:
                continue
            if first["repository"] != second["repository"]:
                continue
            related = (_depends_on(first_id, second_id, by_id)
                       or _depends_on(second_id, first_id, by_id))
            shared = sorted(first["_paths"] & second["_paths"])
            both_running = (first["status"] in RUNNING_STATUSES
                            and second["status"] in RUNNING_STATUSES)
            if shared and (both_running or not related):
                conflicts.append({"tasks": [first_id, second_id],
                                  "reason": "concurrent_file_ownership", "files": shared})
            elif first["branch"] == second["branch"] and (both_running or not related):
                conflicts.append({"tasks": [first_id, second_id],
                                  "reason": "concurrent_branch_ownership",
                                  "branches": [first["branch"]]})

    decision = "BLOCKED" if blocked_tasks or conflicts else "PASS"
    summary = {
        "tasks": len(by_id),
        "repositories": len(repositories),
        "enabled_agents": sorted(name for name, cfg in agents.items() if cfg["enabled"]),
        "complete": sum(1 for item in by_id.values() if item["status"] == "complete"),
    }
    return {"decision": decision, "errors": [], "blocked_tasks": blocked_tasks,
            "conflicts": conflicts, "summary": summary}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--manifest", required=True, type=pathlib.Path,
                        help="Path to a local offline JSON task manifest")
    args = parser.parse_args(argv)
    try:
        if args.manifest.stat().st_size > MAX_MANIFEST_BYTES:
            raise ValueError("manifest exceeds 512 KiB")
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        result = {"decision": "FAIL", "errors": [f"invalid manifest file: {type(exc).__name__}"],
                  "blocked_tasks": [], "conflicts": [], "summary": {}}
        print(json.dumps(result, sort_keys=True))
        return 2
    result = evaluate(manifest)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    decision = result["decision"]
    if decision == "PASS":
        return 0
    if decision == "BLOCKED":
        return 1
    if decision == "FAIL":
        return 2
    return 2  # unknown decisions fail closed


if __name__ == "__main__":
    sys.exit(main())
