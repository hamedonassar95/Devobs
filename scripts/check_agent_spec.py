#!/usr/bin/env python3
"""Validate the machine-readable AI agent inventory and enforce known guardrails."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "agent-spec.yaml"
REQUIRED_FIELDS = {
    "id",
    "workflow",
    "provider",
    "model",
    "objective",
    "success_metric",
    "baseline_status",
    "estimated_cost_usd_per_run",
    "cost_status",
    "budget_gate",
    "max_retries",
    "max_provider_calls_per_run",
    "human_review",
    "production_write",
}
GH_AW_WORKFLOWS = {
    ".github/workflows/efficiency-improver",
    ".github/workflows/incident-investigator",
    ".github/workflows/incident-investigator-claude",
    ".github/workflows/incident-investigator-vertex",
    ".github/workflows/phase8b-ai-patch-generator",
}


def fail(message: str) -> None:
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> None:
    try:
        spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"Cannot read {SPEC_PATH.relative_to(ROOT)} as JSON-compatible YAML: {exc}")

    policy = spec.get("policy")
    agents = spec.get("agents")
    if spec.get("schema_version") != 1 or not isinstance(policy, dict) or not isinstance(agents, list):
        fail("agent-spec.yaml must declare schema_version 1, policy, and agents.")
    if policy.get("max_retries") != 3:
        fail("The global retry ceiling must remain three.")
    if policy.get("production_mutations_allowed") is not False:
        fail("Agents must not be authorized to mutate production.")
    if policy.get("production_mutations_require_human_approval") is not True:
        fail("Production mutations must require explicit human approval.")
    if policy.get("budget_approval_variable") != "DEVOBS_AI_BUDGET_APPROVED":
        fail("The explicit AI budget approval variable changed unexpectedly.")
    if policy.get("budget_approval_is_dollar_cap") is not False:
        fail("A manual approval switch must not be misrepresented as a dollar cap.")

    seen: set[str] = set()
    for agent in agents:
        if not isinstance(agent, dict) or REQUIRED_FIELDS - agent.keys():
            missing = sorted(REQUIRED_FIELDS - set(agent.keys())) if isinstance(agent, dict) else sorted(REQUIRED_FIELDS)
            fail(f"Agent entry is malformed; missing fields: {', '.join(missing)}")
        agent_id = agent["id"]
        if not isinstance(agent_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]*", agent_id) or agent_id in seen:
            fail(f"Agent id is invalid or duplicated: {agent_id!r}")
        seen.add(agent_id)
        workflow = ROOT / agent["workflow"]
        if not workflow.is_file() or ROOT not in workflow.resolve().parents:
            fail(f"Agent {agent_id} references a missing or out-of-repository workflow.")
        if not agent["objective"].strip() or not agent["success_metric"].strip() or agent["baseline_status"] != "not_measured":
            fail(f"Agent {agent_id} must document its objective, metric, and unmeasured baseline honestly.")
        if agent["estimated_cost_usd_per_run"] is not None:
            fail(f"Agent {agent_id} must not claim a cost estimate until provider/account pricing is measured.")
        if type(agent["max_retries"]) is not int or not 0 <= agent["max_retries"] <= policy["max_retries"]:
            fail(f"Agent {agent_id} exceeds the retry ceiling.")
        if type(agent["max_provider_calls_per_run"]) is not int or not 1 <= agent["max_provider_calls_per_run"] <= 3:
            fail(f"Agent {agent_id} has an invalid provider-call limit.")
        if agent["production_write"] is not False or not agent["human_review"].strip():
            fail(f"Agent {agent_id} must remain non-production-writing and document human review.")

    required_direct_gates = {
        ".github/workflows/ai-code-review.yml",
        ".github/workflows/claude-code-assistant.yml",
    }
    for relative in required_direct_gates:
        content = (ROOT / relative).read_text(encoding="utf-8")
        if "DEVOBS_AI_BUDGET_APPROVED" not in content or "approved == 'true'" not in content:
            fail(f"Direct provider workflow {relative} must require explicit budget approval before inference.")

    breaker = (ROOT / ".github/workflows/ai-provider-circuit-breaker.yml").read_text(encoding="utf-8")
    if not re.search(r"if:.*DEVOBS_AI_BUDGET_APPROVED\s*==\s*'true'", breaker):
        fail("Vertex AI failover must require explicit budget approval.")

    for workflow_id in GH_AW_WORKFLOWS:
        source_path = ROOT / f"{workflow_id}.md"
        lock_path = ROOT / f"{workflow_id}.lock.yml"
        source = source_path.read_text(encoding="utf-8")
        lock = lock_path.read_text(encoding="utf-8")
        frontmatter = re.match(r"\A---\n(.*?)\n---\n", source, re.DOTALL)
        if frontmatter is None or not re.search(
            r"^if:.*vars\.DEVOBS_AI_BUDGET_APPROVED\s*==\s*'true'",
            frontmatter.group(1),
            re.MULTILINE,
        ):
            fail(f"Agentic workflow {source_path.relative_to(ROOT)} must require explicit budget approval.")

        jobs = re.search(r"^jobs:\s*\n(.*)", lock, re.MULTILINE | re.DOTALL)
        if jobs is None:
            fail(f"Generated workflow {lock_path.relative_to(ROOT)} has no jobs section.")
        activation = re.search(
            r"^  activation:\s*\n(.*?)(?=^  [a-zA-Z0-9_-]+:\s*$|\Z)",
            jobs.group(1),
            re.MULTILINE | re.DOTALL,
        )
        if activation is None or not re.search(
            r"vars\.DEVOBS_AI_BUDGET_APPROVED\s*==\s*'true'", activation.group(1)
        ):
            fail(f"Generated workflow {lock_path.relative_to(ROOT)} is missing its budget approval gate; recompile it with gh-aw.")

    print(f"Validated {len(agents)} agent specs, retry/production policy, direct-provider gates, Vertex failover, and all {len(GH_AW_WORKFLOWS)} gh-aw source/lock budget gates.")


if __name__ == "__main__":
    main()
