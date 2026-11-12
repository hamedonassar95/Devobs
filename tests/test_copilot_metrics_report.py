import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.copilot_metrics_report import (
    MetricsInputError,
    main,
    render_report,
    summarize_metrics,
)


def usage_row(
    *, day="2026-11-01", kind="remote_user", surface="copilot_cli", requests=3,
    prompt_tokens=40, output_tokens=25, byok=None,
):
    return {
        "day": day,
        "user_login": "private-example-user",
        "totals_by_local_byok": byok
        if byok is not None
        else [
            {
                "byok_kind": kind,
                "surface": surface,
                "request_count": requests,
                "prompt_count": 2,
                "token_usage": {
                    "prompt_tokens_sum": prompt_tokens,
                    "output_tokens_sum": output_tokens,
                    "avg_tokens_per_request": 21.67,
                },
            }
        ],
    }


class CopilotMetricsReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)

    def write_ndjson(self, name, rows):
        path = self.root / name
        path.write_text(
            "".join(json.dumps(row) + "\n" for row in rows),
            encoding="utf-8",
        )
        return path

    def test_aggregates_disjoint_report_shards_without_emitting_user_fields(self):
        first = self.write_ndjson("part-1.ndjson", [usage_row()])
        second = self.write_ndjson(
            "part-2.ndjson",
            [
                usage_row(
                    day="2026-11-02",
                    kind="local_user",
                    surface="copilot_app",
                    requests=5,
                    prompt_tokens=120,
                    output_tokens=70,
                )
            ],
        )

        report = summarize_metrics([first, second])
        rendered = render_report(report)

        self.assertEqual(report["records"], 2)
        self.assertEqual(report["requests"], 8)
        self.assertEqual(report["prompt_tokens"], 160)
        self.assertEqual(report["output_tokens"], 95)
        self.assertEqual(report["days"], ["2026-11-01", "2026-11-02"])
        self.assertIn("remote_user", rendered)
        self.assertIn("local_user", rendered)
        self.assertIn("USD cost: not available", rendered)
        self.assertIn("Budget gate: unchanged", rendered)
        self.assertNotIn("private-example-user", rendered)

    def test_reports_unknown_metrics_separately_from_observed_zero(self):
        path = self.write_ndjson(
            "partial.ndjson",
            [usage_row(byok=[]), {"day": "2026-11-02", "totals_by_local_byok": None}],
        )

        report = summarize_metrics([path])
        rendered = render_report(report)

        self.assertEqual(report["records_with_byok_metrics"], 1)
        self.assertEqual(report["records_with_unavailable_byok_metrics"], 1)
        self.assertEqual(report["requests"], 0)
        self.assertIn("1/2 records; 1 unavailable", rendered)

    def test_fails_closed_when_no_usable_byok_field_is_present(self):
        path = self.write_ndjson("old.ndjson", [{"day": "2026-11-01"}])
        with self.assertRaisesRegex(MetricsInputError, "no_usable_byok_metrics"):
            summarize_metrics([path])

    def test_fails_closed_for_invalid_counts_or_token_shapes(self):
        malformed_count = self.write_ndjson(
            "bad-count.ndjson", [usage_row(requests=True)]
        )
        with self.assertRaisesRegex(MetricsInputError, "invalid_count:request_count"):
            summarize_metrics([malformed_count])

        malformed_tokens = usage_row()
        malformed_tokens["totals_by_local_byok"][0]["token_usage"]["output_tokens_sum"] = -1
        bad_tokens = self.write_ndjson("bad-tokens.ndjson", [malformed_tokens])
        with self.assertRaisesRegex(MetricsInputError, "invalid_count:output_tokens_sum"):
            summarize_metrics([bad_tokens])

    def test_fails_closed_on_malformed_or_duplicate_key_ndjson(self):
        for name, content in (
            ("bad-json.ndjson", "{not-json}\n"),
            ("duplicate.ndjson", '{"day":"2026-11-01","day":"2026-11-02"}\n'),
            ("blank.ndjson", "\n"),
        ):
            with self.subTest(name=name):
                path = self.root / name
                path.write_text(content, encoding="utf-8")
                with self.assertRaises(MetricsInputError):
                    summarize_metrics([path])

    def test_cli_reports_input_errors_without_touching_budget_settings(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            result = main(["--input", str(self.root / "missing.ndjson")])

        self.assertEqual(result, 1)
        self.assertIn("input_file_not_found", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
