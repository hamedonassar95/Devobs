"""Contract tests for the two manual, read-only GitLab preflight workflows.

The repository does not vendor PyYAML, so these tests parse only the small YAML
shape the workflows use. They fail closed: any structural drift, widened
permission, extra trigger, or write path breaks a test instead of being ignored.
"""
import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
ANCESTRY = WORKFLOWS / "gitlab-replica-preflight-manual.yml"
POLICY = WORKFLOWS / "gitlab-mr-policy-audit-manual.yml"
SHA_PIN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+@[0-9a-f]{40}")

sys.path.insert(0, str(ROOT / "scripts"))
import gitlab_hosted_preflight as hosted  # noqa: E402
import gitlab_merge_policy as policy  # noqa: E402


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _find_block(lines: list[str], key: str, indent: int) -> list[str]:
    """Body lines of a mapping key, ending at the next line at or above indent."""
    start = None
    for index, line in enumerate(lines):
        stripped = line.strip()
        if start is None:
            if (_indent(line) == indent and stripped.endswith(":")
                    and stripped[:-1].strip() == key):
                start = index + 1
            continue
        if stripped and _indent(line) <= indent:
            return lines[start:index]
    return lines[start:] if start is not None else []


def _mapping(lines: list[str], indent: int) -> dict[str, str]:
    """Scalar keys declared exactly at ``indent``."""
    result = {}
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in stripped:
            continue
        if _indent(line) == indent:
            key, value = stripped.split(":", 1)
            result[key] = value.strip()
    return result


def _on_triggers(lines: list[str]) -> set[str]:
    triggers = set()
    for line in _find_block(lines, "on", 0):
        if line.strip() and not line.strip().startswith("#") and _indent(line) == 2:
            triggers.add(line.strip().split(":", 1)[0])
    return triggers


def _jobs(lines: list[str]) -> dict[str, list[str]]:
    """Job bodies keyed by job id, using the two-space indent under ``jobs:``."""
    jobs, current_id, current = {}, None, []
    for line in _find_block(lines, "jobs", 0):
        stripped = line.strip()
        if _indent(line) == 2 and stripped.endswith(":"):
            if current_id is not None:
                jobs[current_id] = current
            current_id = stripped[:-1].strip()
            current = [line]
        elif current_id is not None:
            current.append(line)
    if current_id is not None:
        jobs[current_id] = current
    return jobs


def _steps(job_body: list[str]) -> list[dict]:
    """Steps as dicts with scalar keys, ``with:`` children and raw text."""
    block = _find_block(job_body, "steps", 4)
    chunks, current = [], None
    for line in block:
        if _indent(line) == 6 and line.strip().startswith("- "):
            current = [line]
            chunks.append(current)
        elif current is not None:
            current.append(line)
    steps = []
    for chunk in chunks:
        key_indent = _indent(chunk[0]) + 2
        first = " " * key_indent + chunk[0].strip()[2:]
        body = [first] + chunk[1:]
        steps.append({
            "keys": _mapping(body, key_indent),
            "with": _mapping(_find_block(body, "with", key_indent), key_indent + 2),
            "text": "\n".join(body),
        })
    return steps


def _parse(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        "triggers": _on_triggers(lines),
        "permissions": _mapping(_find_block(lines, "permissions", 0), 2),
        "concurrency": _mapping(_find_block(lines, "concurrency", 0), 2),
        "jobs": _jobs(lines),
        "text": "\n".join(lines),
    }


