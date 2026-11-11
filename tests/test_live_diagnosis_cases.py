"""Offline safety tests for the post-deployment synthetic diagnosis runner."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from devobs_intelligence.run_live_diagnosis_cases import (  # noqa: E402
    _CASES,
    run_cases,
    write_report,
)


class LiveDiagnosisCasesTests(unittest.TestCase):
    def test_five_synthetic_cases_record_input_output_latency_without_token(self):
        class Response:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self, limit):
                return json.dumps({
                    "diagnosis": "Synthetic diagnosis",
                    "recommendation": "Inspect the related subsystem safely.",
                    "severity": "medium",
                    "confidence": "medium",
                    "model": "gpt-6-luna",
                    "latency_ms": 12,
                }).encode()

        opener = Mock()
        opener.open.side_effect = [Response() for _ in _CASES]
        times = iter([1.000, 1.025] * len(_CASES))
        report = run_cases(
            "https://devobs-ai-staging.onrender.com/v1/tenants/demo/projects/repair/"
            "services/api/diagnostics",
            "synthetic-bearer-token",
            opener=opener,
            clock=lambda: next(times),
            wall_clock=lambda: datetime(2026, 11, 5, tzinfo=timezone.utc),
        )
        self.assertEqual(opener.open.call_count, 5)
        self.assertEqual(report["cases_sent"], 5)
        self.assertEqual([record["case_id"] for record in report["results"]],
                         [case["case_id"] for case in _CASES])
        for record, case in zip(report["results"], _CASES):
            self.assertEqual(record["input"], case["error_log"])
            self.assertEqual(record["output"]["model"], "gpt-6-luna")
            self.assertEqual(record["client_latency_ms"], 25)
            self.assertEqual(record["server_latency_ms"], 12)
            self.assertTrue(record["passed"])
        self.assertNotIn("synthetic-bearer-token", json.dumps(report))
        for call in opener.open.call_args_list:
            request = call.args[0]
            self.assertEqual(call.kwargs["timeout"], 120)
            self.assertEqual(request.get_method(), "POST")
            self.assertEqual(request.get_header("Authorization"),
                             "Bearer synthetic-bearer-token")
            self.assertNotIn("synthetic-bearer-token", request.data.decode())

    def test_rejects_non_https_wrong_route_and_existing_report(self):
        opener = Mock()
        for endpoint in (
            "http://devobs-ai-staging.onrender.com/v1/tenants/a/projects/b/services/c/diagnostics",
            "https://devobs-ai-staging.onrender.com/healthz",
        ):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                run_cases(endpoint, "synthetic-token", opener=opener)
        opener.open.assert_not_called()

        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.json"
            target.write_text("existing", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_report(target, {"results": []})
            self.assertEqual(target.read_text(encoding="utf-8"), "existing")

    def test_report_file_is_owner_only(self):
        if os.name != "posix":
            self.skipTest("POSIX file permission check")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.json"
            write_report(target, {"cases_sent": 5, "results": []})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8"))["cases_sent"], 5)


if __name__ == "__main__":
    unittest.main()
