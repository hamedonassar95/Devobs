import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = (
    ROOT / ".agents/skills/dev-lifecycle/scripts/check-status.sh",
    ROOT / ".claude/skills/dev-lifecycle/scripts/check-status.sh",
)
PHASES = (
    "requirements",
    "design",
    "planning",
    "implementation",
    "testing",
    "deployment",
    "monitoring",
)


class AiDevKitStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workdir = Path(self.temp.name)
        self.feature = "sample-feature"
        self.doc_root = Path("docs/ai")
        self.docs = {
            phase: self.doc_root / phase / f"{self.feature}.md"
            for phase in PHASES
        }
        for path in self.docs.values():
            absolute = self.workdir / path
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text("# fixture\n", encoding="utf-8")

        (self.workdir / self.docs["planning"]).write_text(
            "# Plan\n- [x] first task\n", encoding="utf-8"
        )
        (self.workdir / self.docs["implementation"]).write_text(
            "# Implementation\n\n## Lifecycle progress\n"
            "- [x] Phase 2: requirements reviewed\n"
            "- [x] Phase 3: design reviewed\n"
            "- [x] Phase 4: initial plan created after reviews\n",
            encoding="utf-8",
        )
        self.fixture = self.workdir / "lint-output.json"
        self.write_lint_result()

        self.fake_cli = self.workdir / "fake-ai-devkit"
        self.fake_cli.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" > \"$AI_DEVKIT_ARGS\"\n"
            "if [[ -n \"${FAKE_LINT_STDERR:-}\" ]]; then printf '%s\\n' \"$FAKE_LINT_STDERR\" >&2; fi\n"
            "cat \"$AI_DEVKIT_LINT_OUTPUT\"\n"
            "exit \"${FAKE_LINT_EXIT:-0}\"\n",
            encoding="utf-8",
        )
        self.fake_cli.chmod(0o755)
        self.fake_npx = self.workdir / "npx"
        self.fake_npx.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$@\" > \"$AI_DEVKIT_ARGS\"\n"
            "if [[ -n \"${FAKE_LINT_STDERR:-}\" ]]; then printf '%s\\n' \"$FAKE_LINT_STDERR\" >&2; fi\n"
            "cat \"$AI_DEVKIT_LINT_OUTPUT\"\n"
            "exit \"${FAKE_LINT_EXIT:-0}\"\n",
            encoding="utf-8",
        )
        self.fake_npx.chmod(0o755)
        self.args_file = self.workdir / "cli-args.txt"

    def lint_result(self, *, missing_phase=None, failed_check=None):
        checks = []
        for phase in PHASES:
            missing = phase == missing_phase
            path = (
                self.doc_root / phase / f"{self.feature}.md"
                if not missing
                else self.doc_root / phase / f"YYYY-MM-DD-feature-{self.feature}.md"
            )
            checks.append(
                {
                    "id": f"feature-doc-{phase}",
                    "level": "miss" if missing else "ok",
                    "category": "feature-docs",
                    "required": missing,
                    "message": path.as_posix(),
                }
            )

        if failed_check:
            checks.append(
                {
                    "id": failed_check,
                    "level": "miss",
                    "category": "git",
                    "required": True,
                    "message": "Branch feature-sample-feature does not exist",
                }
            )

        misses = sum(check["level"] == "miss" for check in checks)
        return {
            "cwd": str(self.workdir),
            "feature": {
                "raw": self.feature,
                "normalizedName": self.feature,
                "branchName": f"feature-{self.feature}",
            },
            "checks": checks,
            "summary": {
                "ok": len(checks) - misses,
                "miss": misses,
                "warn": 0,
                "requiredFailures": misses,
            },
            "pass": misses == 0,
            "exitCode": 1 if misses else 0,
        }

    def write_lint_result(self, *, missing_phase=None, failed_check=None):
        self.fixture.write_text(
            json.dumps(
                self.lint_result(
                    missing_phase=missing_phase,
                    failed_check=failed_check,
                )
            ),
            encoding="utf-8",
        )

    def run_script(
        self, script, *, lint_exit=0, feature=None, use_default_cli=False, lint_stderr="", cwd=None
    ):
        env = os.environ.copy()
        env.update(
            {
                "AI_DEVKIT_BIN": str(self.fake_cli),
                "AI_DEVKIT_LINT_OUTPUT": str(self.fixture),
                "AI_DEVKIT_ARGS": str(self.args_file),
                "FAKE_LINT_EXIT": str(lint_exit),
                "FAKE_LINT_STDERR": lint_stderr,
            }
        )
        if use_default_cli:
            env.pop("AI_DEVKIT_BIN", None)
            env["PATH"] = f"{self.workdir}{os.pathsep}{env['PATH']}"
        return subprocess.run(
            ["bash", str(script), feature or self.feature],
            cwd=cwd or self.workdir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_unexpected_lint_failure_does_not_recommend_a_lifecycle_phase(self):
        self.write_lint_result(failed_check="git-branch")
        for script in SCRIPTS:
            with self.subTest(script=script.parent.parent.parent.parent.name):
                result = self.run_script(script, lint_exit=1)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("--- Suggested phase ---", result.stdout)
                self.assertIn("AI DevKit lint failed", result.stdout)

    def test_missing_design_document_routes_to_design_review(self):
        self.write_lint_result(missing_phase="design")
        (self.workdir / self.docs["design"]).unlink()
        result = self.run_script(SCRIPTS[0], lint_exit=1)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 3 (Review Design) — no design document yet", result.stdout)

    def test_missing_requirements_routes_to_new_requirement(self):
        self.write_lint_result(missing_phase="requirements")
        (self.workdir / self.docs["requirements"]).unlink()
        result = self.run_script(SCRIPTS[0], lint_exit=1)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 1 (New Requirement) — no requirements doc yet", result.stdout)

    def test_missing_plan_routes_to_initial_plan_after_design_review(self):
        self.write_lint_result(missing_phase="planning")
        (self.workdir / self.docs["planning"]).unlink()
        result = self.run_script(SCRIPTS[0], lint_exit=1)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 4 (Create Initial Plan) — design exists but no planning doc", result.stdout)

    def test_markdown_links_do_not_count_as_incomplete_planning_tasks(self):
        (self.workdir / self.docs["planning"]).write_text(
            "# Plan\n- [Contributor guide](docs/AI_DEVKIT.md)\n",
            encoding="utf-8",
        )

        result = self.run_script(SCRIPTS[0])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Planning: 0/0 tasks done, 0 remaining", result.stdout)
        self.assertIn("Phase 4 (Create Initial Plan) — no planning tasks recorded", result.stdout)

    def test_successful_lint_uses_the_requested_feature_and_routes_remaining_work(self):
        result = self.run_script(SCRIPTS[0])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 7 (Check Implementation)", result.stdout)
        self.assertEqual(
            self.args_file.read_text(encoding="utf-8").splitlines(),
            ["lint", "--json", "--feature", self.feature],
        )

    def test_invocation_from_subdirectory_resolves_paths_from_repository_root(self):
        subprocess.run(["git", "init", "-q"], cwd=self.workdir, check=True)
        subdirectory = self.workdir / "nested" / "caller"
        subdirectory.mkdir(parents=True)

        result = self.run_script(SCRIPTS[0], cwd=subdirectory)

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 7 (Check Implementation)", result.stdout)

    def test_cli_normalized_name_may_differ_from_the_requested_feature(self):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        data["feature"]["raw"] = "Sample_Feature"
        data["feature"]["normalizedName"] = self.feature
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

        result = self.run_script(SCRIPTS[0], feature="Sample_Feature")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 7 (Check Implementation)", result.stdout)

    def test_configured_docs_root_is_taken_from_ai_devkit_json_paths(self):
        self.doc_root = Path("docs/ai/testing/feature-docs")
        self.docs = {
            phase: self.doc_root / phase / f"{self.feature}.md"
            for phase in PHASES
        }
        for path in self.docs.values():
            absolute = self.workdir / path
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.write_text("# fixture\n", encoding="utf-8")
        (self.workdir / self.docs["planning"]).write_text(
            "# Plan\n- [x] first task\n", encoding="utf-8"
        )
        (self.workdir / self.docs["implementation"]).write_text(
            "# Implementation\n\n## Lifecycle progress\n"
            "- [x] Phase 2: reviewed\n- [x] Phase 3: reviewed\n"
            "- [x] Phase 4: planned\n",
            encoding="utf-8",
        )
        self.write_lint_result()

        result = self.run_script(SCRIPTS[0])

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[EXISTS] docs/ai/testing/feature-docs/requirements/sample-feature.md", result.stdout)
        self.assertIn("Phase 7 (Check Implementation)", result.stdout)

    def test_missing_deployment_or_monitoring_docs_blocks_lifecycle_completion(self):
        implementation = self.workdir / self.docs["implementation"]
        implementation.write_text(
            "# Implementation\n\n## Lifecycle progress\n"
            "- [x] Phase 2: reviewed\n- [x] Phase 3: reviewed\n"
            "- [x] Phase 4: planned\n- [x] Phase 7: implemented\n"
            "- [x] Phase 8: tested\n- [x] Phase 9: reviewed\n",
            encoding="utf-8",
        )
        for phase in ("deployment", "monitoring"):
            with self.subTest(phase=phase):
                self.write_lint_result(missing_phase=phase)
                (self.workdir / self.docs[phase]).unlink()
                result = self.run_script(SCRIPTS[0], lint_exit=1)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(
                    f"required {phase} document is missing", result.stdout
                )
                self.assertNotIn("Lifecycle complete", result.stdout)
                absolute = self.workdir / self.docs[phase]
                absolute.parent.mkdir(parents=True, exist_ok=True)
                absolute.write_text("# fixture\n", encoding="utf-8")

    def test_cli_stderr_does_not_contaminate_json_output(self):
        result = self.run_script(SCRIPTS[0], lint_stderr="npm warn exec package download")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Phase 7 (Check Implementation)", result.stdout)

    def test_default_cli_uses_the_pinned_validated_release(self):
        result = self.run_script(SCRIPTS[0], use_default_cli=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            self.args_file.read_text(encoding="utf-8").splitlines(),
            ["--yes", "ai-devkit@0.70.1", "lint", "--json", "--feature", self.feature],
        )

    def test_lifecycle_checklist_advances_one_verified_phase_at_a_time(self):
        implementation = self.workdir / self.docs["implementation"]
        cases = (
            ("", "Phase 2 (Review Requirements)"),
            ("- [x] Phase 2: checked\n", "Phase 3 (Review Design)"),
            (
                "- [x] Phase 2: checked\n- [x] Phase 3: checked\n",
                "Phase 4 (Create Initial Plan)",
            ),
            (
                "- [x] Phase 2: checked\n- [x] Phase 3: checked\n"
                "- [x] Phase 4: checked\n",
                "Phase 7 (Check Implementation)",
            ),
            (
                "- [x] Phase 2: checked\n- [x] Phase 3: checked\n"
                "- [x] Phase 4: checked\n- [x] Phase 7: checked\n",
                "Phase 8 (Write Tests)",
            ),
            (
                "- [x] Phase 2: checked\n- [x] Phase 3: checked\n"
                "- [x] Phase 4: checked\n- [x] Phase 7: checked\n"
                "- [x] Phase 8: checked\n",
                "Phase 9 (Code Review)",
            ),
            (
                "- [x] Phase 2: checked\n- [x] Phase 3: checked\n"
                "- [x] Phase 4: checked\n- [x] Phase 7: checked\n"
                "- [x] Phase 8: checked\n"
                "- [x] Phase 9: checked\n",
                "Lifecycle complete",
            ),
        )
        for checklist, expected in cases:
            with self.subTest(expected=expected):
                implementation.write_text(
                    "# Implementation\n\n## Lifecycle progress\n" + checklist,
                    encoding="utf-8",
                )
                result = self.run_script(SCRIPTS[0])
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn(expected, result.stdout)

    def test_missing_testing_or_implementation_doc_stops_phase_routing(self):
        complete_reviews = (
            "# Implementation\n\n## Lifecycle progress\n"
            "- [x] Phase 2: requirements reviewed\n"
            "- [x] Phase 3: design reviewed\n"
        )
        implementation = self.workdir / self.docs["implementation"]
        for phase in ("testing", "implementation"):
            with self.subTest(phase=phase):
                self.write_lint_result(missing_phase=phase)
                if phase == "testing":
                    implementation.write_text(complete_reviews, encoding="utf-8")
                (self.workdir / self.docs[phase]).unlink()
                result = self.run_script(SCRIPTS[0], lint_exit=1)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"required {phase} document is missing", result.stdout)
                self.assertIn("No phase suggested", result.stdout)
                for suggested_phase in (2, 3, 4, 5, 7, 8, 9):
                    self.assertNotIn(f"Phase {suggested_phase} (", result.stdout)
                absolute = self.workdir / self.docs[phase]
                absolute.parent.mkdir(parents=True, exist_ok=True)
                absolute.write_text("# fixture\n", encoding="utf-8")

    def test_invalid_json_from_lint_stops_phase_routing(self):
        self.fixture.write_text("not json\n", encoding="utf-8")
        result = self.run_script(SCRIPTS[0], lint_exit=1)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_inconsistent_feature_doc_check_stops_phase_routing(self):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        requirements = next(
            check for check in data["checks"] if check["id"] == "feature-doc-requirements"
        )
        requirements["level"] = "warn"
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

        result = self.run_script(SCRIPTS[0])

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_lint_miss_for_an_existing_document_stops_phase_routing(self):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        requirements = next(
            check for check in data["checks"] if check["id"] == "feature-doc-requirements"
        )
        requirements.update(level="miss", required=True)
        data["summary"].update(ok=len(data["checks"]) - 1, miss=1, requiredFailures=1)
        data["pass"] = False
        data["exitCode"] = 1
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

        result = self.run_script(SCRIPTS[0], lint_exit=1)

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_lint_success_for_a_missing_document_stops_phase_routing(self):
        (self.workdir / self.docs["requirements"]).unlink()

        result = self.run_script(SCRIPTS[0])

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_lint_document_path_outside_repository_stops_phase_routing(self):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        requirements = next(
            check for check in data["checks"] if check["id"] == "feature-doc-requirements"
        )
        outside = self.workdir.parent / f"{self.workdir.name}-outside.md"
        outside.write_text("# outside repository\n", encoding="utf-8")
        self.addCleanup(outside.unlink, missing_ok=True)
        requirements["message"] = f"../{outside.name}"
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

        result = self.run_script(SCRIPTS[0])

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_lint_document_path_must_match_its_phase(self):
        data = json.loads(self.fixture.read_text(encoding="utf-8"))
        requirements = next(
            check for check in data["checks"] if check["id"] == "feature-doc-requirements"
        )
        requirements["message"] = self.docs["design"].as_posix()
        self.fixture.write_text(json.dumps(data), encoding="utf-8")

        result = self.run_script(SCRIPTS[0])

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("--- Suggested phase ---", result.stdout)

    def test_codex_and_claude_helpers_are_identical(self):
        self.assertEqual(SCRIPTS[0].read_bytes(), SCRIPTS[1].read_bytes())

    def test_init_template_uses_skill_and_generated_config_uses_name(self):
        template = json.loads((ROOT / "templates/ai-devkit.json").read_text(encoding="utf-8"))
        config = json.loads((ROOT / ".ai-devkit.json").read_text(encoding="utf-8"))
        template_skills = template["skills"]
        config_skills = config["skills"]

        self.assertEqual(
            template["registries"]["codeaholicguy/ai-devkit"],
            config["registries"]["codeaholicguy/ai-devkit"],
        )
        self.assertTrue(all("skill" in skill and "name" not in skill for skill in template_skills))
        self.assertTrue(all("name" in skill and "skill" not in skill for skill in config_skills))
        self.assertEqual(
            {skill["skill"] for skill in template_skills},
            {skill["name"] for skill in config_skills},
        )


if __name__ == "__main__":
    unittest.main()