class WorkflowContractTests(unittest.TestCase):
    def setUp(self):
        self.parsed = {"ancestry": _parse(ANCESTRY), "policy": _parse(POLICY)}

    def test_both_workflows_are_manual_dispatch_only(self):
        for name, parsed in self.parsed.items():
            with self.subTest(workflow=name):
                self.assertEqual(parsed["triggers"], {"workflow_dispatch"})

    def test_both_workflows_use_distinct_concurrency_groups(self):
        groups = {name: parsed["concurrency"].get("group")
                  for name, parsed in self.parsed.items()}
        for name, group in groups.items():
            with self.subTest(workflow=name):
                self.assertTrue(group)
        self.assertEqual(len(set(groups.values())), len(groups))
        for name, parsed in self.parsed.items():
            with self.subTest(workflow=name, key="cancel"):
                self.assertEqual(parsed["concurrency"].get("cancel-in-progress"), "false")

    def test_permissions_are_read_only_at_workflow_and_job_level(self):
        for name, parsed in self.parsed.items():
            with self.subTest(workflow=name, scope="workflow"):
                self.assertEqual(parsed["permissions"], {"contents": "read"})
            self.assertEqual(len(parsed["jobs"]), 1, name)
            for job_id, body in parsed["jobs"].items():
                with self.subTest(workflow=name, job=job_id):
                    self.assertEqual(
                        _mapping(_find_block(body, "permissions", 4), 6),
                        {"contents": "read"},
                    )

    def test_jobs_are_restricted_to_main_and_pinned(self):
        for name, parsed in self.parsed.items():
            for job_id, body in parsed["jobs"].items():
                keys = _mapping(body, 4)
                with self.subTest(workflow=name, job=job_id):
                    self.assertEqual(keys.get("if"), "github.ref == 'refs/heads/main'")
                    self.assertEqual(keys.get("timeout-minutes"), "5")
                    self.assertTrue(keys.get("runs-on", "").startswith("ubuntu-"))

    def test_actions_are_sha_pinned_and_checkout_drops_credentials(self):
        for name, parsed in self.parsed.items():
            for job_id, body in parsed["jobs"].items():
                steps = _steps(body)
                uses = [step["keys"].get("uses") for step in steps]
                pinned = [value for value in uses if value]
                with self.subTest(workflow=name, job=job_id):
                    self.assertEqual(len(pinned), 2)
                    for value in pinned:
                        self.assertRegex(value.split("#")[0].strip(), SHA_PIN.pattern)
                checkouts = [step for step in steps
                             if "actions/checkout@" in (step["keys"].get("uses") or "")]
                with self.subTest(workflow=name, job=job_id, step="checkout"):
                    self.assertEqual(len(checkouts), 1)
                    self.assertEqual(checkouts[0]["with"].get("persist-credentials"), "false")

    def test_every_run_step_is_fail_closed(self):
        for name, parsed in self.parsed.items():
            for job_id, body in parsed["jobs"].items():
                for step in _steps(body):
                    if "run" not in step["keys"]:
                        continue
                    with self.subTest(workflow=name, job=job_id,
                                      step=step["keys"].get("name")):
                        self.assertIn("set -euo pipefail", step["text"])

    def test_ancestry_workflow_does_not_run_the_policy_audit(self):
        self.assertIn("scripts/gitlab_hosted_preflight.py", self.parsed["ancestry"]["text"])
        self.assertNotIn("gitlab_merge_policy", self.parsed["ancestry"]["text"])

    def test_policy_workflow_does_not_run_ancestry_checks(self):
        text = self.parsed["policy"]["text"]
        self.assertIn("scripts/gitlab_merge_policy.py", text)
        self.assertNotIn("gitlab_hosted_preflight", text)
        self.assertNotIn("gitlab_fast_forward_preflight", text)
        self.assertNotIn("git merge-base", text)

    def test_workflows_contain_no_write_bypass_or_sync_approval_path(self):
        forbidden = (
            "continue-on-error", "|| true", "secrets.", "git push",
            "--force", "--mirror", "SYNC_APPROVED", "pull_request:",
            "schedule:", "push:", "workflow_run:",
        )
        for name, parsed in self.parsed.items():
            for token in forbidden:
                with self.subTest(workflow=name, token=token):
                    self.assertNotIn(token, parsed["text"])


class MissingPolicyMetadataTests(unittest.TestCase):
    def payload(self, **changes):
        base = {"id": 89037773, "path_with_namespace": "hamedonassar95/Devobs",
                "visibility": "public", "default_branch": "main", "merge_method": "ff"}
        base.update(changes)
        return json.dumps(base).encode("utf-8")

    def test_missing_merge_method_never_counts_as_verified(self):
        payload = json.loads(self.payload())
        del payload["merge_method"]
        result, code = policy.audit(json.dumps(payload).encode("utf-8"))
        self.assertEqual((result["status"], code), ("BLOCKED", 2))
        self.assertEqual(result["reason"], "missing_field:merge_method")
        self.assertNotIn("mr_path", result)
        self.assertNotIn("merge_method", result)

    def test_null_or_wrong_type_merge_method_is_not_defaulted(self):
        for bad in (None, 0, [], {}, True):
            with self.subTest(value=bad):
                result, code = policy.audit(self.payload(merge_method=bad))
                self.assertEqual((result["status"], code), ("BLOCKED", 2))
                self.assertEqual(result["reason"], "wrong_type:merge_method")
                self.assertNotIn("mr_path", result)

    def test_valid_methods_still_require_human_approval(self):
        for method in ("ff", "merge", "rebase_merge"):
            with self.subTest(method=method):
                result, code = policy.audit(self.payload(merge_method=method))
                self.assertEqual(code, 0)
                self.assertEqual(result["status"], "REVIEW_REQUIRED")
                self.assertTrue(result["approval_required_for_replica_transfer"])
                self.assertEqual(result["direct_git_push"], "NOT_EVALUATED")
                self.assertNotIn("SYNC_APPROVED", json.dumps(result))


class AncestryLabelTests(unittest.TestCase):
    def test_ancestry_candidate_is_review_required_not_sync_approved(self):
        def probe(repo):
            return {"status": "FAST_FORWARD_CANDIDATE", "github_sha": "b" * 40,
                    "gitlab_sha": "a" * 40, "write_performed": False}

        result, code = hosted.evaluate(ROOT, probe=probe)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "REVIEW_REQUIRED")
        self.assertTrue(result["human_approval_required_for_sync"])
        self.assertNotIn("SYNC_APPROVED", json.dumps(result))

    def test_ancestry_match_is_not_a_sync_approval_either(self):
        def probe(repo):
            sha = "c" * 40
            return {"status": "ALREADY_MATCHED", "github_sha": sha,
                    "gitlab_sha": sha, "write_performed": False}

        result, code = hosted.evaluate(ROOT, probe=probe)
        self.assertEqual((result["status"], code), ("ALREADY_MATCHED", 0))
        self.assertTrue(result["human_approval_required_for_sync"])
        self.assertNotIn("SYNC_APPROVED", json.dumps(result))

    def test_production_scripts_never_emit_sync_approved(self):
        for name in ("gitlab_hosted_preflight.py", "gitlab_merge_policy.py",
                     "gitlab_fast_forward_preflight.py"):
            with self.subTest(script=name):
                text = (ROOT / "scripts" / name).read_text(encoding="utf-8")
                self.assertNotIn("SYNC_APPROVED", text)


if __name__ == "__main__":
    unittest.main()
