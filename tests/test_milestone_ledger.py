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

    def test_pr365_to_371_merges_are_recorded_without_promoting_readiness_gates(self):
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
        gates = {item["id"]: item["status"] for item in self.data["gates"]}
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
