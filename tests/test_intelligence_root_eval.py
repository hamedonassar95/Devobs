"""Root-cause evaluation is measurable, abstention-aware, and never a release permit."""
import sys
import unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from devobs_intelligence.context import normalize_telemetry,ServiceTopology
from devobs_intelligence.incident_memory import IncidentMemory
from devobs_intelligence.correlation import correlate,IncidentFinding
from devobs_intelligence.root_eval import evaluate_root_rankings,RootEvaluationError

NOW=datetime(2026,10,25,1,0,tzinfo=timezone.utc)


def finding(metric="error_rate_pct",value=8.0):
    graph=ServiceTopology("alpha","platform",["api","db","web"],
                          [("web","api"),("api","db")])
    point=normalize_telemetry({"tenant":"alpha","project":"platform",
        "service":"db","source_sha":"a"*40,
        "observed_at":"2026-10-25T01:00:00Z",
        "metric":metric,"value":value,"evidence_digest":"b"*64})
    return correlate(graph,[point],IncidentMemory([]),NOW)


def item(name, expected, outcome=None):
    return {"case_id":name,"expected_service":expected,"finding":outcome or finding()}


class RankingEvaluationTests(unittest.TestCase):
    def test_top1_top3_and_abstention_counts(self):
        strong=finding()
        uncertain=finding("capacity_pct",10.0)
        rows=[item("one","db",strong),item("two","api",strong),
              item("three","db",uncertain)]
        score=evaluate_root_rankings(rows)
        self.assertEqual(score["case_count"],3)
        self.assertAlmostEqual(score["top1_accuracy"],1/3)
        self.assertAlmostEqual(score["top3_accuracy"],1/3)
        self.assertAlmostEqual(score["abstention_rate"],1/3)
        self.assertFalse(score["minimum_sample_met"])
        self.assertFalse(score["promotion_authorized"])

    def test_never_infer_unmeasured_false_action_or_cost(self):
        report=evaluate_root_rankings([item("one","db")])
        self.assertIsNone(report["false_action_rate"])
        self.assertIsNone(report["human_override_rate"])
        self.assertIsNone(report["measured_cost_per_incident"])
        self.assertFalse(report["production_evaluation"])

    def test_reject_duplicate_and_untrusted_results(self):
        with self.assertRaisesRegex(RootEvaluationError,"duplicate_case"):
            evaluate_root_rankings([item("one","db"),item("one","api")])
        with self.assertRaisesRegex(RootEvaluationError,"invalid_case"):
            evaluate_root_rankings([{"case_id":"one","expected_service":"db",
                                     "finding":"unverified"}])
        with self.assertRaises(RootEvaluationError):
            evaluate_root_rankings([{"case_id":"one","expected_service":"db",
                                     "finding":finding(),"other":"extra"}])

    def test_minimum_sample_cannot_be_lowered_to_one(self):
        with self.assertRaisesRegex(RootEvaluationError,"invalid_gate"):
            evaluate_root_rankings([item("one","db")],minimum_cases=1)

    def test_top3_scoring_uses_actual_ranked_services(self):
        f=finding()
        multi=IncidentFinding(f.status,f.category,("api","db","web"),
                f.impacted_services,f.evidence_digests,(),f.source_sha,False,False)
        report=evaluate_root_rankings([item("one","db",multi)])
        self.assertEqual(report["top1_accuracy"],0)
        self.assertEqual(report["top3_accuracy"],1)


if __name__=="__main__": unittest.main()
