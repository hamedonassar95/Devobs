"""Behavioral contract tests for versioned, scoped incident findings."""
import hashlib
import json
import sys
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from devobs_intelligence.context import (
    ContextError, normalize_telemetry, ServiceTopology, ServiceTopologySnapshot,
)
from devobs_intelligence.correlation import (
    IncidentFinding, correlate, validate_impact_paths_against_snapshot,
)
from devobs_intelligence.incident_memory import IncidentMemory

NOW = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)


def make_finding(metric="error_rate_pct", value=8.0):
    topology = ServiceTopology("alpha", "platform", ["api", "db"], [("api", "db")])
    telemetry = normalize_telemetry({
        "tenant": "alpha", "project": "platform", "service": "db",
        "source_sha": "a" * 40, "observed_at": "2026-11-02T12:00:00Z",
        "metric": metric, "value": value,
        "evidence_digest": "b" * 64,
    })
    return correlate(topology, [telemetry], IncidentMemory([]), NOW)


def make_snapshot(services=("api", "cache", "db"),
                  edges=(("api", "db"), ("api", "cache"), ("cache", "db")),
                  source_sha="a" * 40):
    return ServiceTopologySnapshot(
        "alpha", "platform", list(services), list(edges), source_sha,
        NOW.isoformat(),
    )


def reseal(record):
    payload = {key: value for key, value in record.items()
               if key != "finding_digest"}
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")
    record["finding_digest"] = hashlib.sha256(canonical).hexdigest()
    return record


class IncidentFindingContractTests(unittest.TestCase):
    def test_scoped_finding_round_trips_through_json_deterministically(self):
        finding = make_finding()
        record = finding.to_record()
        restored = IncidentFinding.from_record(json.loads(json.dumps(record)))

        self.assertEqual(record["schema_version"], 3)
        self.assertEqual(record["ranking_interpretation"], "fixed_heuristic_not_causal")
        self.assertEqual(record["ranked_service_evidence"][0]["service"], "db")
        self.assertEqual(record["ranked_service_evidence"][0]["score"], 2)
        self.assertEqual(
            record["impact_path_interpretation"],
            "declared_edges_not_causal",
        )
        self.assertEqual(
            record["impact_paths"],
            [
                {"service": "api", "path_services": ["api", "db"]},
                {"service": "db", "path_services": ["db"]},
            ],
        )
        self.assertEqual(
            record["ranked_service_evidence"][0]["signals"],
            [{
                "metric": "error_rate_pct",
                "reason_code": "error_rate_threshold_met",
                "points": 2,
                "evidence_digest": "b" * 64,
            }],
        )
        self.assertEqual(record["tenant"], "alpha")
        self.assertEqual(record["project"], "platform")
        self.assertEqual(restored, finding)
        self.assertEqual(restored.to_record(), record)

    def test_abstention_round_trips_without_inventing_a_ranked_service(self):
        finding = make_finding("capacity_pct", 10.0)
        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")

        restored = IncidentFinding.from_record(finding.to_record())

        self.assertEqual(restored, finding)
        self.assertEqual(restored.ranked_services, ())
        self.assertEqual(restored.ranked_service_evidence, ())
        self.assertEqual(restored.impacted_services, ())
        self.assertEqual(restored.impact_paths, ())

    def test_rehashed_impact_path_with_wrong_start_service_is_rejected(self):
        record = make_finding().to_record()
        record["impact_paths"][0]["path_services"][0] = "db"
        reseal(record)

        with self.assertRaisesRegex(ContextError, "invalid_incident_finding_impact_paths"):
            IncidentFinding.from_record(record)

    def test_impact_paths_are_recomputed_against_the_exact_fresh_snapshot(self):
        topology = make_snapshot()
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": "a" * 40, "observed_at": NOW.isoformat(),
            "metric": "error_rate_pct", "value": 8,
            "evidence_digest": "b" * 64,
        })
        finding = correlate(topology, [telemetry], IncidentMemory([]), NOW)

        verified = validate_impact_paths_against_snapshot(
            finding.to_record(), topology, now_utc=NOW,
        )

        self.assertEqual(verified, finding)

        altered = make_snapshot(edges=(("api", "db"), ("api", "cache")))
        with self.assertRaisesRegex(ContextError, "incident_finding_topology_mismatch"):
            validate_impact_paths_against_snapshot(
                finding.to_record(), altered, now_utc=NOW,
            )

        with self.assertRaisesRegex(ContextError, "stale_topology"):
            validate_impact_paths_against_snapshot(
                finding.to_record(), topology,
                now_utc=NOW + timedelta(seconds=901),
            )

    def test_snapshot_validator_rejects_a_valid_shaped_but_nonshortest_path(self):
        topology = make_snapshot()
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": "a" * 40, "observed_at": NOW.isoformat(),
            "metric": "error_rate_pct", "value": 8,
            "evidence_digest": "b" * 64,
        })
        finding = correlate(topology, [telemetry], IncidentMemory([]), NOW)
        record = finding.to_record()
        record["impact_paths"][0]["path_services"] = ["api", "cache", "db"]
        reseal(record)

        # The strict record parser can validate shape, but needs the exact graph
        # to distinguish a valid longer route from the deterministic shortest one.
        self.assertEqual(IncidentFinding.from_record(record).impact_paths[0].path_services,
                         ("api", "cache", "db"))
        with self.assertRaisesRegex(ContextError, "incident_finding_impact_paths_mismatch"):
            validate_impact_paths_against_snapshot(record, topology, now_utc=NOW)

    def test_snapshot_validator_accepts_abstention_without_ranked_paths(self):
        topology = make_snapshot()
        telemetry = normalize_telemetry({
            "tenant": "alpha", "project": "platform", "service": "db",
            "source_sha": "a" * 40, "observed_at": NOW.isoformat(),
            "metric": "capacity_pct", "value": 10,
            "evidence_digest": "b" * 64,
        })
        finding = correlate(topology, [telemetry], IncidentMemory([]), NOW)

        self.assertEqual(finding.status, "INSUFFICIENT_EVIDENCE")
        self.assertEqual(
            validate_impact_paths_against_snapshot(
                finding.to_record(), topology, now_utc=NOW,
            ),
            finding,
        )

    def test_tampered_ranking_is_rejected_even_with_recomputed_digest(self):
        record = make_finding().to_record()
        record["ranked_service_evidence"][0]["signals"][0]["points"] = 1
        payload = {key: value for key, value in record.items()
                   if key != "finding_digest"}
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        record["finding_digest"] = hashlib.sha256(canonical).hexdigest()

        with self.assertRaisesRegex(ContextError, "invalid_incident_finding_ranking"):
            IncidentFinding.from_record(record)

    def test_unknown_fields_versions_and_content_changes_are_rejected(self):
        record = make_finding().to_record()

        extra = {**record, "unexpected": "value"}
        with self.assertRaisesRegex(ContextError, "invalid_incident_finding_record"):
            IncidentFinding.from_record(extra)

        unsupported = {**record, "schema_version": 4}
        with self.assertRaisesRegex(ContextError, "unsupported_incident_finding_schema"):
            IncidentFinding.from_record(unsupported)

        changed = {**record, "category": "capacity_pressure"}
        with self.assertRaisesRegex(ContextError, "incident_finding_digest_mismatch"):
            IncidentFinding.from_record(changed)


if __name__ == "__main__":
    unittest.main()
