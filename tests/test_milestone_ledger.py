"""Behavioral negative and positive tests for the offline milestone ledger."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from milestone_ledger import InvalidLedger, validate  # noqa: E402


class MilestoneLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "docs" / "MILESTONE_LEDGER.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.data = copy.deepcopy(self.record)

    def test_current_merged_evidence_and_gates_validate(self):
        result = validate(self.data)
        self.assertGreaterEqual(result["merged_milestones"], 3)
        self.assertGreaterEqual(result["open_gates"], 2)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])

    def test_recent_merges_are_recorded_without_ai9_production_promotion(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertIn(326, records)
        self.assertIn(327, records)
        self.assertEqual(
            records[327]["merge_sha"],
            "5982bd239f7fc083163ce99e24f9bc3e20e75f5d",
        )
        self.assertIn("NOT independent", records[327]["limitations"])
        gate = next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertEqual(gate["source"], "docs/AI9_V3_INDEPENDENT_EVAL_GATE.md")
        self.assertIn("synthetic generator", gate["reason"])
        self.assertIn("labeled incident", gate["next_action"])

    def test_v3_holdout_evaluator_is_recorded_without_claiming_execution(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertEqual(records[328]["merge_sha"], "44380997850387fbc748890075bc3d414792cc6a")
        self.assertEqual(records[329]["merge_sha"], "82bc271d145d374f5f12c4c1517eb936c1826549")
        self.assertIn("NOT RUN", records[329]["limitations"])
        self.assertEqual(records[330]["merge_sha"], "dfc360857ffda586166df03799a6bec4be73486d")
        self.assertIn("no OAuth", records[330]["limitations"])
        gate = next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")
        self.assertEqual(gate["status"], "BLOCKED")
        self.assertIn("ALL_FROZEN_WINDOW_GATES_PASS", gate["reason"])
        self.assertIn("separate owner release decision", gate["next_action"])

    def test_openai_docs_mcp_milestone_is_saved_without_claiming_runtime(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertEqual(records[331]["merge_sha"], "08ca255967a1390888cab7010bb618180e83dba6")
        self.assertEqual(records[332]["merge_sha"], "d412f15894bc5767c86fa0e6261836d1a2b45ddb")
        self.assertIn("NOT VERIFIED", records[332]["limitations"])
        self.assertIn("NOT RUN", records[331]["limitations"])
        self.assertEqual(len(self.data["milestones"]), len(records))
        self.assertEqual(
            next(g for g in self.data["gates"] if g["id"] == "ai9-detection-quality")["status"],
            "BLOCKED",
        )
        self.assertEqual(
            next(g for g in self.data["gates"] if g["id"] == "p01-managed-saas")["status"],
            "BLOCKED",
        )

    def test_pr333_merge_logged_without_mcp_runtime_claim(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        self.assertIn(333, records)
        self.assertEqual(records[333]["pr_head_sha"], "5ccbf6083ffcd72e8ad05b0142d1ffc24c420402")
        self.assertEqual(records[333]["merge_sha"], "89367014e29df1e2f913394f0e2dba39a0ff3d8d")
        self.assertEqual(records[333]["ci_run_id"], 41174724412)
        self.assertIn("CONFIGURATION ONLY", records[333]["limitations"])
        self.assertIn("not_found", records[333]["limitations"])
        gates = {entry["id"]: entry["status"] for entry in self.data["gates"]}
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")

    def test_pr334_336_merges_recorded_without_promoting_blocked_gates(self):
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        expected = {
            334: ("cd7049247d76e248ad9624b080458c1f13d3963b",
                  "104050c066ec165ed3cd71aec738b0d3b96132c8", 41175266360),
            335: ("c6b2bd1034f0ed30199c93818ea5179aa65c67ec",
                  "a7eeafcb88f06f6afac10bf8a9dbd22ad6d22c84", 41189031324),
            336: ("e12a625ce3f1dc2c953f25010cafd709aa1888a2",
                  "23e3cc7eae0d455d3d0e5638835bd67651a3a080", 41189422355),
        }
        for number, (head, merged, ci) in expected.items():
            with self.subTest(pr=number):
                self.assertEqual(records[number]["pr_head_sha"], head)
                self.assertEqual(records[number]["merge_sha"], merged)
                self.assertEqual(records[number]["ci_run_id"], ci)
                self.assertIn("P01", records[number]["limitations"])
        self.assertIn("NOT VERIFIED", records[334]["limitations"])
        self.assertIn("NOT acceptance", records[335]["limitations"])
        self.assertIn("OFFLINE", records[336]["limitations"])
        gates = {gate["id"]: gate["status"] for gate in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")

    def test_pr337_338_evidence_logged_without_codex_runtime_claim(self):
        entries = {item["pr_number"]: item for item in self.data["milestones"]}
        expected = {
            337: ("0703694b7987bbe2ca0c45c149651535f9fed927",
                  "f1bd3c5717d95a9ee89116c0fce49ef9fac572d7", 41189673147),
            338: ("65a0cd7032043d167edf009699e1b88bc3c32ab0",
                  "304665cbfb1576427f3ff74e0a946762f38906b7", 41190379411),
        }
        for number, (head, merged, ci) in expected.items():
            with self.subTest(pr=number):
                self.assertEqual(entries[number]["pr_head_sha"], head)
                self.assertEqual(entries[number]["merge_sha"], merged)
                self.assertEqual(entries[number]["ci_run_id"], ci)
                self.assertIn("BLOCKED", entries[number]["limitations"])
        self.assertIn("NOT verified executing Codex runtime", entries[338]["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr339_340_recorded_with_offline_only_p01_t09(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        expected = {
            339: ("4dcbf9e7b1c53d59ba0e7d5763e4abfefd217744",
                  "6024fa2eda44e9e207d6c59c5f5e21723af197c8", 41190651115),
            340: ("059a9a17ed12d6b1c1cb02cf1146d7c96ea0d88f",
                  "166177abb5144b4115d8d72a309daadf73d2b227", 41191053107),
        }
        for number, (head, merged, ci) in expected.items():
            with self.subTest(pr=number):
                self.assertEqual(records[number]["pr_head_sha"], head)
                self.assertEqual(records[number]["merge_sha"], merged)
                self.assertEqual(records[number]["ci_run_id"], ci)
                self.assertIn("P01", records[number]["limitations"])
        self.assertIn("3 passed/0 failed", records[340]["verification"])
        self.assertIn("NOT a live P01", records[340]["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr341_verified_merge_recorded_without_advancing_p01(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[341]
        self.assertEqual(entry["pr_head_sha"], "34bf13ba8a76345193bfa3aa7e418654242e50cb")
        self.assertEqual(entry["merge_sha"], "c23965d439ebc6c82d91ba213888df83f050cdf4")
        self.assertEqual(entry["ci_run_id"], 41191357480)
        self.assertIn("41191496396 SUCCESS", entry["verification"])
        self.assertIn("NOT approved hosted SaaS", entry["limitations"])
        gates = {g["id"]: g["status"] for g in self.data["gates"]}
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr342_345_exact_merges_are_recorded_without_gate_promotion(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        expected = {
            342: ("aa6d90556353423290b52e5032e5d5dbd8e3ed2e",
                  "b741d4b29e39e99de4f6fb29e7ed1fc7aed06940", 41191958371, 41192337652),
            343: ("b759d9d1164ffb03baf03cf702ff417bc86a3e36",
                  "24d71c753354f452ea5239aa659b8d94bedcad8e", 41192715097, 41192806183),
            344: ("694c4e2612393508ca616a13b91c4219d81e9a62",
                  "552bc49c5c9add27ab38552f36a45a73b311dd23", 41342999772, 41343195262),
            345: ("324db74a0429404067f318772a4cce1938c3607d",
                  "26f8adcbae62aab0cbd6bd24a692c8c443c3619b", 41344032855, 41344203872),
        }
        for number, (head, merged, ci, main_ci) in expected.items():
            with self.subTest(pr=number):
                self.assertEqual(records[number]["pr_head_sha"], head)
                self.assertEqual(records[number]["merge_sha"], merged)
                self.assertEqual(records[number]["ci_run_id"], ci)
                self.assertIn("VERIFIED", records[number]["verification"])
                self.assertIn(
                    f"main ci {main_ci} success".lower(),
                    records[number]["verification"].lower(),
                )
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr346_merge_is_recorded_without_advancing_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 346)
        self.assertEqual(entry["pr_head_sha"], "1645df5c149323f250d68830123907ff2bbe8242")
        self.assertEqual(entry["merge_sha"], "e5bfd3e46a44e8946056b1040d8043f3a22f4b23")
        self.assertEqual(entry["ci_run_id"], 41350441454)
        self.assertIn("Main CI 41350693382 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr347_merge_records_pr_preview_limit_and_main_success_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 347)
        self.assertEqual(entry["pr_head_sha"], "8d8c59d38b3509bd80a5055053f36bb43df1ece3")
        self.assertEqual(entry["merge_sha"], "de11d125f0146b627a220683df8143d8dc0b01f1")
        self.assertEqual(entry["ci_run_id"], 41350908437)
        self.assertIn("41352023746 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41352024004 SUCCESS", entry["verification"])
        self.assertIn("Deployment rate limited", entry["verification"])
        self.assertIn("Vercel status SUCCESS", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr348_merge_records_vercel_rate_limit_and_main_success_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 348)
        self.assertEqual(entry["pr_head_sha"], "2e690c1bba30da70aa5ece696a056a95829764eb")
        self.assertEqual(entry["merge_sha"], "2639aad5f62ba1cb0b0192ad25d8853f6828023e")
        self.assertEqual(entry["ci_run_id"], 41352262112)
        self.assertIn("41352504016 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41352503961 SUCCESS", entry["verification"])
        self.assertIn("PR-preview Vercel failed", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr349_merge_records_exact_checks_and_vercel_limit_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 349)
        self.assertEqual(entry["pr_head_sha"], "d4ffaf9423fd98c61f12bdaed997dbb1bb621288")
        self.assertEqual(entry["merge_sha"], "f8e55d71ef194f5abb729dcf179ebb647eafe43b")
        self.assertEqual(entry["ci_run_id"], 41352723960)
        self.assertIn("41352718980", entry["verification"])
        self.assertIn("41352831133 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41352830537 SUCCESS", entry["verification"])
        self.assertIn("Deployment rate limited", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr350_merge_records_main_success_and_preserves_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 350)
        self.assertEqual(entry["pr_head_sha"], "d7d6a206c4fbc56d3ecb76458a423a2b4bb599b9")
        self.assertEqual(entry["merge_sha"], "1b32f0ffdfbbaacd60207be995d34f2b88d271d4")
        self.assertEqual(entry["ci_run_id"], 41353064599)
        self.assertIn("41353053027", entry["verification"])
        self.assertIn("41353315577 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41353315286 SUCCESS", entry["verification"])
        self.assertIn("Vercel status SUCCESS", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr351_merge_records_main_success_and_preserves_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 351)
        self.assertEqual(entry["pr_head_sha"], "7d71fc6a8a151db61f652d4bdce38ceb5c3ae240")
        self.assertEqual(entry["merge_sha"], "a30dbeae08d54edbbff7c6790f7e59a6cd47bb14")
        self.assertEqual(entry["ci_run_id"], 41353541830)
        self.assertIn("41353531301", entry["verification"])
        self.assertIn("41354155904 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41354155804 SUCCESS", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr352_merge_records_main_and_vercel_success_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 352)
        self.assertEqual(entry["pr_head_sha"], "5d5b76ef3d71a2f170e26c86a18730ff98f59987")
        self.assertEqual(entry["merge_sha"], "113b6f38ec59ece59a14fd9ccd83cd7c3422271c")
        self.assertEqual(entry["ci_run_id"], 41354331045)
        self.assertIn("41354320212", entry["verification"])
        self.assertIn("41354676094 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41354675758 SUCCESS", entry["verification"])
        self.assertIn("Vercel status SUCCESS", entry["verification"])
        self.assertIn("PR-preview Vercel failed", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr353_merge_records_main_success_and_vercel_limit_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 353)
        self.assertEqual(entry["pr_head_sha"], "3e3ee8299ff1696490923afe3dca36a3d92e53d5")
        self.assertEqual(entry["merge_sha"], "7e319266732de316f6aefd7da766b1d782414371")
        self.assertEqual(entry["ci_run_id"], 41354828751)
        self.assertIn("41354819966", entry["verification"])
        self.assertIn("41354957688 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41354957156 SUCCESS", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        self.assertIn("model inference skipped", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr354_merge_records_main_success_and_preserves_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 354)
        self.assertEqual(entry["pr_head_sha"], "7a174ee4658a8d1375b24ce60280cfd9d882bf17")
        self.assertEqual(entry["merge_sha"], "122f23149c15da6d855b7606dd1eba3161b804d9")
        self.assertEqual(entry["ci_run_id"], 41355180888)
        self.assertIn("41355170895", entry["verification"])
        self.assertIn("41355453787 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41355453093 SUCCESS", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr355_merge_records_main_and_vercel_success_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 355)
        self.assertEqual(entry["pr_head_sha"], "c33f284e2267e17e25aef78f8c1a1c16f05b9b27")
        self.assertEqual(entry["merge_sha"], "9dfdc9ccb12525165dfa34a0c3f4b75c51830a65")
        self.assertEqual(entry["ci_run_id"], 41355833192)
        self.assertIn("41355820779", entry["verification"])
        self.assertIn("41356132745 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41356132195 SUCCESS", entry["verification"])
        self.assertIn("Vercel status SUCCESS", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr356_merge_records_main_success_and_vercel_limit_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 356)
        self.assertEqual(entry["pr_head_sha"], "faf873cdaa5ee2bcaa6a2ac6b105f9186adb799d")
        self.assertEqual(entry["merge_sha"], "e5af2aebef15d2cd6587406e0f49f9f28c824feb")
        self.assertEqual(entry["ci_run_id"], 41356339944)
        self.assertIn("41356329310", entry["verification"])
        self.assertIn("41356533259 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41356533488 SUCCESS", entry["verification"])
        self.assertIn("Vercel status remained FAILURE", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr358_merge_records_frozen_holdout_result_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 358)
        self.assertEqual(entry["pr_head_sha"], "8ac1ce8be2218946c87a97c5105ec57cc49b49fb")
        self.assertEqual(entry["merge_sha"], "3eb987a85c2d85071ad760b205e6f5c84a3ab586")
        self.assertEqual(entry["ci_run_id"], 41359194103)
        self.assertIn("ALL_FROZEN_WINDOW_GATES_PASS", entry["verification"])
        self.assertIn("41359222608", entry["verification"])
        self.assertIn("41359229242", entry["verification"])
        self.assertIn("41359551458 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41359550746 SUCCESS", entry["verification"])
        self.assertIn("not real incident labels", entry["limitations"])
        self.assertIn("must never be rerun", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr359_merge_records_v358_readiness_sync_and_vercel_limit(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 359)
        self.assertEqual(entry["pr_head_sha"], "841bac90be6ac46ef31463de54a884eca7a79c08")
        self.assertEqual(entry["merge_sha"], "4ec87730f0eb768c7ebe7757a77631279004df2a")
        self.assertEqual(entry["ci_run_id"], 41359976109)
        self.assertIn("41359959860 SUCCESS", entry["verification"])
        self.assertIn("41360103112 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41360102509 SUCCESS", entry["verification"])
        self.assertIn("rate-limited", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr360_merge_records_v359_readiness_sync_and_preserves_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 360)
        self.assertEqual(entry["pr_head_sha"], "b0796873b1d5916266a7cf88c6bfaddf8b2c9e6c")
        self.assertEqual(entry["merge_sha"], "3cc934e3199d1abed5366c92b17eeeff9be77d8f")
        self.assertEqual(entry["ci_run_id"], 41360357480)
        self.assertIn("41360344522 SUCCESS", entry["verification"])
        self.assertIn("41360454373 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41360454062 SUCCESS", entry["verification"])
        self.assertIn("rate-limited", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr361_merge_records_v360_readiness_sync_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 361)
        self.assertEqual(entry["pr_head_sha"], "c85fed83cbeee6cdb1fbee8dba50301765a1a888")
        self.assertEqual(entry["merge_sha"], "0147224f9177fb956e5ff58fea8df242dbbd7d4a")
        self.assertEqual(entry["ci_run_id"], 41360658237)
        self.assertIn("41360645854 SUCCESS", entry["verification"])
        self.assertIn("41360789146 SUCCESS", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("41360789202 SUCCESS", entry["verification"])
        self.assertIn("Vercel failed on the PR preview", entry["verification"])
        self.assertIn("Vercel on the merge SHA succeeded", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr362_merge_records_v361_sync_without_gate_promotion(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 362)
        self.assertEqual(entry["pr_head_sha"], "be9f716a7181dc5a005db33267f5aa316d4388b2")
        self.assertEqual(entry["merge_sha"], "916d511665370b8533ff502c68e71b5e12fcf24b")
        self.assertEqual(entry["ci_run_id"], 41361116522)
        self.assertIn("41361102359 SUCCESS", entry["verification"])
        self.assertIn("Node tests", entry["verification"])
        self.assertIn("41361229621 SUCCESS", entry["verification"])
        self.assertIn("41361228767 SUCCESS", entry["verification"])
        self.assertIn("Pages publish", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("Vercel failed", entry["verification"])
        self.assertIn("Vercel was rate-limited", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr363_merge_records_main_success_and_preserves_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 363)
        self.assertEqual(entry["pr_head_sha"], "79f8eb9793b1acd541bd39cdd71c637989a95085")
        self.assertEqual(entry["merge_sha"], "2eeb5298dd846c236c4a825cc739874bd2d067e6")
        self.assertEqual(entry["ci_run_id"], 41361488020)
        self.assertIn("41361474917 SUCCESS", entry["verification"])
        self.assertIn("41361625894 SUCCESS", entry["verification"])
        self.assertIn("41361625560 SUCCESS", entry["verification"])
        self.assertIn("Vercel failed", entry["verification"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr364_merge_record_matches_ci_and_preserves_readiness_gates(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], self.data["milestones"][-1]["pr_number"])
        entry = next(item for item in self.data["milestones"] if item["pr_number"] == 364)
        self.assertEqual(entry["pr_head_sha"], "87d289e1ee5134734a157a51b0302907b40f2400")
        self.assertEqual(entry["merge_sha"], "baa4db24dc4bebf364410cd6790dba6d4e0b1fea")
        self.assertEqual(entry["ci_run_id"], 41362939397)
        self.assertIn("41362934702 SUCCESS", entry["verification"])
        self.assertIn("41363048571 SUCCESS", entry["verification"])
        self.assertIn("41363048181 SUCCESS", entry["verification"])
        self.assertIn("Pages publish", entry["verification"])
        self.assertIn("verify-production", entry["verification"])
        self.assertIn("Vercel PR check failed", entry["verification"])
        self.assertIn("No external dataset", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr365_to_404_merges_are_recorded_without_promoting_readiness_gates(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        expected = {
            365: ("bf1d158dee28a9b8a00bfc0c29e847b7398867e6",
                  "28a633d391311b36cb64fcb3ec528e7363f07ad9", 41363442004),
            366: ("394420e38c95fcc2f24562fe6c6158dcc3275e6f",
                  "c56c7f60315f9ce6c2d400ef51f6045e1b8260a3", 41423657947),
            367: ("a54f0afdcba16e3613ec28f96e8dc7e81230cd90",
                  "cdd8cdc8c8dca7d36a660af41f00b175b694dfce", 41404954163),
            368: ("01a0babf679c24cfcdffb428ec0b2ee52deb2fc3",
                  "520b77fdfc07ffcb1d8ac3c2776333abc485b852", 41422995159),
            369: ("0e08c376f872fd664b8c3807a4ea0a66d4d26fbc",
                  "2eaa12511e45056a4bac4e26c454871d7b43b001", 41424695607),
            371: ("7b07a42017ec3a53e2b6d48fee220f4af464918c",
                  "323413a36f0446dc4013eec302bef189c5061bf2", 41426781794),
            372: ("6b0e4a6c4754685aaccab821fdd8c7171e68d35d",
                  "e3526ffb934216af5301e16c5e7f1bcf60355042", 41427744524),
            373: ("16bfde9401d8e074db47a5e99964486468d684a0",
                  "4d61ff2e49f1d8b28d0bd11267ff425b861639e0", 41428670992),
            374: ("cd96da7bf5ba4d529bfff6bc37aa54cf2a3bc746",
                  "0988a5e58f7b8dba7066eb0b9079539e6d0b58a5", 41429418945),
            375: ("a86510564f01c9b4ef10a180cea063f3df6782c8",
                  "c5e25db806500429ac7d5b83b663eb2a566151e1", 41430830200),
            376: ("cc4f4d64c686cd8198ae3509c57defea3427f60e",
                  "bfd40df4f3ae9ceb0c539c3ed6861c24c88e6aee", 41431843697),
            377: ("9e32035d5bf7b94c8cfd7b15384db8e4c3559024",
                  "34b47f1352e489d9a92b2e202441a8469d66fabb", 41432899091),
            378: ("288ccde0a977d809ab6df4324d4e399fb126ece0",
                  "0c6f143faffdbee7b66d9661ee3534b513051f5c", 41440593177),
            379: ("bb5c6cb3a1243720e952b8211cc4604a68896460",
                  "b3a308accc23dec7b7da91c9e48e40fb8e7dc0ac", 41441685660),
            380: ("139b4ae89e745629e0e407393134d6195be5f43c",
                  "c3180f5a5e945dbf16e32f50a25041233596035a", 41442978965),
            381: ("53b07327baea2b0c085ea8d41ee0af2f426aa217",
                  "3fd878eda52ef480764894a4ae82cd8af0570af2", 41443937104),
            383: ("55688ec572c07e54a97677b19831311f0f2c3403",
                  "47073379e27bba6a9009c39bd5799a3000e5280f", 41448277637),
            384: ("38d37eb6cce47f59959f39e5b333960bab6f8ac7",
                  "1319797525567c3e3a2b4ffbea14a80bc651524e", 41450789386),
            385: ("3982e1bc7baefad5ab6c78d3e70abd4cdb53361d",
                  "d5fa0a08f1d99ca074f4ee91c145121f8f5c0b59", 41451743622),
            386: ("4c4b040ae4480fb7a8d64ddf9da88c429ac5df00",
                  "e4a9d002b0fa21271db8f2ffa44e3f8d5854ae08", 41453461558),
            387: ("82ad683072c981705cbe9fc3471c26ffea9afd0b",
                  "c82e4db2a9b82dbb01b0636d2b90ab836041e203", 41454746336),
            388: ("732028acf4138b6c1d30805e9361fcd53f40ecb0",
                  "7cb400b5d90c2935c98e76aad7c5335a77aa48b5", 41456679101),
            389: ("b42a5f0b280491c3ef064b48ea6e3476f2d6191a",
                  "27349fcdb9f3753a7bc686dd2177795ef005014d", 41459188955),
            390: ("08e03201d85ddeeccd10b00bcebede31da06dd69",
                  "2346d5006d8f602f42d3e17e11e0cf296d8ece05", 41461221768),
            391: ("6369846a872942d56731a68301747006e0956c73",
                  "230468f345f1426852a229565f9dde801cf0100f", 41466736255),
            392: ("7373feedd193e9aa498c3eb4d77bce8f19657a9b",
                  "0688f3aad663d5a5be7bb5d72dce28966a2c781e", 41474580125),
            393: ("1813e4645b179812c3f7be4c8f2f95f47e3cdc87",
                  "dda0d28c036e90af236596e377a8299762638a46", 41480022731),
        }
        for number, (head, merged, ci) in expected.items():
            with self.subTest(pr=number):
                self.assertEqual(records[number]["pr_head_sha"], head)
                self.assertEqual(records[number]["merge_sha"], merged)
                self.assertEqual(records[number]["ci_run_id"], ci)
                self.assertIn("SUCCESS", records[number]["verification"])
                self.assertIn("BLOCKED", records[number]["limitations"])
        self.assertEqual(
            validate(self.data)["latest_pr"],
            self.data["milestones"][-1]["pr_number"],
        )
        self.assertIn("main CI 41425006983", records[369]["verification"])
        self.assertIn("41425006913 SUCCESS", records[369]["verification"])
        self.assertIn("Vercel status failed", records[369]["verification"])
        self.assertIn("Main CI 41427215538", records[371]["verification"])
        self.assertIn("41427213176 SUCCESS", records[371]["verification"])
        self.assertIn("not a signature", records[371]["limitations"])
        self.assertIn("Main CI 41428246481", records[372]["verification"])
        self.assertIn("41428244774 SUCCESS", records[372]["verification"])
        self.assertIn("Vercel check on the PR failed", records[372]["verification"])
        self.assertIn("Main CI 41429076464", records[373]["verification"])
        self.assertIn("41429076168 SUCCESS", records[373]["verification"])
        self.assertIn("Vercel check on the PR failed", records[373]["verification"])
        self.assertIn("Main CI 41429682676", records[374]["verification"])
        self.assertIn("41429681653 SUCCESS", records[374]["verification"])
        self.assertIn("Vercel check failed due to its build-rate limit", records[374]["verification"])
        self.assertIn("Main CI 41431148732", records[375]["verification"])
        self.assertIn("41431147710 SUCCESS", records[375]["verification"])
        self.assertIn("Vercel PR status failed", records[375]["verification"])
        self.assertIn("Main CI 41431998816", records[376]["verification"])
        self.assertIn("41431997968 SUCCESS", records[376]["verification"])
        self.assertIn("Vercel PR status failed", records[376]["verification"])
        self.assertIn("Main CI 41433070130", records[377]["verification"])
        self.assertIn("41433069213 SUCCESS", records[377]["verification"])
        self.assertIn("41432872907 SUCCESS", records[377]["verification"])
        self.assertIn("PR Vercel preview", records[377]["limitations"])
        self.assertIn("budget approval was absent", records[377]["limitations"])
        self.assertIn("Main CI 41441026324", records[378]["verification"])
        self.assertIn("41441024464 SUCCESS", records[378]["verification"])
        self.assertIn("41440575417 SUCCESS", records[378]["verification"])
        self.assertIn("not signatures", records[378]["limitations"])
        self.assertIn("Main CI 41442122329", records[379]["verification"])
        self.assertIn("41442121820 SUCCESS", records[379]["verification"])
        self.assertIn("41441676086 SUCCESS", records[379]["verification"])
        self.assertIn("do not authenticate writers", records[379]["limitations"])
        self.assertIn(
            "PR CI 41442989473 and exact-head push CI 41442978965 SUCCESS",
            records[380]["verification"],
        )
        self.assertIn("41442982971 SUCCESS", records[380]["verification"])
        self.assertIn("41443266347", records[380]["verification"])
        self.assertIn("41443266003 SUCCESS", records[380]["verification"])
        self.assertIn("not authenticate key enrollment", records[380]["limitations"])
        self.assertIn("41443912233 SUCCESS", records[381]["verification"])
        self.assertIn("41443932175 SUCCESS", records[381]["verification"])
        self.assertIn("41444390758", records[381]["verification"])
        self.assertIn("41444390296 SUCCESS", records[381]["verification"])
        self.assertIn("does not authenticate the producer", records[381]["limitations"])
        self.assertIn("41446366516 SUCCESS", records[383]["verification"])
        self.assertIn("41446390406 SUCCESS", records[383]["verification"])
        self.assertIn("41448275676 SUCCESS", records[383]["verification"])
        self.assertIn("rate-limited", records[383]["verification"])
        self.assertIn("do not authenticate telemetry producers", records[383]["limitations"])
        self.assertIn("41450117574 SUCCESS", records[384]["verification"])
        self.assertIn("41450140512 SUCCESS", records[384]["verification"])
        self.assertIn("41450788131 SUCCESS", records[384]["verification"])
        self.assertIn("rate-limited", records[384]["verification"])
        self.assertIn("do not authenticate an external source", records[384]["limitations"])
        self.assertIn("41451717572 SUCCESS", records[385]["verification"])
        self.assertIn("41451739116 SUCCESS", records[385]["verification"])
        self.assertIn("41452380746 SUCCESS", records[385]["verification"])
        self.assertIn("41452379582 SUCCESS", records[385]["verification"])
        self.assertIn("rate-limited", records[385]["verification"])
        self.assertIn("no real incident data", records[385]["limitations"])
        self.assertIn("41453419441 SUCCESS", records[386]["verification"])
        self.assertIn("41453454978 SUCCESS", records[386]["verification"])
        self.assertIn("41453945952 SUCCESS", records[386]["verification"])
        self.assertIn("41453945090 SUCCESS", records[386]["verification"])
        self.assertIn("rate-limited", records[386]["verification"])
        self.assertIn("privileged writer", records[386]["limitations"])
        self.assertIn("41454710164 SUCCESS", records[387]["verification"])
        self.assertIn("41454741109 SUCCESS", records[387]["verification"])
        self.assertIn("41455742840", records[387]["verification"])
        self.assertIn("41455742285 SUCCESS", records[387]["verification"])
        self.assertIn("failed due to its build-rate limit", records[387]["verification"])
        self.assertIn("unsigned", records[387]["limitations"])
        self.assertIn("41456657796 SUCCESS", records[388]["verification"])
        self.assertIn("41456674077 SUCCESS", records[388]["verification"])
        self.assertIn("41457678227", records[388]["verification"])
        self.assertIn("41457676053 SUCCESS", records[388]["verification"])
        self.assertIn("static Pages publication", records[388]["verification"])
        self.assertIn("unsigned", records[388]["limitations"])
        self.assertIn("41466709183 SUCCESS", records[391]["verification"])
        self.assertIn("41466731548 SUCCESS", records[391]["verification"])
        self.assertIn("41470834569", records[391]["verification"])
        self.assertIn("41470832717 SUCCESS", records[391]["verification"])
        self.assertIn("verify-production", records[391]["verification"])
        self.assertIn("41474547278 SUCCESS", records[392]["verification"])
        self.assertIn("41474575499 SUCCESS", records[392]["verification"])
        self.assertIn("41475266103", records[392]["verification"])
        self.assertIn("41475263029 SUCCESS", records[392]["verification"])
        self.assertIn("model inference skipped", records[392]["limitations"])
        self.assertIn("41479978302 SUCCESS", records[393]["verification"])
        self.assertIn("41480018267 SUCCESS", records[393]["verification"])
        self.assertIn("41483738977", records[393]["verification"])
        self.assertIn("41483734733 SUCCESS", records[393]["verification"])
        self.assertIn("no AI call", records[393]["limitations"])
        self.assertEqual(records[394]["merge_sha"], "f3dc921ed8ea8de150582567763405dbcfc34746")
        self.assertIn("41485437158 SUCCESS", records[394]["verification"])
        self.assertIn("41485462136 SUCCESS", records[394]["verification"])
        self.assertIn("41491251830", records[394]["verification"])
        self.assertIn("41491251634 SUCCESS", records[394]["verification"])
        self.assertIn("owner-provided UI screenshots", records[394]["limitations"])
        self.assertIn("AI-9 remains FAIL/BLOCKED", records[394]["limitations"])
        self.assertEqual(records[395]["pr_head_sha"], "8370ca19e49e567afa853013cfbee4f615394d87")
        self.assertEqual(records[395]["merge_sha"], "bbadef10ab7f49f5136f50b331440dac4b3bc2d4")
        self.assertEqual(records[395]["ci_run_id"], 41492474753)
        self.assertIn("41492448493 SUCCESS", records[395]["verification"])
        self.assertIn("41492469681 SUCCESS", records[395]["verification"])
        self.assertIn("41493063624", records[395]["verification"])
        self.assertIn("41493062782 SUCCESS", records[395]["verification"])
        self.assertIn("Static Pages is not P01 staging", records[395]["limitations"])
        self.assertIn("AI-9 remains FAIL/BLOCKED", records[395]["limitations"])
        self.assertEqual(records[396]["pr_head_sha"], "3ce710dd1f4da014c26cd3a4d996fabb87b39f00")
        self.assertEqual(records[396]["merge_sha"], "5944b4ac44d42c507ace0b4a468b210636733033")
        self.assertEqual(records[396]["ci_run_id"], 41494074797)
        self.assertIn("41494031457 SUCCESS", records[396]["verification"])
        self.assertIn("41494069977 SUCCESS", records[396]["verification"])
        self.assertIn("41495057209", records[396]["verification"])
        self.assertIn("41495055337 SUCCESS", records[396]["verification"])
        self.assertIn("Vercel PR preview failed due to deployment rate limit", records[396]["verification"])
        self.assertIn("AI-9 remains FAIL/BLOCKED", records[396]["limitations"])
        self.assertEqual(records[397]["pr_head_sha"], "f869f2d525c8b5a79cf2eb28b79ea20977e045b7")
        self.assertEqual(records[397]["merge_sha"], "9ba9901d9b558bbc6bb45f7ebb661a03028a1c9c")
        self.assertEqual(records[397]["ci_run_id"], 41495991816)
        self.assertIn("41495950385 SUCCESS", records[397]["verification"])
        self.assertIn("41495988647 SUCCESS", records[397]["verification"])
        self.assertIn("41496604409", records[397]["verification"])
        self.assertIn("41496602621 SUCCESS", records[397]["verification"])
        self.assertIn("AI-9 remains FAIL/BLOCKED", records[397]["limitations"])
        self.assertEqual(records[398]["pr_head_sha"], "118cdcc9ababd083bcb97ead0371c15542117039")
        self.assertEqual(records[398]["merge_sha"], "be326c48dda67b8d918bf949933271c5a0e3282e")
        self.assertEqual(records[398]["ci_run_id"], 41497085256)
        self.assertIn("41497038530 SUCCESS", records[398]["verification"])
        self.assertIn("41497081182 SUCCESS", records[398]["verification"])
        self.assertIn("41499273400", records[398]["verification"])
        self.assertIn("41499272034 SUCCESS", records[398]["verification"])
        self.assertIn("AI-9 remains FAIL/BLOCKED", records[398]["limitations"])
        self.assertEqual(records[399]["pr_head_sha"], "5336966db4eae9696993539de6ea8ae6d378a643")
        self.assertEqual(records[399]["merge_sha"], "766c590746736c5698648f67d8d90d00b17b7e6f")
        self.assertEqual(records[399]["ci_run_id"], 41501346453)
        self.assertIn("41501299721 SUCCESS", records[399]["verification"])
        self.assertIn("41501363549 SUCCESS", records[399]["verification"])
        self.assertIn("41501791942", records[399]["verification"])
        self.assertIn("41501792008 SUCCESS", records[399]["verification"])
        self.assertIn("does not prove model inference", records[399]["limitations"])
        self.assertEqual(records[400]["pr_head_sha"], "7d971f8e096d99ba8e9954d82e898941b9ce3eb5")
        self.assertEqual(records[400]["merge_sha"], "38a061a611382758af2eaebe900e572890989fc9")
        self.assertEqual(records[400]["ci_run_id"], 41502955578)
        self.assertIn("41502910321 SUCCESS", records[400]["verification"])
        self.assertIn("41502951679 SUCCESS", records[400]["verification"])
        self.assertIn("41503251534", records[400]["verification"])
        self.assertIn("41503250514 SUCCESS", records[400]["verification"])
        self.assertIn("does not prove upstream ingress byte limits", records[400]["limitations"])
        self.assertEqual(records[401]["pr_head_sha"], "f6ac6b24b06f090d89ea5d4878a6c7b6b9928152")
        self.assertEqual(records[401]["merge_sha"], "d252a97956ccc006e85fc365f081ed85962cb1b4")
        self.assertEqual(records[401]["ci_run_id"], 41504278801)
        self.assertIn("41504315999", records[401]["verification"])
        self.assertIn("41504309819", records[401]["verification"])
        self.assertIn("41504487437", records[401]["verification"])
        self.assertIn("41504484442", records[401]["verification"])
        self.assertEqual(records[402]["pr_head_sha"], "413ea70419ee6b1e032f0f313d7db1f61fb52c24")
        self.assertEqual(records[402]["merge_sha"], "8587d266dcb51bd2c4fe48930f61378c22e3156c")
        self.assertEqual(records[402]["ci_run_id"], 41506046290)
        self.assertIn("41506089460", records[402]["verification"])
        self.assertIn("41506084748", records[402]["verification"])
        self.assertIn("41506588415", records[402]["verification"])
        self.assertIn("41506586886", records[402]["verification"])
        self.assertIn("preview rate limit did not affect required checks", records[402]["limitations"])
        self.assertEqual(records[403]["pr_head_sha"], "6c3fd25e0cf3d081ede701abfbf29bc45e1137a2")
        self.assertEqual(records[403]["merge_sha"], "b2370a6dd31d91f228be3370c0c9fdb1a6cc5d3a")
        self.assertEqual(records[403]["ci_run_id"], 41509295468)
        self.assertIn("41509245579", records[403]["verification"])
        self.assertIn("41509288062", records[403]["verification"])
        self.assertIn("41509946685", records[403]["verification"])
        self.assertIn("41509945914", records[403]["verification"])
        self.assertIn("process memory", records[403]["limitations"])
        self.assertEqual(records[404]["pr_head_sha"], "d5e4c5f15d0ef109812b7ecdeeee82011c4db244")
        self.assertEqual(records[404]["merge_sha"], "3c7caeeb9ce4262580a1ca9a17224a0cace3e370")
        self.assertEqual(records[404]["ci_run_id"], 41512457878)
        self.assertIn("41512495321", records[404]["verification"])
        self.assertIn("41512490550", records[404]["verification"])
        self.assertIn("41513967517", records[404]["verification"])
        self.assertIn("41513966193", records[404]["verification"])
        self.assertIn("owner approval", records[404]["limitations"])
        self.assertIn("41459163558 SUCCESS", records[389]["verification"])
        self.assertIn("41459181626 SUCCESS", records[389]["verification"])
        self.assertIn("41459888214", records[389]["verification"])
        self.assertIn("41459887605 SUCCESS", records[389]["verification"])
        self.assertIn("T34 is still open", records[389]["limitations"])
        self.assertIn("41461187596 SUCCESS", records[390]["verification"])
        self.assertIn("41461214931 SUCCESS", records[390]["verification"])
        self.assertIn("41463879043", records[390]["verification"])
        self.assertIn("41463878344 SUCCESS", records[390]["verification"])
        self.assertIn("static Pages publication", records[390]["verification"])
        self.assertIn("Node tests and controlled incident drill were skipped", records[390]["verification"])
        self.assertIn("does not prevent another process", records[390]["limitations"])
        self.assertIn("AI-9 remains BLOCKED/FAIL", records[390]["limitations"])
        self.assertEqual(validate(self.data)["latest_pr"], self.data["milestones"][-1]["pr_number"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr407_merge_is_recorded_with_post_merge_evidence_and_unchanged_gates(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[407]
        self.assertEqual(entry["pr_head_sha"], "ea5108c7855ebb2e4502d89c6b558dbed5aa9da5")
        self.assertEqual(entry["merge_sha"], "437200597912e5d6f92cf7f9e6aad679b40b0e33")
        self.assertEqual(entry["ci_run_id"], 41520175435)
        self.assertIn("41520203368 SUCCESS", entry["verification"])
        self.assertIn("41520195858 SUCCESS", entry["verification"])
        self.assertIn("41520608784", entry["verification"])
        self.assertIn("41520607823 SUCCESS", entry["verification"])
        self.assertIn("skipped Codex inference", entry["verification"])
        self.assertIn("synthetic, unreviewed fixture", entry["limitations"])
        self.assertIn("Gate dispositions did not change", entry["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr408_merge_records_ci_codeql_and_static_site_evidence(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[408]
        self.assertEqual(entry["pr_head_sha"], "5fbf3f6578e0c9bbcc6a42190d467872199d0095")
        self.assertEqual(entry["merge_sha"], "8d4c1875aafb321f4b6a874ac748e6cae471f0eb")
        self.assertEqual(entry["ci_run_id"], 41616589063)
        self.assertIn("41616565301 SUCCESS", entry["verification"])
        self.assertIn("41616583002 SUCCESS", entry["verification"])
        self.assertIn("41617030405", entry["verification"])
        self.assertIn("41617028662 SUCCESS", entry["verification"])
        self.assertIn("Codex inference was skipped", entry["verification"])
        self.assertIn("five deterministic synthetic cases", entry["limitations"])
        self.assertIn("Gate dispositions did not change", entry["limitations"])

    def test_pr409_merge_records_ci_codeql_and_limited_metric_evidence(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[409]
        self.assertEqual(entry["pr_head_sha"], "2c9bfe18061b6aea698623ac8152c7c7ee3bca36")
        self.assertEqual(entry["merge_sha"], "2fae0241c4fda8103e76cb5f05583244b568c819")
        self.assertEqual(entry["ci_run_id"], 41618050928)
        self.assertIn("41618026517 SUCCESS", entry["verification"])
        self.assertIn("41618046825 SUCCESS", entry["verification"])
        self.assertIn("41618477420", entry["verification"])
        self.assertIn("41618476461 SUCCESS", entry["verification"])
        self.assertIn("Codex model-review step was skipped", entry["verification"])
        self.assertIn("five synthetic, unreviewed cases", entry["limitations"])
        self.assertIn("not a general safe-refusal rate", entry["limitations"])

    def test_pr410_merge_records_insufficient_metric_ci_and_synthetic_scope(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[410]
        self.assertEqual(
            entry["title"],
            "Measure abstention on explicitly labeled insufficient-evidence cases",
        )
        self.assertEqual(entry["pr_head_sha"], "470f02f5d9d1c5a08e806d598ec1179f6b34f8a9")
        self.assertEqual(entry["merge_sha"], "138fa5423e5aef705c8f8be99fbae51bf5e546bb")
        self.assertEqual(entry["ci_run_id"], 41619952990)
        self.assertIn("41619914219 SUCCESS", entry["verification"])
        self.assertIn("41619947629 SUCCESS", entry["verification"])
        self.assertIn("41620390423", entry["verification"])
        self.assertIn("41620389693 SUCCESS", entry["verification"])
        self.assertIn("Codex model-review step was skipped", entry["verification"])
        self.assertIn("one explicitly labeled insufficient case", entry["limitations"])
        self.assertIn("Gate dispositions did not change", entry["limitations"])

    def test_pr411_merge_records_sufficient_metric_ci_and_synthetic_scope(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[411]
        self.assertEqual(
            entry["title"],
            "Add sufficient-evidence abstention rate to offline synthetic scorecard",
        )
        self.assertEqual(entry["pr_head_sha"], "db7592d93b674f12d56b338c80494790ba965020")
        self.assertEqual(entry["merge_sha"], "5c8cb05d12560d9771769fbf7a157df056e91934")
        self.assertEqual(entry["ci_run_id"], 41626407724)
        self.assertIn("41626384456 SUCCESS", entry["verification"])
        self.assertIn("41626404076 SUCCESS", entry["verification"])
        self.assertIn("41626783764", entry["verification"])
        self.assertIn("41626782537 SUCCESS", entry["verification"])
        self.assertIn("Codex model-review step was skipped", entry["verification"])
        self.assertIn("four synthetic, unreviewed labels", entry["limitations"])
        self.assertIn("Gate dispositions did not change", entry["limitations"])

    def test_pr412_merge_records_metadata_split_guard_and_preserves_gates(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[412]
        self.assertEqual(entry["title"], "Add metadata-only evaluation split leakage guard")
        self.assertEqual(entry["pr_head_sha"], "4bbbf8e133cc5fd09a75dd52e598765d63e49e89")
        self.assertEqual(entry["merge_sha"], "156577a1206ec4cea8786ee9de7f9f718dd25227")
        self.assertEqual(entry["ci_run_id"], 41628667280)
        self.assertIn("41628661583 SUCCESS", entry["verification"])
        self.assertIn("41628663487 SUCCESS", entry["verification"])
        self.assertIn("41629134477", entry["verification"])
        self.assertIn("41629133141 SUCCESS", entry["verification"])
        self.assertIn("The Actions AI Code Review model step was skipped", entry["verification"])
        self.assertIn("separate Codex review summary", entry["verification"])
        self.assertIn("P04 T28/T29", entry["limitations"])
        self.assertIn("all readiness gates remain open or blocked", entry["limitations"])

    def test_pr413_records_signed_topology_attestation_and_limits(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[413]
        self.assertEqual(entry["title"], "Verify signed topology provenance offline (P03 T22)")
        self.assertEqual(entry["pr_head_sha"], "01fb6b0ea23b7d5ceaeadc1c8755c7c7205219d9")
        self.assertEqual(entry["merge_sha"], "acf1b0c97c084db4826d07066951ccda23f08d80")
        self.assertEqual(entry["ci_run_id"], 41630254246)
        self.assertIn("41630246585 SUCCESS", entry["verification"])
        self.assertIn("41630247569", entry["verification"])
        self.assertIn("41630631919", entry["verification"])
        self.assertIn("41630630347 SUCCESS", entry["verification"])
        self.assertIn("model step was skipped", entry["verification"])
        self.assertIn("T22 remains partial", entry["limitations"])
        self.assertIn("generated keys and synthetic topology only", entry["limitations"])
        self.assertIn("No readiness gate changed", entry["limitations"])

    def test_pr414_records_edge_verifiability_and_limits(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[414]
        self.assertEqual(entry["title"], "Mark unverified edges in topology drift reports (P03 T23)")
        self.assertEqual(entry["pr_head_sha"], "e6d43a9bbe207e54cfd1f21916995dbcea1898ef")
        self.assertEqual(entry["merge_sha"], "fac245a4686bb6360f41f9ebf4b0668141816a7c")
        self.assertEqual(entry["ci_run_id"], 41631891044)
        self.assertIn("41631884551 SUCCESS", entry["verification"])
        self.assertIn("41631885400", entry["verification"])
        self.assertIn("model step was skipped", entry["verification"])
        self.assertIn("41632661962", entry["verification"])
        self.assertIn("41632661123 SUCCESS", entry["verification"])
        self.assertIn("T23 remains partial", entry["limitations"])
        self.assertIn("Readiness gates remain unchanged", entry["limitations"])

    def test_pr415_records_t24_evidence_and_preserves_gate_dispositions(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[415]
        self.assertEqual(
            entry["title"],
            "Explain heuristic incident ranking with evidence digests (P03 T24)",
        )
        self.assertEqual(entry["pr_head_sha"], "539c9d5db89b9c8635f3c24560b370b7eee059ce")
        self.assertEqual(entry["merge_sha"], "7812489e310378d3eb1660d4bc0d37c2cfdb2ee0")
        self.assertEqual(entry["ci_run_id"], 41634487079)
        self.assertIn("41634480958 SUCCESS", entry["verification"])
        self.assertIn("41634481643", entry["verification"])
        self.assertIn("836 tests with 22 skips", entry["verification"])
        self.assertIn("model step was skipped", entry["verification"])
        self.assertIn("41634896082", entry["verification"])
        self.assertIn("41634894925 SUCCESS", entry["verification"])
        self.assertIn("T24 remains partial", entry["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )

    def test_pr416_and_pr417_are_recorded_without_gate_promotion(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        impact_paths = records[416]
        self.assertEqual(impact_paths["title"], "Add deterministic impact paths to T24 findings")
        self.assertEqual(impact_paths["pr_head_sha"], "7df1c32b03bf99935abdcae7f110ea2f30879624")
        self.assertEqual(impact_paths["merge_sha"], "1a1ed3d7204dbf245cbc471e591f5390a521ec2e")
        self.assertEqual(impact_paths["ci_run_id"], 41636602093)
        self.assertIn("41636593330 SUCCESS", impact_paths["verification"])
        self.assertIn("41636598032", impact_paths["verification"])
        self.assertIn("840 tests, 22 skipped", impact_paths["verification"])
        self.assertIn("41637692177", impact_paths["verification"])
        self.assertIn("41637691331 SUCCESS", impact_paths["verification"])
        self.assertIn("T24 remains partial", impact_paths["limitations"])

        website = records[417]
        self.assertEqual(
            website["title"],
            "design(site): Devobs 2026 RTL command center and Android/Windows download status",
        )
        self.assertEqual(website["pr_head_sha"], "fd41a93808c96aa6b335b0e858893d3ef2120a6f")
        self.assertEqual(website["merge_sha"], "620743877ea964fe6b332218961c41c46a0e27a2")
        self.assertEqual(website["ci_run_id"], 41646481581)
        self.assertIn("41646398283 SUCCESS", website["verification"])
        self.assertIn("41646475413", website["verification"])
        self.assertIn("41647057907", website["verification"])
        self.assertIn("41647056104 SUCCESS", website["verification"])
        self.assertIn("no model call is claimed", website["verification"])
        self.assertIn("No readiness gate changed", website["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )

    def test_pr418_is_recorded_with_exact_merge_evidence_and_limits(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[418]
        self.assertEqual(
            entry["title"],
            "Verify T24 impact paths against the exact fresh topology snapshot",
        )
        self.assertEqual(entry["pr_head_sha"], "3c5c4681a54b9518f4320069860f443273b956bd")
        self.assertEqual(entry["merge_sha"], "a66775cf8c58b9ab2890936bbd2a88b6647f399c")
        self.assertEqual(entry["ci_run_id"], 41655343424)
        self.assertIn("41655295899 SUCCESS", entry["verification"])
        self.assertIn("41655335969", entry["verification"])
        self.assertIn("847 tests, 22 skipped", entry["verification"])
        self.assertIn("41672386628", entry["verification"])
        self.assertIn("41672386750 SUCCESS", entry["verification"])
        self.assertIn("verify-production passed", entry["verification"])
        self.assertIn("snapshot provenance", entry["limitations"])
        self.assertIn("T24 remains partial", entry["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )

    def test_pr419_is_recorded_with_exact_merge_evidence_and_limits(self):
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        entry = records[419]
        self.assertEqual(
            entry["title"],
            "Bind T24 findings to signed topology and impact-path verification",
        )
        self.assertEqual(
            entry["pr_head_sha"],
            "1da4f176a20c71b23caf038bbd796ea5f073ee9a",
        )
        self.assertEqual(
            entry["merge_sha"],
            "3b3eeec8e85fe4068d84f44899aafa946d54cf35",
        )
        self.assertEqual(entry["ci_run_id"], 41673754849)
        self.assertIn("41674495022", entry["verification"])
        self.assertIn("41674494043", entry["verification"])
        self.assertIn("855 tests with 22 skipped", entry["verification"])
        self.assertIn("model-review steps were skipped", entry["verification"])
        self.assertIn(
            "Controlled incident drill and restore checks were skipped",
            entry["verification"],
        )
        self.assertIn("caller-supplied trust source", entry["limitations"])
        self.assertIn("T24 remains partial", entry["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )

    def test_pr574_history_remains_recorded_and_gates_unpromoted(self):
        result = validate(self.data)
        self.assertEqual(result["latest_pr"], 589)
        self.assertEqual(result["merged_milestones"], 212)
        records = {item["pr_number"]: item for item in self.data["milestones"]}
        self.assertEqual(records[550]["pr_head_sha"], "0e681cb62b4359f99d59caaaab99bfbc911e1879")
        self.assertEqual(records[550]["merge_sha"], "b68031d1b11c20d2f6fa29e46b687aa2010186b3")
        self.assertEqual(records[550]["ci_run_id"], 43153169533)
        self.assertIn("no Google API call", records[550]["limitations"])
        self.assertEqual(records[552]["pr_head_sha"], "fb1375dc265f43436bdc0bccea3b0007b51cbea4")
        self.assertEqual(records[552]["merge_sha"], "8c490b796994a842899db5e677eab6eff62bce7c")
        self.assertEqual(records[552]["ci_run_id"], 43155307706)
        self.assertIn("drive.file", records[552]["limitations"])
        self.assertIn("no live Google API call", records[552]["limitations"])
        self.assertEqual(records[554]["pr_head_sha"], "7266a45e34e7206b0861cb71f076a77f708af973")
        self.assertEqual(records[554]["merge_sha"], "10cd5055b833ab7fd1911256e8d0d4283e16fec7")
        self.assertEqual(records[554]["ci_run_id"], 43157396044)
        self.assertIn("drive.file", records[554]["limitations"])
        self.assertIn("no live Google API call", records[554]["limitations"])
        self.assertEqual(records[556]["pr_head_sha"], "3bee8a851213d45455828e9929108d75aaa62a92")
        self.assertEqual(records[556]["merge_sha"], "92ce3839bff39cfa1d02106993a11b2444c13ea7")
        self.assertEqual(records[556]["ci_run_id"], 43159280339)
        self.assertIn("chat.messages.create", records[556]["limitations"])
        self.assertIn("no live Google Chat API call", records[556]["limitations"])
        self.assertEqual(records[558]["pr_head_sha"], "57ff9fbfca2a00d1c731f449f3bc6e925ec4cb9d")
        self.assertEqual(records[558]["merge_sha"], "8579c907a6d0e83a59c7aff7011b49eaf71f3b6e")
        self.assertEqual(records[558]["ci_run_id"], 43183901590)
        self.assertIn("https://www.googleapis.com/auth/tasks", records[558]["limitations"])
        self.assertIn("No Google account was connected", records[558]["limitations"])
        self.assertEqual(records[560]["pr_head_sha"], "843dc2356e838761e26730634cddaaa77b1b27e5")
        self.assertEqual(records[560]["merge_sha"], "a0c0b568f3f09302051c51cc197fd84c2c735ade")
        self.assertEqual(records[560]["ci_run_id"], 43186249132)
        self.assertIn("Catalog-only correction", records[560]["limitations"])
        self.assertIn("no live API call", records[560]["limitations"])
        self.assertEqual(records[562]["pr_head_sha"], "3003b924abdc24151f4188cb1279bba1609eb5e5")
        self.assertEqual(records[562]["merge_sha"], "66f04316838870b095e0ab1ee9e104660b534f73")
        self.assertEqual(records[562]["ci_run_id"], 43191054462)
        self.assertIn("gmail.send", records[562]["limitations"])
        self.assertIn("no live Gmail API call", records[562]["limitations"])
        self.assertIn("inference skipped", records[562]["verification"])
        self.assertEqual(
            records[565]["pr_head_sha"],
            "b64d4e1f50893024a5e96e672e9e02493f12ded2",
        )
        self.assertEqual(
            records[565]["merge_sha"],
            "b6179ba440018c67936aca06ab92c562566cfd6e",
        )
        self.assertEqual(records[565]["ci_run_id"], 43231162103)
        self.assertIn("GitHub Pages publication", records[565]["verification"])
        self.assertIn("Vercel Production", records[565]["verification"])
        self.assertIn("AI-9 and P01 remain BLOCKED", records[565]["limitations"])
        self.assertEqual(
            records[572]["pr_head_sha"],
            "15e017fadc9e9978da4e782ee35853e71db3dfda",
        )
        self.assertEqual(
            records[572]["merge_sha"],
            "3a0c768572d49759565a5b6b947a0134194f13f9",
        )
        self.assertEqual(records[572]["ci_run_id"], 43233982170)
        self.assertIn("CodeQL 43233980719", records[572]["verification"])
        self.assertIn("verify-production passed", records[572]["verification"])
        self.assertIn("dpl_GTBXPmwQGVpQFbMtLVshteKoJLrX", records[572]["verification"])
        self.assertIn("AI-9 and P01 remain BLOCKED", records[572]["limitations"])
        self.assertEqual(
            records[574]["pr_head_sha"],
            "e3d4463407e077c4934798e0bc6e63c1c22f2187",
        )
        self.assertEqual(
            records[574]["merge_sha"],
            "f28c5bfec3641239ba96fe79d7fc3892ccd2d11c",
        )
        self.assertEqual(records[574]["ci_run_id"], 43246268485)
        self.assertIn("Python 3.12 and 3.15", records[574]["verification"])
        self.assertIn("CodeQL 43246266737", records[574]["verification"])
        self.assertIn("does not estimate USD spend", records[574]["limitations"])
        self.assertIn("AI-9 and P01 remain BLOCKED", records[574]["limitations"])
        self.assertEqual(
            records[530]["merge_sha"],
            "1dbc2d811b317b9f060bf46fa2376aaf083f0aec",
        )
        self.assertIn("No model weights were downloaded", records[530]["limitations"])
        self.assertEqual(records[532]["merge_sha"], "b518ad23affac0bc04e76497c52067afb494119a")
        self.assertEqual(records[532]["pr_head_sha"], "2cded308474161764b282af245e63460f70b668d")
        self.assertEqual(records[532]["ci_run_id"], 43129410896)
        self.assertIn("No OAuth Client ID", records[532]["limitations"])
        self.assertEqual(records[533]["merge_sha"], "f22263dfe43fb18f16ca4fc477307c90ddcb3d75")
        self.assertEqual(records[533]["pr_head_sha"], "0d347a04c4b7860b62343b6bc00028f03939826f")
        self.assertEqual(records[533]["ci_run_id"], 43130502274)
        self.assertIn("50 tests", records[533]["verification"])
        self.assertEqual(records[534]["merge_sha"], "933adefc3fbce277d431f253b3b6e96db992564f")
        self.assertEqual(records[534]["pr_head_sha"], "82ef6f6551851c5f3899b25f163873f4e97b0d8b")
        self.assertEqual(records[534]["ci_run_id"], 43131087636)
        self.assertIn("AI Code Review workflow 43130859436 completed", records[534]["verification"])
        self.assertIn("No AI model review ran", records[534]["limitations"])
        self.assertIn("remains untested with a real OAuth client", records[534]["limitations"])
        self.assertEqual(records[535]["merge_sha"], "b1f71c354c757a02c638d9ff31a9fab72d7b6b32")
        self.assertEqual(records[535]["pr_head_sha"], "5f172f878923acdbda831fdca7eca0f4db0beece")
        self.assertEqual(records[535]["ci_run_id"], 43131851220)
        self.assertIn("Node tests (push run)", records[535]["verification"])
        self.assertIn("No AI model review ran", records[535]["limitations"])
        self.assertEqual(records[536]["merge_sha"], "8d317f6b3f4db78c1d1a2338483a8f923ddba192")
        self.assertEqual(records[536]["pr_head_sha"], "2ed27a6f2e88f5cfbd6cfdc1fcd044744a9914d2")
        self.assertEqual(records[536]["ci_run_id"], 43132602268)
        self.assertIn("Node tests (push run)", records[536]["verification"])
        self.assertIn("No AI model review ran", records[536]["limitations"])
        self.assertEqual(records[537]["merge_sha"], "188693a06b3a9483a51175d1eb24d3ff01a29dbe")
        self.assertEqual(records[537]["pr_head_sha"], "8c0de0dc90dd0b23b46dfda34eb1ba07d494b3b2")
        self.assertEqual(records[537]["ci_run_id"], 43133228690)
        self.assertIn("Node tests passed on push", records[537]["verification"])
        self.assertIn("No AI model review ran", records[537]["limitations"])
        self.assertEqual(records[538]["merge_sha"], "04ef9efdda824130a795c3909b73748621c6581d")
        self.assertEqual(records[538]["pr_head_sha"], "1ac5cdc695a9c698b5ad7e5147c0c89021284af6")
        self.assertEqual(records[538]["ci_run_id"], 43133640879)
        self.assertIn("Post-merge main CI status is UNVERIFIED", records[538]["verification"])
        self.assertIn("GitHub CLI HTTP 401", records[538]["limitations"])
        self.assertEqual(records[539]["merge_sha"], "47004a850ebdc376711bf763ec9ca5458532a538")
        self.assertEqual(records[539]["pr_head_sha"], "a843db5b8bdaff34ae509171a3959e7698c58e9a")
        self.assertEqual(records[539]["ci_run_id"], 43134970833)
        self.assertEqual(records[540]["merge_sha"], "a1fdb646dc05be6105f5d3f2f38009b9221c9ead")
        self.assertEqual(records[540]["pr_head_sha"], "d7d728ea877efa8f6c67a73da4cda75ef1d59cd9")
        self.assertEqual(records[540]["ci_run_id"], 43136775234)
        self.assertEqual(records[541]["merge_sha"], "f6f627bbb0a8c215f79e260265dc8a939f820019")
        self.assertEqual(records[541]["pr_head_sha"], "2c1f92905780473f17f49fb065ae7514058d5cd2")
        self.assertEqual(records[541]["ci_run_id"], 43141603760)
        self.assertIn("Docker, OAuth and a live GitHub MCP call were not run", records[541]["limitations"])
        self.assertEqual(records[542]["merge_sha"], "1ee8e5f581173f01baf398936b98b26c49de1f47")
        self.assertEqual(records[542]["pr_head_sha"], "5967024a5bf0fbf53f40984097348be2e4e5b39b")
        self.assertEqual(records[542]["ci_run_id"], 43142370703)
        self.assertIn("no application behavior", records[542]["limitations"])
        self.assertEqual(records[543]["merge_sha"], "f34a1969c59780f3a77d027ec6e320f82e803ad3")
        self.assertEqual(records[543]["pr_head_sha"], "a58a3550b04a2ab366bfbf8245fe8fe4c9ee25dc")
        self.assertEqual(records[543]["ci_run_id"], 43143834691)
        self.assertIn("Grafana, Docker, OAuth", records[543]["limitations"])
        self.assertEqual(records[544]["merge_sha"], "882053b0a6c8c0264871aaa8a4121059190bb471")
        self.assertEqual(records[544]["pr_head_sha"], "36dcf9fafb994cda153c95c6ff75a7b0109de68e")
        self.assertEqual(records[544]["ci_run_id"], 43144634329)
        self.assertIn("no application behavior", records[544]["limitations"])
        self.assertEqual(records[545]["merge_sha"], "dc4f9834fe011985a93bbc4dd2bafef046fb9712")
        self.assertEqual(records[545]["pr_head_sha"], "9b3bdd5da890af9dd2f345a68fbd78a2d12eb0a6")
        self.assertEqual(records[545]["ci_run_id"], 43145332069)
        self.assertIn("no application behavior", records[545]["limitations"])
        self.assertEqual(records[546]["merge_sha"], "9a6eef149a3c942757867875883acbd34764499d")
        self.assertEqual(records[546]["pr_head_sha"], "01d165bb76af08857b6e4478330e55a93e503961")
        self.assertEqual(records[546]["ci_run_id"], 43147378625)
        self.assertIn("no cluster, kubeconfig", records[546]["limitations"])
        self.assertEqual(records[547]["merge_sha"], "e1f0b7041bbf45659652a85b270aa4d218edd1e8")
        self.assertEqual(records[547]["pr_head_sha"], "b2c3000082bddc5f6ab4314c7c777dbcf36dfdcc")
        self.assertEqual(records[547]["ci_run_id"], 43148113880)
        self.assertIn("synchronized state and readiness", records[547]["verification"])
        self.assertEqual(records[548]["merge_sha"], "74607bcdb1723274bae1516707d691ef583bbde0")
        self.assertEqual(records[548]["pr_head_sha"], "c5ef51fac267da555f01aeb2c13dd1d80620246b")
        self.assertEqual(records[548]["ci_run_id"], 43149872811)
        self.assertIn("no Docker runtime", records[548]["limitations"])
        self.assertIn("Post-merge main CI 43134970833", records[539]["verification"])
        self.assertIn("43134970567", records[539]["verification"])
        self.assertIn("AI-9 remains BLOCKED", records[539]["limitations"])
        self.assertIn("P01 remains BLOCKED", records[539]["limitations"])
        expected_recent = {
            502: ("0f6168681b08f687bc7a3aefa8238c0a7f3de691", "917b481694c4e3607f93890681e39c23e5dcad21", 42689426462),
            503: ("dd7a59bc3cf68070cfde419c442bdc7c2c52eb8f", "8b1ad57f5761fa86b6e606b8610ca3d643a8c0c6", 42737489501),
            504: ("babf6a5ed5c5edb935f6b4462563370801b68b81", "ada7d5519d11c2dada6b0e2096d535a99629098d", 42737545038),
            505: ("083ec1b6d6c3b576b8ec48b4cb82cd9dbe106b13", "13d6bc70d679e57ab6a5a09cf41690cdb21cfd97", 42739143583),
            506: ("fcc9ae0eb8a6a3e8d5f695f4624c5bb78514175b", "d395168a4b031e6b4614d653c89caeb4d366b6f1", 42796420402),
            507: ("902d2f735d2b2ee0f649218cd824b2417bc2284d", "71c79115e5a75f5b6629a5c1eaacbba0c2113233", 42798389835),
            508: ("2e1a3fb3235e1a529e9a286d9290d8adae124480", "57b256f21215a66bab9754e3f4f60ab8e6118ede", 42800093891),
            509: ("015f8b84d1e4233beb2cb7e03082267cd4dba5ed", "2ea1f58a6323f4ccc0e6553be4b2fb61e6017c99", 42805723188),
            514: ("fbfb8598bbada7e829bc87227f7a94ef68baaa98", "700cea42f876a1d9748ba86371dfbfdccef27942", 42978420012),
            515: ("85f806759a4d2c055e6ffaa418fd5c4c0b1eb2e2", "c8a99533a671438d6e6d2858b47124c3eaff138b", 42977569032),
            517: ("67842c5fba8645c72cf060a7c5088ab6408d5ca5", "cad4ad1dfc15061ec05c03ef04d10b01013a804a", 42997342707),
            518: ("f6ecfe35115e39f5969e483e7c53007637bd5139", "918946615a19f4bec31490d52d8a1125b522d9ad", 42999814862),
            519: ("15ad3b8bf190f5661a1eec158f59644328120314", "fc07f32d60a8ae46f03b4e1294a77d5faf1c12db", 43006292131),
            520: ("ceae271ebf0b19bffc7bc3ec2138b153211f6a6d", "c110603a9c8d66861d0551a4606ba2406c8ce6ad", 43007272717),
            521: ("777db154fb62a2d07acdf440cc7709b05bf0c97b", "1028e1c8fd02c1afe0ec40fce864b82b4134a147", 43010472818),
            522: ("df397841a3d9309de724fb6829d6c75346e7f72b", "cc29c7635ca817b13dbf92d6875e2386b81e1c6e", 43022732431),
            534: ("82ef6f6551851c5f3899b25f163873f4e97b0d8b", "933adefc3fbce277d431f253b3b6e96db992564f", 43131087636),
            535: ("5f172f878923acdbda831fdca7eca0f4db0beece", "b1f71c354c757a02c638d9ff31a9fab72d7b6b32", 43131851220),
            536: ("2ed27a6f2e88f5cfbd6cfdc1fcd044744a9914d2", "8d317f6b3f4db78c1d1a2338483a8f923ddba192", 43132602268),
            537: ("8c0de0dc90dd0b23b46dfda34eb1ba07d494b3b2", "188693a06b3a9483a51175d1eb24d3ff01a29dbe", 43133228690),
            538: ("1ac5cdc695a9c698b5ad7e5147c0c89021284af6", "04ef9efdda824130a795c3909b73748621c6581d", 43133640879),
            539: ("a843db5b8bdaff34ae509171a3959e7698c58e9a", "47004a850ebdc376711bf763ec9ca5458532a538", 43134970833),
            542: ("5967024a5bf0fbf53f40984097348be2e4e5b39b", "1ee8e5f581173f01baf398936b98b26c49de1f47", 43142370703),
            543: ("a58a3550b04a2ab366bfbf8245fe8fe4c9ee25dc", "f34a1969c59780f3a77d027ec6e320f82e803ad3", 43143834691),
            544: ("36dcf9fafb994cda153c95c6ff75a7b0109de68e", "882053b0a6c8c0264871aaa8a4121059190bb471", 43144634329),
            545: ("9b3bdd5da890af9dd2f345a68fbd78a2d12eb0a6", "dc4f9834fe011985a93bbc4dd2bafef046fb9712", 43145332069),
            546: ("01d165bb76af08857b6e4478330e55a93e503961", "9a6eef149a3c942757867875883acbd34764499d", 43147378625),
            547: ("b2c3000082bddc5f6ab4314c7c777dbcf36dfdcc", "e1f0b7041bbf45659652a85b270aa4d218edd1e8", 43148113880),
            548: ("c5ef51fac267da555f01aeb2c13dd1d80620246b", "74607bcdb1723274bae1516707d691ef583bbde0", 43149872811),
        }
        for number, (head_sha, merge_sha, ci_run_id) in expected_recent.items():
            with self.subTest(pr=number):
                self.assertEqual(records[number]["pr_head_sha"], head_sha)
                self.assertEqual(records[number]["merge_sha"], merge_sha)
                self.assertEqual(records[number]["ci_run_id"], ci_run_id)
        self.assertIn("natural incident labels", records[504]["limitations"])
        self.assertIn("No Actions run was found on the merge SHA", records[505]["limitations"])
        self.assertIn("CodeQL 42796417098 passed", records[506]["verification"])
        self.assertIn("static Pages", records[506]["limitations"])
        self.assertIn("CodeQL 42798388830 passed", records[507]["verification"])
        self.assertIn("Does not authenticate evidence", records[507]["limitations"])
        self.assertIn("CodeQL 42800092231 passed", records[508]["verification"])
        self.assertIn("Node skipped by path selection", records[508]["verification"])
        self.assertIn("issue #237 reopened", records[508]["verification"])
        self.assertIn("does not satisfy its acceptance criteria", records[508]["limitations"])
        self.assertIn("CodeQL 42805723573 passed", records[509]["verification"])
        self.assertIn("Node passed on the exact-head push run", records[509]["verification"])
        self.assertIn("Issue #237 remains open", records[509]["verification"])
        self.assertIn("No AI-9 holdout seed was run or consumed", records[509]["limitations"])
        self.assertIn("independent hosted staging evidence", records[509]["limitations"])
        self.assertIn("No Terra/Copilot/OpenAI inference", records[514]["limitations"])
        self.assertIn("Static Pages published and verify-production passed", records[514]["verification"])
        self.assertIn("no Terraform plan/apply", records[515]["limitations"])
        self.assertIn("Conftest policy tests passed", records[515]["verification"])
        self.assertIn("CodeQL 43022731578 passed", records[522]["verification"])
        self.assertIn("No cloud resource, secret change, or AI inference", records[522]["limitations"])
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        otel_api_501 = records[501]
        self.assertEqual(otel_api_501["pr_head_sha"], "5dc875a27c2a127a80248bc34414b6d12f86b4f0")
        self.assertEqual(otel_api_501["merge_sha"], "4382e364e8d67ef70425e5fe35473aac0f5a8272")
        self.assertEqual(otel_api_501["ci_run_id"], 42688136804)
        self.assertIn("CodeQL 42688135345 passed", otel_api_501["verification"])
        self.assertIn("AI-9 remains BLOCKED", otel_api_501["limitations"])
        self.assertIn("P01 remains BLOCKED", otel_api_501["limitations"])
        otel_500 = records[500]
        self.assertEqual(otel_500["pr_head_sha"], "5ad401c6baa2a9fbe33acc50afbbd33954afcef7")
        self.assertEqual(otel_500["merge_sha"], "6d56eabbc758b79faeda026c29c6372cd5989df4")
        self.assertEqual(otel_500["ci_run_id"], 42667080164)
        self.assertIn("CodeQL 42667079871 passed", otel_500["verification"])
        self.assertIn("AI-9 remains BLOCKED", otel_500["limitations"])
        self.assertIn("P01 remains BLOCKED", otel_500["limitations"])
        docs_484 = records[484]
        self.assertEqual(docs_484["pr_head_sha"], "74e5eac7094fa4d5df32c821f9afe6f04c7fae81")
        self.assertEqual(docs_484["merge_sha"], "b95e06afb300958df12c26ba88e5174a23d2c790")
        self.assertEqual(docs_484["ci_run_id"], 42519721372)
        self.assertIn("CodeQL 42519720974 passed", docs_484["verification"])
        self.assertIn("verify-production passed", docs_484["verification"])
        docs_485 = records[485]
        self.assertEqual(docs_485["pr_head_sha"], "bcf184571e9399d9f889da65c3576c24a73d204a")
        self.assertEqual(docs_485["merge_sha"], "5d5d541e9929eeee6b3789484f1913b25b493c17")
        self.assertEqual(docs_485["ci_run_id"], 42520693959)
        self.assertIn("CodeQL 42520693694 passed", docs_485["verification"])
        self.assertIn("verify-production passed", docs_485["verification"])
        integration_486 = records[486]
        self.assertEqual(integration_486["pr_head_sha"], "a9e52e05beca9728ddada58ccfda7c627e55ed18")
        self.assertEqual(integration_486["merge_sha"], "9bd2030931b1df953bd1005e0b45fc3d12454a41")
        self.assertEqual(integration_486["ci_run_id"], 42526324255)
        self.assertIn("CodeQL 42526324165 passed", integration_486["verification"])
        self.assertIn("LiveOps PR #1", integration_486["verification"])
        self.assertIn("not configured", integration_486["limitations"])
        self.assertIn("no dispatch event", integration_486["limitations"])
        evidence_sync_487 = records[487]
        self.assertEqual(evidence_sync_487["pr_head_sha"], "a91a8d68fb174d340a242816bbfbf7cf990a2f09")
        self.assertEqual(evidence_sync_487["merge_sha"], "06e852b8845a2d8ac1087fbdce2246c3248d8aad")
        self.assertEqual(evidence_sync_487["ci_run_id"], 42527292764)
        self.assertIn("CodeQL 42527292455 passed", evidence_sync_487["verification"])
        self.assertIn("verify-production passed", evidence_sync_487["verification"])
        monitoring_483 = records[483]
        self.assertEqual(monitoring_483["pr_head_sha"], "046c46838c11a07941f21714f7a4b3a5055ab446")
        self.assertEqual(monitoring_483["merge_sha"], "dadd4b83bf102d8eb232b199e7f7fb603cc20c4d")
        self.assertEqual(monitoring_483["ci_run_id"], 42518883043)
        self.assertIn("CodeQL 42518882082 SUCCESS", monitoring_483["verification"])
        self.assertIn("verify-production passed", monitoring_483["verification"])
        self.assertIn("promtool unavailable", monitoring_483["limitations"])
        self.assertIn("no containers started", monitoring_483["limitations"])
        evidence_sync_480 = records[480]
        self.assertEqual(evidence_sync_480["pr_head_sha"], "b554af6da6fe37e082ae7211580d92ec3010b780")
        self.assertEqual(evidence_sync_480["merge_sha"], "a4667625bbf802db9764ea215ca6754574694d09")
        self.assertEqual(evidence_sync_480["ci_run_id"], 42513312273)
        self.assertIn("CodeQL 42513311805 SUCCESS", evidence_sync_480["verification"])
        feature_k8s_481 = records[481]
        self.assertEqual(feature_k8s_481["pr_head_sha"], "a20709defb7cad148f47d7043186df5d5203051e")
        self.assertEqual(feature_k8s_481["merge_sha"], "85c65afd2ca1018da38a674ee88ea09942170cb9")
        self.assertEqual(feature_k8s_481["ci_run_id"], 42514879986)
        self.assertIn("CodeQL 42514879654 SUCCESS", feature_k8s_481["verification"])
        self.assertIn("No manifests were applied", feature_k8s_481["limitations"])
        self.assertIn("Apache-2.0", feature_k8s_481["limitations"])
        evidence_sync_495 = records[495]
        self.assertEqual(evidence_sync_495["pr_head_sha"], "21b913e5d67950038eeea4a1638f3efd6f217d9d")
        self.assertEqual(evidence_sync_495["merge_sha"], "4611ef6aa24bc9d9d4d08475a09dc761a32684ab")
        self.assertEqual(evidence_sync_495["ci_run_id"], 42595730920)
        self.assertIn("CodeQL 42595729760 passed", evidence_sync_495["verification"])
        self.assertIn("not natural-incident evidence", evidence_sync_495["limitations"])
        self.assertIn("AI-9 remains BLOCKED", evidence_sync_495["limitations"])
        pip_lock_497 = records[497]
        self.assertEqual(pip_lock_497["pr_head_sha"], "4ab2ebdbb3dc9e63e7eb007a072062635c07fcd7")
        self.assertEqual(pip_lock_497["merge_sha"], "b53fa0b35b718d4003a5d22a690cc0a04bd47553")
        self.assertEqual(pip_lock_497["ci_run_id"], 42601549598)
        self.assertIn("CodeQL 42601548178 passed", pip_lock_497["verification"])
        self.assertIn("pip==26.3", pip_lock_497["limitations"])
        psycopg_lock_498 = records[498]
        self.assertEqual(psycopg_lock_498["pr_head_sha"], "ac84b25511bb405863dbe8a893e1e25235ec6e0b")
        self.assertEqual(psycopg_lock_498["merge_sha"], "08963d4e3e342e0093d6d90d14fce861aa8a9695")
        self.assertEqual(psycopg_lock_498["ci_run_id"], 42602416866)
        self.assertIn("CodeQL 42602416548 passed", psycopg_lock_498["verification"])
        self.assertIn("22 skipped", psycopg_lock_498["limitations"])
        self.assertIn("P01 remains BLOCKED", psycopg_lock_498["limitations"])
        evidence_sync_479 = records[479]
        self.assertEqual(evidence_sync_479["pr_head_sha"], "5f2d565e179b28a183f5936c7895be4c2f405d5a")
        self.assertEqual(evidence_sync_479["merge_sha"], "e03d8be4a5c1b19e35c31d98339b45e7caf27d9d")
        self.assertEqual(evidence_sync_479["ci_run_id"], 42512447144)
        self.assertIn("CodeQL 42512446957 SUCCESS", evidence_sync_479["verification"])
        self.assertIn("no model inference is claimed", evidence_sync_479["limitations"])
        evidence_sync_478 = records[478]
        self.assertEqual(evidence_sync_478["pr_head_sha"], "ff4a33a66f87b82ad8be2cb6224fdf3bb210f7f9")
        self.assertEqual(evidence_sync_478["merge_sha"], "928485b35c549338e81eb7f5892ffadcadd62026")
        self.assertEqual(evidence_sync_478["ci_run_id"], 42510834635)
        self.assertIn("CodeQL 42510834600 SUCCESS", evidence_sync_478["verification"])
        self.assertIn("no model inference is claimed", evidence_sync_478["limitations"])
        evidence_sync_477 = records[477]
        self.assertEqual(evidence_sync_477["pr_head_sha"], "f2637976c699bcdacddfcca2b3027fcb813d25e7")
        self.assertEqual(evidence_sync_477["merge_sha"], "f657f4c51e2001d1be78d0d7d407ab5f3ad6b6a9")
        self.assertEqual(evidence_sync_477["ci_run_id"], 42510206549)
        self.assertIn("CodeQL 42510206514 SUCCESS", evidence_sync_477["verification"])
        self.assertIn("no model inference is claimed", evidence_sync_477["limitations"])
        evidence_sync_476 = records[476]
        self.assertEqual(evidence_sync_476["pr_head_sha"], "94241f7327be0ddc0004097ed2b3bd725dd701b0")
        self.assertEqual(evidence_sync_476["merge_sha"], "a2745960a56fe58e934e5c2a65aa9347cb3126c5")
        self.assertEqual(evidence_sync_476["ci_run_id"], 42509629238)
        self.assertIn("CodeQL 42509628495 SUCCESS", evidence_sync_476["verification"])
        self.assertIn("Node tests passed in exact-head CI 42509355473", evidence_sync_476["limitations"])
        evidence_sync_475 = records[475]
        self.assertEqual(evidence_sync_475["pr_head_sha"], "0c643266996a75e40f657b7f8be4ab3f900e2d13")
        self.assertEqual(evidence_sync_475["merge_sha"], "5cb98322e9a54f0102f2f0ab1df7673de2121b4c")
        self.assertEqual(evidence_sync_475["ci_run_id"], 42509038532)
        self.assertIn("CodeQL 42509038342 SUCCESS", evidence_sync_475["verification"])
        evidence_sync_474 = records[474]
        self.assertEqual(evidence_sync_474["pr_head_sha"], "9f5834d18dee42ea0172b4a049343e1eaf824e9e")
        self.assertEqual(evidence_sync_474["merge_sha"], "c07f12ea07ff6ec3efd5f09886fead503e593b69")
        self.assertEqual(evidence_sync_474["ci_run_id"], 42507031658)
        self.assertIn("CodeQL 42507031373 SUCCESS", evidence_sync_474["verification"])
        self.assertIn("600000 ms", evidence_sync_474["limitations"])
        evidence_sync_473 = records[473]
        self.assertEqual(evidence_sync_473["pr_head_sha"], "fc4bca0fd5da34cd23bde842d287432db56339a3")
        self.assertEqual(evidence_sync_473["merge_sha"], "b8bcaaa221e3ac9319d60e9dc84c90314deaebc4")
        self.assertEqual(evidence_sync_473["ci_run_id"], 42506762280)
        self.assertIn("CodeQL 42506762080 SUCCESS", evidence_sync_473["verification"])
        evidence_sync_472 = records[472]
        self.assertEqual(
            evidence_sync_472["pr_head_sha"],
            "c97795d81986f02108a2c10780e3cf30c8640d7a",
        )
        self.assertEqual(
            evidence_sync_472["merge_sha"],
            "5f108923c301a95aea2bb3a93f0985317d090d0f",
        )
        self.assertEqual(evidence_sync_472["ci_run_id"], 42505771596)
        self.assertIn("CodeQL 42505771116 SUCCESS", evidence_sync_472["verification"])
        self.assertIn("timeout-cap warning", evidence_sync_472["limitations"])
        evidence_sync_471 = records[471]
        self.assertEqual(
            evidence_sync_471["pr_head_sha"],
            "29d5b6866da518b245f1c2d9f06ac1647bf0a9aa",
        )
        self.assertEqual(
            evidence_sync_471["merge_sha"],
            "c79410f81ebd2c398c9894803d2c494cdcbae509",
        )
        self.assertEqual(evidence_sync_471["ci_run_id"], 42504932069)
        self.assertIn("CodeQL 42504930954 SUCCESS", evidence_sync_471["verification"])
        self.assertIn("timeout-cap warning", evidence_sync_471["limitations"])
        evidence_sync_470 = records[470]
        self.assertEqual(
            evidence_sync_470["pr_head_sha"],
            "88da38a947d3ced13336d7e033928d23f7aa9add",
        )
        self.assertEqual(
            evidence_sync_470["merge_sha"],
            "a1508d3125b92f529c9dcd30e7e477978660dd0d",
        )
        self.assertEqual(evidence_sync_470["ci_run_id"], 42503855396)
        self.assertIn("CodeQL 42503854498 SUCCESS", evidence_sync_470["verification"])
        self.assertIn("Node passed on one exact-head CI run", evidence_sync_470["verification"])
        evidence_sync_469 = records[469]
        self.assertEqual(
            evidence_sync_469["pr_head_sha"],
            "0d3ef0d808a7c0feae0da074616017bd4fda4288",
        )
        self.assertEqual(
            evidence_sync_469["merge_sha"],
            "21f9c8d3f6c2cc7b9e580bfcf8d81121b9e02d4a",
        )
        self.assertEqual(evidence_sync_469["ci_run_id"], 42502967385)
        self.assertIn("CodeQL 42502966485 SUCCESS", evidence_sync_469["verification"])
        self.assertIn("Node passed on one exact-head CI run", evidence_sync_469["verification"])
        evidence_sync_468 = records[468]
        self.assertEqual(
            evidence_sync_468["pr_head_sha"],
            "15b71acbe810988e4b9d3517c2d390664a2bb927",
        )
        self.assertEqual(
            evidence_sync_468["merge_sha"],
            "2783cb7293c6535b0b051cde88d803aaff4df7e3",
        )
        self.assertEqual(evidence_sync_468["ci_run_id"], 42502451903)
        self.assertIn("Exact-merge main CI 42502451903", evidence_sync_468["verification"])
        evidence_sync_467 = records[467]
        self.assertEqual(
            evidence_sync_467["pr_head_sha"],
            "b0337742556937ae8b8fc8090cecadd9c32411fe",
        )
        self.assertEqual(
            evidence_sync_467["merge_sha"],
            "13ac0a30e819341cf7e9439535d06cf2c8493d6b",
        )
        self.assertEqual(evidence_sync_467["ci_run_id"], 42502012924)
        self.assertIn("Exact-merge main CI 42502012924", evidence_sync_467["verification"])
        evidence_sync_466 = records[466]
        self.assertEqual(
            evidence_sync_466["pr_head_sha"],
            "c626c514b247e0a12953841ae4bb1c21d19373f2",
        )
        self.assertEqual(
            evidence_sync_466["merge_sha"],
            "a753723e72882c089ceb413608b6e2c5d4df6bfb",
        )
        self.assertEqual(evidence_sync_466["ci_run_id"], 42500725685)
        self.assertIn("Exact-merge main CI 42500725685", evidence_sync_466["verification"])
        evidence_sync_464 = records[464]
        self.assertEqual(
            evidence_sync_464["pr_head_sha"],
            "939e4439068fbe82d06dc492ef9cc61d7051d883",
        )
        self.assertEqual(
            evidence_sync_464["merge_sha"],
            "413a69eef88f15303b675adcde5da4e14f4c64f0",
        )
        self.assertEqual(evidence_sync_464["ci_run_id"], 42498146148)
        self.assertIn("Exact-merge main CI 42498146148", evidence_sync_464["verification"])
        local_models_465 = records[465]
        self.assertEqual(
            local_models_465["pr_head_sha"],
            "e6b0d631620adc28633c25fce2e6baad2f104245",
        )
        self.assertEqual(
            local_models_465["merge_sha"],
            "bd883cc49e79c461eb616f2d0592718fbd8b5c52",
        )
        self.assertEqual(local_models_465["ci_run_id"], 42498318610)
        self.assertIn("Exact-merge main CI 42498318610", local_models_465["verification"])
        self.assertIn("No local model container/image or weights", local_models_465["limitations"])
        evidence_sync_463 = records[463]
        self.assertEqual(
            evidence_sync_463["pr_head_sha"],
            "42879ec9cf65fffeff45f49f93da335f0ed0b80f",
        )
        self.assertEqual(
            evidence_sync_463["merge_sha"],
            "16377e2b605772f102245f735d5d90db24d663ec",
        )
        self.assertEqual(evidence_sync_463["ci_run_id"], 42496643751)
        self.assertIn("Exact-merge main CI 42496643751", evidence_sync_463["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync_463["limitations"])
        evidence_sync_449 = records[449]
        self.assertEqual(
            evidence_sync_449["pr_head_sha"],
            "423673da4fa8c1754ebf9b6ee94b5d14149e545f",
        )
        self.assertEqual(
            evidence_sync_449["merge_sha"],
            "0e8c03e5ba4df6e7aa09f63e64918103606d8814",
        )
        self.assertEqual(evidence_sync_449["ci_run_id"], 42425213432)
        self.assertIn("Exact-merge main CI 42425213432", evidence_sync_449["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync_449["limitations"])
        foundation_450 = records[450]
        self.assertEqual(
            foundation_450["pr_head_sha"],
            "adf08378470dc0bf93b286a1a44a981bf1e2cb2e",
        )
        self.assertEqual(
            foundation_450["merge_sha"],
            "fe19ff799a9eb8d2be42e5ff788b8b1a252f79a3",
        )
        self.assertEqual(foundation_450["ci_run_id"], 42425329761)
        self.assertIn("Exact-merge main CI 42425329761", foundation_450["verification"])
        self.assertIn("PR #451 merged only into", foundation_450["limitations"])
        self.assertIn("not main", foundation_450["limitations"])
        runbook_455 = records[455]
        self.assertEqual(
            runbook_455["pr_head_sha"],
            "2489f919aece388ebe1ca22b4f672d15fa187969",
        )
        self.assertEqual(
            runbook_455["merge_sha"],
            "4d1a4e5c663e69c31964a62afc8417b5a6386e29",
        )
        self.assertEqual(runbook_455["ci_run_id"], 42482486198)
        self.assertIn("Exact-merge main CI 42482486198", runbook_455["verification"])
        self.assertIn("localStorage", runbook_455["limitations"])
        self.assertIn("AI-9 BLOCKED", runbook_455["limitations"])
        evidence_sync_456 = records[456]
        self.assertEqual(
            evidence_sync_456["pr_head_sha"],
            "3c76f5f6ea91c9a7dbcc93297ca033ccf5affffb",
        )
        self.assertEqual(
            evidence_sync_456["merge_sha"],
            "97a7da7592be21cd8250bda2efff65c5fa45792e",
        )
        self.assertEqual(evidence_sync_456["ci_run_id"], 42484399657)
        self.assertIn("Exact-merge main CI 42484399657", evidence_sync_456["verification"])
        self.assertIn("recording PR #455", evidence_sync_456["limitations"])
        local_models_457 = records[457]
        self.assertEqual(
            local_models_457["pr_head_sha"],
            "eb2a0e5c94348d3b95517e35780e52968d62d67f",
        )
        self.assertEqual(
            local_models_457["merge_sha"],
            "b2a5a4feec930cc9e0ca75289f1c9b640ed99cac",
        )
        self.assertEqual(local_models_457["ci_run_id"], 42484596864)
        self.assertIn("Cosign verification", local_models_457["verification"])
        self.assertIn("No model weights", local_models_457["limitations"])
        evidence_sync_458 = records[458]
        self.assertEqual(
            evidence_sync_458["pr_head_sha"],
            "0803958af80e25ec164de778fded0f14265c390b",
        )
        self.assertEqual(
            evidence_sync_458["merge_sha"],
            "63895a1159f6867f5becda56f24395ff33f4057f",
        )
        self.assertEqual(evidence_sync_458["ci_run_id"], 42486881365)
        self.assertIn("Exact-head CI 42486018274", evidence_sync_458["verification"])
        self.assertIn("Exact-merge main CI 42486881365", evidence_sync_458["verification"])
        self.assertIn("Node skipped on PR and main CI", evidence_sync_458["verification"])
        gemini_459 = records[459]
        self.assertEqual(
            gemini_459["pr_head_sha"],
            "1ba0ed7ae91449e306bd9b065df1b05b5793f679",
        )
        self.assertEqual(
            gemini_459["merge_sha"],
            "0a350672865b1c62f72928fccf078ee5e1bd12c5",
        )
        self.assertEqual(gemini_459["ci_run_id"], 42490036290)
        self.assertIn("Exact-head CI 42489939852", gemini_459["verification"])
        self.assertIn("Exact-merge main CI 42490036290", gemini_459["verification"])
        self.assertIn("No Gemini inference", gemini_459["limitations"])
        evidence_sync_460 = records[460]
        self.assertEqual(
            evidence_sync_460["pr_head_sha"],
            "12a6e40ff08ca8334a7425598fddb479d8452e99",
        )
        self.assertEqual(
            evidence_sync_460["merge_sha"],
            "418deb79296d44a1f06671287e6aa6798a3305d7",
        )
        self.assertEqual(evidence_sync_460["ci_run_id"], 42489904300)
        self.assertIn("Exact-head CI 42488504758", evidence_sync_460["verification"])
        self.assertIn("Exact-merge main CI 42489904300", evidence_sync_460["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync_460["limitations"])
        evidence_sync_461 = records[461]
        self.assertEqual(
            evidence_sync_461["pr_head_sha"],
            "130f86ddc0903425559ef8126d3b5166fbb78146",
        )
        self.assertEqual(
            evidence_sync_461["merge_sha"],
            "e9578d677601e4efbbe47aef8f869686b9604038",
        )
        self.assertEqual(evidence_sync_461["ci_run_id"], 42494465959)
        self.assertIn("Exact-head CI 42490799344", evidence_sync_461["verification"])
        self.assertIn("Exact-merge main CI 42494465959", evidence_sync_461["verification"])
        self.assertIn("No Gemini inference", evidence_sync_461["limitations"])
        evidence_sync_462 = records[462]
        self.assertEqual(
            evidence_sync_462["pr_head_sha"],
            "12c2764e46364c8c951a8421073c463a7ee238ef",
        )
        self.assertEqual(
            evidence_sync_462["merge_sha"],
            "fcd1c53da3a8c97de404e0614c2a12125059418c",
        )
        self.assertEqual(evidence_sync_462["ci_run_id"], 42495741659)
        self.assertIn("Exact-head CI 42495644430", evidence_sync_462["verification"])
        self.assertIn("Exact-merge main CI 42495741659", evidence_sync_462["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync_462["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )
        evidence_sync_448 = records[448]
        self.assertEqual(
            evidence_sync_448["pr_head_sha"],
            "0f0dd8dfecfa470548d51ce5c838c06af0dc3f97",
        )
        self.assertEqual(
            evidence_sync_448["merge_sha"],
            "fcffcde2ac65f2affadad808e09c91d248f93734",
        )
        self.assertEqual(evidence_sync_448["ci_run_id"], 42421345704)
        self.assertIn("Exact-merge CI 42421345704", evidence_sync_448["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync_448["limitations"])
        evidence_sync = records[447]
        self.assertEqual(
            evidence_sync["pr_head_sha"],
            "6b6d51d2f56c0b483915d09d0ea21f2866d6671c",
        )
        self.assertEqual(
            evidence_sync["merge_sha"],
            "c2a9ddbcf8e505a2612ee2a69a1e1f0e312a3d0e",
        )
        self.assertEqual(evidence_sync["ci_run_id"], 42420735715)
        self.assertIn("Exact-merge CI 42420735715", evidence_sync["verification"])
        self.assertIn("Documentation/test synchronization", evidence_sync["limitations"])
        ai_stage_integration = records[446]
        self.assertEqual(
            ai_stage_integration["pr_head_sha"],
            "5bd2173ba7faf09b6035f37b36692f713653cebd",
        )
        self.assertEqual(
            ai_stage_integration["merge_sha"],
            "abdaf0f21e47761d961d3826478a772365b7a1f7",
        )
        self.assertEqual(ai_stage_integration["ci_run_id"], 42419091194)
        self.assertIn("Exact-merge main CI 42419091194", ai_stage_integration["verification"])
        self.assertIn("no model inference", ai_stage_integration["limitations"])
        scorecard = records[437]
        self.assertEqual(
            scorecard["merge_sha"],
            "783a3d329d829e9c2f10cbd33fa6abe77abda846",
        )
        self.assertEqual(
            scorecard["pr_head_sha"],
            "ff600f7ed15556278fe929df6ccfb8cc20cacde7",
        )
        self.assertEqual(scorecard["ci_run_id"], 41875788207)
        self.assertIn("41879187351", scorecard["verification"])
        self.assertIn("no JSON artifact", scorecard["limitations"])
        zizmor = records[438]
        self.assertEqual(
            zizmor["merge_sha"],
            "fb6c448ce234ad6e8295cd178225794f94ea044f",
        )
        self.assertEqual(
            zizmor["pr_head_sha"],
            "711d1d94cdede3e898bf6eae1a7ad447aa3d1756",
        )
        self.assertEqual(zizmor["ci_run_id"], 41884733066)
        self.assertIn("41884731624", zizmor["verification"])
        self.assertIn("AI-9 FAIL / BLOCKED", zizmor["limitations"])
        actionlint = records[435]
        self.assertEqual(
            actionlint["merge_sha"],
            "4756f7e125fbaff193f25c84df9ac1073e0fe64c",
        )
        self.assertEqual(
            actionlint["pr_head_sha"],
            "0b461fea0a248cd8c43a1e43aeaad702eb8acffe",
        )
        self.assertEqual(actionlint["ci_run_id"], 41846791365)
        self.assertIn("successful GitHub workflows do not prove", actionlint["limitations"])
        implementation = records[420]
        self.assertEqual(
            implementation["pr_head_sha"],
            "fc83e67277a05d47a7eaeaecc857864a62cda162",
        )
        self.assertEqual(
            implementation["merge_sha"],
            "bcaa246bc0d4a670b8f49f0d20edfc9939bbd772",
        )
        self.assertEqual(implementation["ci_run_id"], 41705566648)
        self.assertIn("41706381759", implementation["verification"])
        self.assertIn("41706380276", implementation["verification"])
        self.assertIn("893 passed, 22 skipped", implementation["verification"])
        self.assertIn("T22-T25 remain partial", implementation["limitations"])

        documentation = records[421]
        self.assertEqual(
            documentation["pr_head_sha"],
            "0516a5c64bb91fbd596707b2d201deca8eb97dfc",
        )
        self.assertEqual(
            documentation["merge_sha"],
            "7ca86444efc3529ba5da0ca934939578f52d6d4e",
        )
        self.assertEqual(documentation["ci_run_id"], 41707347161)
        self.assertIn("41709068995", documentation["verification"])
        self.assertIn("41709067466", documentation["verification"])
        self.assertIn("Documentation only", documentation["limitations"])

        latest_documentation = records[422]
        self.assertEqual(
            latest_documentation["pr_head_sha"],
            "e574c7a0947547cd04f535ddddfc64aa62623c70",
        )
        self.assertEqual(
            latest_documentation["merge_sha"],
            "f34977941c1634958c0c94b527ac4cb071b341b6",
        )
        self.assertEqual(latest_documentation["ci_run_id"], 41710043269)
        self.assertIn("41710442360", latest_documentation["verification"])
        self.assertIn("41710441908", latest_documentation["verification"])
        self.assertIn("Documentation only", latest_documentation["limitations"])

        newest_documentation = records[423]
        self.assertEqual(
            newest_documentation["pr_head_sha"],
            "d619ab74ce1107d3d970567f7f726c79380bc5af",
        )
        self.assertEqual(
            newest_documentation["merge_sha"],
            "29d69e55d982609d2d6b893c7306d37fefc11c4b",
        )
        self.assertEqual(newest_documentation["ci_run_id"], 41711195370)
        self.assertIn("41717471721", newest_documentation["verification"])
        self.assertIn("41717469794", newest_documentation["verification"])
        self.assertIn("Documentation only", newest_documentation["limitations"])

        documentation_424 = records[424]
        self.assertEqual(
            documentation_424["pr_head_sha"],
            "eef59baf58115762440b02ec2e3043db78e19c70",
        )
        self.assertEqual(
            documentation_424["merge_sha"],
            "32632f46f0be09da7d65b143dfa7859d01fa43ad",
        )
        self.assertEqual(documentation_424["ci_run_id"], 41719532112)
        self.assertIn("41722249240", documentation_424["verification"])
        self.assertIn("41722248715", documentation_424["verification"])

        platform_feature = records[425]
        self.assertEqual(
            platform_feature["pr_head_sha"],
            "8137d3e53418e2111485c5ff84c6eb78ef653018",
        )
        self.assertEqual(
            platform_feature["merge_sha"],
            "e75a6ba19a9c319b94cb4bfa9a4fdfbcce46fc9d",
        )
        self.assertEqual(platform_feature["ci_run_id"], 41730515418)
        self.assertIn("41730759897", platform_feature["verification"])
        self.assertIn("41730758476", platform_feature["verification"])
        self.assertIn("localStorage", platform_feature["limitations"])
        self.assertIn("unverified", platform_feature["limitations"])

        merge_evidence = records[426]
        self.assertEqual(
            merge_evidence["pr_head_sha"],
            "73d166d224e88205d2e15ebfbd36e4d17fa92523",
        )
        self.assertEqual(
            merge_evidence["merge_sha"],
            "0e1b8af7ae732f333f82c1abaae7a00e317e7f7b",
        )
        self.assertEqual(merge_evidence["ci_run_id"], 41807891435)
        self.assertIn("41808324038", merge_evidence["verification"])
        self.assertIn("41808322378", merge_evidence["verification"])

        latest_merge = records[427]
        self.assertEqual(
            latest_merge["pr_head_sha"],
            "c66378723e5396ed0e6e3c09bdad1473bd1179ea",
        )
        self.assertEqual(
            latest_merge["merge_sha"],
            "d769dc26479e943b743edd45f770498d7d9e5254",
        )
        self.assertEqual(latest_merge["ci_run_id"], 41808975424)
        self.assertIn("41809164943", latest_merge["verification"])
        self.assertIn("41809166587", latest_merge["verification"])
        self.assertIn("HTTP 500", latest_merge["limitations"])

        newest_merge = records[429]
        self.assertEqual(
            newest_merge["pr_head_sha"],
            "225653774f1778757f1776d0c598e559641461c2",
        )
        self.assertEqual(
            newest_merge["merge_sha"],
            "fd5321e330acc6c1e38c516161e98167388bc7be",
        )
        self.assertEqual(newest_merge["ci_run_id"], 41809776109)
        self.assertIn("41809998465", newest_merge["verification"])
        self.assertIn("41809998782", newest_merge["verification"])
        self.assertIn("verify-production passed", newest_merge["verification"])
        self.assertIn("Documentation only", newest_merge["limitations"])

        latest_merge = records[430]
        self.assertEqual(
            latest_merge["pr_head_sha"],
            "ecb1abadf155851190f64fc9c273bcd079272720",
        )
        self.assertEqual(
            latest_merge["merge_sha"],
            "c1d2c54d323db21eda41809254016896b14f79f0",
        )
        self.assertEqual(latest_merge["ci_run_id"], 41810508402)
        self.assertIn("41810818519", latest_merge["verification"])
        self.assertIn("41810823255", latest_merge["verification"])
        self.assertIn("verify-production passed", latest_merge["verification"])
        self.assertIn("Documentation only", latest_merge["limitations"])

        newest_merge = records[431]
        self.assertEqual(
            newest_merge["pr_head_sha"],
            "f46e8ab832e19d8870462a688ea52359b42db055",
        )
        self.assertEqual(
            newest_merge["merge_sha"],
            "a7f822e0bd8cc6b8e7017d1992572852f4b9f36a",
        )
        self.assertEqual(newest_merge["ci_run_id"], 41812081497)
        self.assertIn("41812564677", newest_merge["verification"])
        self.assertIn("41812581749", newest_merge["verification"])
        self.assertIn("verify-production passed", newest_merge["verification"])
        self.assertIn("no destination was created", newest_merge["limitations"])

        latest_merge = records[433]
        self.assertEqual(
            latest_merge["pr_head_sha"],
            "07ed303fc42df48b3c0154591e4b63a5ce5ea8ef",
        )
        self.assertEqual(
            latest_merge["merge_sha"],
            "b5ce4a42f10176da1bc0194461353281f64c3707",
        )
        self.assertEqual(latest_merge["ci_run_id"], 41815601457)
        self.assertIn("41816012226", latest_merge["verification"])
        self.assertIn("41816012361", latest_merge["verification"])
        self.assertIn("local SQLite topology-keyring persistence", latest_merge["limitations"])
        self.assertIn("P01 remains NO-GO / BLOCKED", latest_merge["limitations"])
        recent_merges = {
            439: (
                "8913531b0c592f8783434a164aaa69acb41d7618",
                "6aa6963996b4f98d112b45af9c52631adcecb81e",
                41891798822,
            ),
            440: (
                "b2700d26090480dddc7321a1a3536c20223b91f7",
                "d21f9008fa492b154218c113b53a78cd87f8f8b1",
                41903748967,
            ),
            441: (
                "3e9ebab9838ad72d07d3d4a080109c24611b4661",
                "5b75be633b4fd5c797d9e4fdc1e960fd0d68e07e",
                42008311085,
            ),
            442: (
                "3e64be9b530708c9ee2a6080c17d72ef0487b85d",
                "4b5923254c52b61e87a7afd77301ee4e3719b4aa",
                42144057744,
            ),
            444: (
                "f58c4528ee59e977693bd3469702317fafbb403b",
                "96698a7e1ed4c50fe85ca8996760b65be75863c5",
                42411639299,
            ),
            445: (
                "ae780aa23c4c20541dcf7715109aa3920fbb4ce2",
                "0ea63c5d7ca7ccb3a5f3ca3a97b3206804ff7224",
                42416177822,
            ),
        }
        for pr_number, (head_sha, merge_sha, run_id) in recent_merges.items():
            entry = records[pr_number]
            self.assertEqual(entry["pr_head_sha"], head_sha)
            self.assertEqual(entry["merge_sha"], merge_sha)
            self.assertEqual(entry["ci_run_id"], run_id)
            self.assertIn("VERIFIED 2026-11-07", entry["verification"])
        self.assertIn(
            "Pages publish and verify-production are not claimed successful",
            records[439]["limitations"],
        )
        self.assertIn("No real OpenAI request", records[440]["limitations"])
        self.assertIn("no Render resource", records[441]["limitations"])
        self.assertIn(
            "source event linkage was not independently established",
            records[442]["limitations"],
        )
        self.assertIn("42411290552", records[444]["verification"])
        self.assertIn("42411638478", records[444]["verification"])
        self.assertIn("verify-production passed", records[444]["verification"])
        self.assertIn("No post-merge repository_dispatch event", records[444]["limitations"])
        self.assertIn("42416005932", records[445]["verification"])
        self.assertIn("42416177272", records[445]["verification"])
        self.assertIn("Node CI job skipped by path filtering", records[445]["verification"])
        self.assertIn("no model inference is claimed", records[445]["limitations"])
        self.assertEqual(
            {gate["id"]: gate["status"] for gate in self.data["gates"]},
            {
                "ai9-detection-quality": "BLOCKED",
                "p01-managed-saas": "BLOCKED",
                "codex-agent-runtime-acceptance": "OPEN",
            },
        )

    def test_verified_dependency_batch_is_recorded_without_gate_promotion(self):
        result = validate(self.data)
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        expected = {
            566: (
                "ed7b087b75cc5b25570784c5f25b307ad9f5e638",
                "615b3e69fbc5347ee2bbf8ef5390cda888de706f",
                43298409810,
                43298650379,
                43298648964,
            ),
            568: (
                "43fe83f4ef6e77731d0c481d7d3a7b4e2e28486f",
                "85aebd84004b723ad1d7a60438c6c57b25b7769c",
                43298692797,
                43299034541,
                43299032793,
            ),
            569: (
                "79796537880c4f37473f3dc5bccbec9d1c0bfcb2",
                "d3f6e3741596fe30aeaff9f5c4f48b08d169385a",
                43301133050,
                43301723091,
                43301721827,
            ),
            570: (
                "bec6deeba442e2e96434bd9324de8f482bc70223",
                "d8ff193645569134ba6ede21b1030f45f6a9242c",
                43299432384,
                43299907117,
                43299901601,
            ),
            571: (
                "c04ac00c52495b4caa093791529f0934d722271f",
                "60f0b98180040d237aa9d90a3598430d010b99bd",
                43300241509,
                43300687014,
                43300687061,
            ),
            576: (
                "c5cce7c196e8f9a4ef3cbfdc0a9bffa5c65e59a0",
                "3eadca1727671f4990255b6e609e47b719926547",
                43301989268,
                43302413818,
                43302411900,
            ),
        }
        for number, (head, merged, ci, main_ci, codeql) in expected.items():
            with self.subTest(pr=number):
                entry = records[number]
                self.assertEqual(entry["pr_head_sha"], head)
                self.assertEqual(entry["merge_sha"], merged)
                self.assertEqual(entry["ci_run_id"], ci)
                self.assertIn(str(main_ci), entry["verification"])
                self.assertIn(str(codeql), entry["verification"])
                self.assertIn("passed", entry["verification"])
        self.assertNotIn(567, records)
        self.assertEqual(result["merged_milestones"], 212)
        self.assertEqual(result["latest_pr"], 589)
        self.assertIn("v1beta", records[569]["limitations"])
        self.assertIn("verify-production passed", records[576]["verification"])
        gates = {entry["id"]: entry["status"] for entry in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr578_dependabot_metrics_boundary_is_recorded_without_gate_promotion(self):
        result = validate(self.data)
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        entry = records[578]
        self.assertEqual(entry["pr_head_sha"], "5d81c2f218bfbc81b1f27dbfae95d8e7c025b962")
        self.assertEqual(entry["merge_sha"], "7d4f1a4937890bb9ea9786a18cee92e12971ea80")
        self.assertEqual(entry["ci_run_id"], 43305186699)
        for run_id in (43305176500, 43305176702, 43305441591, 43305439062):
            self.assertIn(str(run_id), entry["verification"])
        self.assertIn("verify-production passed", entry["verification"])
        self.assertIn("does not add an API client", entry["limitations"])
        self.assertIn("automatic budget update", entry["limitations"])
        self.assertEqual(result["merged_milestones"], 212)
        self.assertEqual(result["latest_pr"], 589)
        gates = {gate["id"]: gate["status"] for gate in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr585_express5_dependency_refresh_is_verified_without_gate_promotion(self):
        result = validate(self.data)
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        entry = records[585]
        self.assertEqual(entry["pr_head_sha"], "6b362bfe01ed87717d3ea8322f778d6b78680f0b")
        self.assertEqual(entry["merge_sha"], "06c0849bc0fd8494f6ed889763606e013653c367")
        self.assertEqual(entry["ci_run_id"], 43308109491)
        for run_id in (43308097217, 43308097959, 43308109464, 43308481179, 43308479420):
            self.assertIn(str(run_id), entry["verification"])
        self.assertIn("verify-production passed", entry["verification"])
        self.assertIn("0 vulnerabilities", entry["verification"])
        self.assertIn("No live Google or Gemini requests", entry["limitations"])
        self.assertEqual(result["merged_milestones"], 212)
        self.assertEqual(result["latest_pr"], 589)
        gates = {gate["id"]: gate["status"] for gate in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr588_readyz_probe_bounds_are_recorded_without_gate_promotion(self):
        result = validate(self.data)
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        entry = records[588]
        self.assertEqual(entry["pr_head_sha"], "b3d0bb2329ee193efd1c3db6a0169badc6fd7d7f")
        self.assertEqual(entry["merge_sha"], "a5906d40a08927563edb601d36b3eea0d957302b")
        self.assertEqual(entry["ci_run_id"], 43404392132)
        for run_id in (43356823358, 43356817231, 43356823244, 43404391713):
            self.assertIn(str(run_id), entry["verification"])
        self.assertIn("250 ms", entry["limitations"])
        self.assertIn("€11.24 only if Jordan 16% tax applies", entry["limitations"])
        self.assertIn("AWS new-experience", entry["limitations"])
        self.assertIn("$75 pre-tax", entry["limitations"])
        self.assertEqual(result["merged_milestones"], 212)
        self.assertEqual(result["latest_pr"], 589)
        gates = {gate["id"]: gate["status"] for gate in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_pr589_aws_cap_and_jordan_tax_research_is_recorded_without_gate_promotion(self):
        result = validate(self.data)
        records = {entry["pr_number"]: entry for entry in self.data["milestones"]}
        entry = records[589]
        self.assertEqual(entry["pr_head_sha"], "8bae3c2fae904cbc8b09e18fa567ecc1b9748c06")
        self.assertEqual(entry["merge_sha"], "e23a75943a92dfae1757c75bc95a21f66b51dcb6")
        self.assertEqual(entry["ci_run_id"], 43411277843)
        for run_id in (43411060340, 43411068189, 43411061101, 43411068087, 43411276926):
            self.assertIn(str(run_id), entry["verification"])
        self.assertIn("$75", entry["limitations"])
        self.assertIn("zero projects", entry["limitations"])
        self.assertIn("UNVERIFIED", entry["limitations"])
        self.assertEqual(result["merged_milestones"], 212)
        self.assertEqual(result["latest_pr"], 589)
        gates = {gate["id"]: gate["status"] for gate in self.data["gates"]}
        self.assertEqual(gates["ai9-detection-quality"], "BLOCKED")
        self.assertEqual(gates["p01-managed-saas"], "BLOCKED")
        self.assertEqual(gates["codex-agent-runtime-acceptance"], "OPEN")

    def test_duplicate_achievement_rejected(self):
        self.data["milestones"].append(copy.deepcopy(self.data["milestones"][-1]))
        with self.assertRaisesRegex(InvalidLedger, "duplicate|not increasing"):
            validate(self.data)

    def test_truncated_sha_rejected(self):
        self.data["milestones"][0]["merge_sha"] = "7fbc0c8"
        with self.assertRaisesRegex(InvalidLedger, "SHA"):
            validate(self.data)

    def test_wrong_repo_rejected(self):
        self.data["repository"] = "someone/other"
        with self.assertRaisesRegex(InvalidLedger, "unexpected repository"):
            validate(self.data)

    def test_boolean_run_id_rejected(self):
        self.data["milestones"][0]["ci_run_id"] = True
        with self.assertRaisesRegex(InvalidLedger, "positive integer"):
            validate(self.data)

    def test_completed_gate_not_allowed_without_merge_evidence(self):
        self.data["gates"][0]["status"] = "COMPLETE"
        with self.assertRaisesRegex(InvalidLedger, "completed gates"):
            validate(self.data)

    def test_bad_source_path_rejected(self):
        self.data["gates"][0]["source"] = "docs/../private.md"
        with self.assertRaisesRegex(InvalidLedger, "docs path"):
            validate(self.data)

    def test_cli_rejects_malformed_json_without_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "broken.json"
            path.write_text('{"schema_version":', encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--file", str(path)],
                capture_output=True, text=True, check=False
            )
        self.assertEqual(run.returncode, 1)
        self.assertIn("MILESTONE_LEDGER_INVALID", run.stderr)

    def test_cli_machine_summary(self):
        run = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "milestone_ledger.py"), "--summary"],
            capture_output=True, text=True, check=False
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)["latest_pr"], self.data["milestones"][-1]["pr_number"])


if __name__ == "__main__":
    unittest.main()
