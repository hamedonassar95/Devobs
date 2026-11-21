"""CLI behavior for the offline integration control plane."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

from devobs.integration_control.__main__ import main

try:
    from . import helpers as h
    from . import hardening_fixtures as hf
except ImportError:  # unittest discover -s tests/integration_control
    import helpers as h
    import hardening_fixtures as hf


class ControlPlaneCliTests(unittest.TestCase):
    def _run(
        self,
        document: object,
        output_format: str = "json",
        *,
        extra_files: dict[str, Any] | None = None,
        extra_args: list[str] | None = None,
    ) -> tuple[int, str]:
        with tempfile.TemporaryDirectory(prefix="integration-control-cli-") as folder:
            root = Path(folder)
            (root / "snapshot.json").write_text(
                json.dumps(document, sort_keys=True), encoding="utf-8"
            )
            for name, payload in (extra_files or {}).items():
                (root / name).write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            resolved = [
                str(root / arg) if arg in (extra_files or {}) else arg
                for arg in (extra_args or [])
            ]
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main([
                    "--input", str(root / "snapshot.json"),
                    "--format", output_format,
                    *resolved,
                ])
            return code, stream.getvalue()

    def test_valid_snapshot_exit_zero_and_json_report(self) -> None:
        code, output = self._run(h.snapshot())

        report = json.loads(output)
        self.assertEqual(code, 0)
        self.assertEqual(report["decision"], "PROCEED_TO_HUMAN_REVIEW")
        self.assertFalse(report["merge_authorized"])
        self.assertIn("HARDENING_MANIFEST_DIGEST",
                      {item["code"] for item in report["findings"]})

    def test_malformed_document_fails_closed(self) -> None:
        code, output = self._run({"not": "a snapshot"})

        report = json.loads(output)
        self.assertEqual(code, 3)
        self.assertEqual(report["decision"], "INVALID")
        self.assertEqual(report["findings"][0]["code"], "invalid_snapshot_fields")

    def test_markdown_output_includes_separate_check_counts(self) -> None:
        _code, output = self._run(h.snapshot(), output_format="markdown")

        self.assertIn("## Checks", output)
        self.assertIn("Passed:", output)
        self.assertIn("Failed: none", output)
        self.assertIn("Skipped: none", output)

    def test_approval_evidence_option_is_advisory_only(self) -> None:
        code, output = self._run(
            h.snapshot(),
            extra_files={"approval.json": hf.complete_approval_set()},
            extra_args=["--approval-evidence", "approval.json"],
        )

        report = json.loads(output)
        self.assertEqual(code, 0)
        self.assertFalse(report["merge_authorized"])
        self.assertIn("APPROVAL_EVIDENCE_PRESENT",
                      {item["code"] for item in report["findings"]})

    def test_empty_approval_evidence_is_unverified(self) -> None:
        code, output = self._run(
            h.snapshot(),
            extra_files={"approval.json": []},
            extra_args=["--approval-evidence", "approval.json"],
        )

        report = json.loads(output)
        self.assertEqual(code, 2)
        self.assertEqual(report["decision"], "UNVERIFIED")
        self.assertIn("APPROVAL_EVIDENCE_MISSING",
                      {item["code"] for item in report["findings"]})

    def test_restricted_action_manifest_exit_one(self) -> None:
        document = h.snapshot(coordination=h.manifest(
            h.task("ICP01", actions=["code_change", "merge"]),
        ))

        code, output = self._run(document)

        report = json.loads(output)
        self.assertEqual(code, 1)
        self.assertIn("UNAUTHORIZED_ACTION_REQUESTED",
                      {item["code"] for item in report["findings"]})

    def test_unreadable_approval_evidence_fails_closed(self) -> None:
        code, output = self._run(
            h.snapshot(),
            extra_args=["--approval-evidence", "missing.json"],
        )

        report = json.loads(output)
        self.assertEqual(code, 1)
        self.assertIn("APPROVAL_EVIDENCE_INVALID",
                      {item["code"] for item in report["findings"]})

    def test_retry_policy_option_blocks_prior_attempt(self) -> None:
        document = h.snapshot()
        from devobs.integration_control.security import digest_payload

        policy = hf.retry_policy(prior_attempt_digests=[
            digest_payload(document["coordination"]),
        ])
        code, output = self._run(
            document,
            extra_files={"retry.json": policy},
            extra_args=["--retry-policy", "retry.json"],
        )

        report = json.loads(output)
        self.assertEqual(code, 1)
        self.assertIn("UNSAFE_RETRY_LOOP",
                      {item["code"] for item in report["findings"]})


if __name__ == "__main__":
    unittest.main()
