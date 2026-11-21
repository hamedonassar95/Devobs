"""Behavioral tests for sanitized, deterministic orchestration audit events."""
import importlib
import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
for _folder in (ROOT, ROOT / "scripts", ROOT / "tools"):
    _path = str(_folder)
    if _path not in sys.path:
        sys.path.insert(0, _path)


def load_module(name):
    """Fail on absence without turning a missing module into an import traceback."""
    try:
        spec = importlib.util.find_spec(name)
    except ModuleNotFoundError:
        spec = None
    if spec is None:
        raise AssertionError("missing module: " + name)
    return importlib.import_module(name)


def synthetic_github_token():
    """Build a synthetic credential-like value without storing a literal secret."""
    return "gh" + "p_" + "ABCDEFGHIJ" + "KLMNOPQRST" + "0123456789"


def synthetic_jwt():
    """Build a synthetic three-part value without storing a literal JWT."""
    return ("eyJ" + "hbGciOiJIUzI1NiJ9."
            + "eyJzdWIiOiJzeW50aGV0aWMifQ."
            + "SIGNATUREVALUE")


class AuditSafetyTests(unittest.TestCase):
    def test_credentials_are_redacted_before_an_event_is_exported(self):
        audit = load_module("devobs.orchestration.audit")
        token = synthetic_github_token()
        jwt = synthetic_jwt()
        value = (
            "Authorization: Bearer " + "SYNTHETICBEARER123 task token="
            + token + " jwt=" + jwt
        )
        result = audit.sanitize(value)
        self.assertIsInstance(result, str)
        self.assertNotIn("SYNTHETICBEARER123", result)
        self.assertNotIn(token, result)
        self.assertNotIn("SIGNATUREVALUE", result)
        self.assertIn(audit.REDACTED, result)

    def test_events_are_structured_sequence_numbered_and_timestamp_free(self):
        audit = load_module("devobs.orchestration.audit")
        trail = audit.AuditTrail("PLAN-1")
        trail.record("plan_started", tasks=3, note="token=" + synthetic_github_token())
        trail.record("task_blocked", task_id="TASK-001", reason="capacity_exhausted")
        events = trail.to_dict()
        self.assertEqual([event["sequence"] for event in events], [1, 2])
        self.assertTrue(all(event["plan_id"] == "PLAN-1" for event in events))
        self.assertEqual(events[1]["event"], "task_blocked")
        self.assertEqual(events[1]["fields"]["reason"], "capacity_exhausted")
        self.assertTrue(all("timestamp" not in event and "time" not in event for event in events))
        self.assertNotIn(synthetic_github_token(), str(events))

    def test_scope_fingerprint_is_canonical_and_content_bound(self):
        audit = load_module("devobs.orchestration.audit")
        first = audit.scope_fingerprint({"b": 1, "a": [2, 3]})
        reordered = audit.scope_fingerprint({"a": [2, 3], "b": 1})
        changed = audit.scope_fingerprint({"a": [2, 4], "b": 1})
        self.assertEqual(first, reordered)
        self.assertEqual(len(first), 64)
        self.assertNotEqual(first, changed)

    def test_unknown_and_policy_failures_are_not_retried(self):
        audit = load_module("devobs.orchestration.audit")
        retryable = audit.classify_failure("rate_limited", attempt=1, max_retries=3)
        terminal = audit.classify_failure("validation_error", attempt=1, max_retries=3)
        policy = audit.classify_failure("approval_required", attempt=1, max_retries=3)
        unknown = audit.classify_failure("unrecognized_thing", attempt=1, max_retries=3)
        self.assertEqual(retryable.category, audit.RETRYABLE)
        self.assertTrue(retryable.retry_allowed)
        self.assertEqual(terminal.category, audit.TERMINAL)
        self.assertFalse(terminal.retry_allowed)
        self.assertEqual(policy.category, audit.POLICY)
        self.assertFalse(policy.retry_allowed)
        self.assertEqual(unknown.category, audit.UNKNOWN)
        self.assertFalse(unknown.retry_allowed)

    def test_retry_limit_is_enforced_for_retryable_failures(self):
        audit = load_module("devobs.orchestration.audit")
        exhausted = audit.classify_failure("timeout", attempt=3, max_retries=3)
        self.assertFalse(exhausted.retry_allowed)
        self.assertEqual(exhausted.reason, "retry_limit_exhausted")


if __name__ == "__main__":
    unittest.main()
