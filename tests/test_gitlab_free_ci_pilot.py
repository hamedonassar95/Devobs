"""Fail-closed regression for the reviewed manual GitLab Free smoke pilot.

The strict text contract intentionally rejects any unreviewed changes to the
pipeline trigger, billing behavior, runner image, or job command. Actual GitLab
CI Lint and live execution remain separate provider-side acceptance gates.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".gitlab-ci.yml"
EXPECTED_CONFIG = '''# GitLab Free pilot: pipeline creation and execution are both manually gated.
# No push, merge-request, scheduled, API or external-trigger pipelines.
workflow:
  rules:
    - if: '$CI_PIPELINE_SOURCE == "web" && $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'
      when: always
    - when: never

stages:
  - verify

free_offline_smoke:
  stage: verify
  image: docker.io/library/python:3.12.15-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258
  rules:
    - when: manual
      allow_failure: false
  timeout: 5m
  script:
    - python3 scripts/milestone_ledger.py --summary
    - python3 -m unittest discover -s tests -p 'test_gitlab_free_ci_pilot.py' -v
'''


class GitLabFreePilotTests(unittest.TestCase):
    def test_manual_pipeline_policy_is_exactly_reviewed(self):
        self.assertEqual(CONFIG_PATH.read_text(encoding="utf-8"), EXPECTED_CONFIG)

    def test_real_offline_ledger_validation_keeps_release_gates_closed(self):
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--summary"],
            cwd=ROOT, text=True, capture_output=True, check=False, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["repository"], "hamedonassar95/Devobs")
        self.assertGreaterEqual(result["merged_milestones"], 280)
        self.assertGreaterEqual(result["latest_pr"], 688)
        self.assertEqual(result["gate_statuses"]["p01-managed-saas"], "BLOCKED")
        self.assertEqual(result["gate_statuses"]["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(result["gate_statuses"]["codex-agent-runtime-acceptance"], "OPEN")


if __name__ == "__main__":
    unittest.main()
