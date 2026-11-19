"""Behavioral tests for the offline Graphify portfolio orchestrator.

Every test uses synthetic local repositories and a fake Graphify runner; no
network call, real extraction, upload, hook or dependency on an installed
Graphify release is required.
"""
import contextlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "integrations"))
import graphify_portfolio as gp  # noqa: E402

PINNED = gp.PINNED_GRAPHIFY_VERSION


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True)


def make_repo(base, name, remote, branch="main", dirty=False):
    path = pathlib.Path(base) / name
    path.mkdir(parents=True)
    subprocess.run(
        ["git", "init", "-q", "-b", branch, str(path)], check=True, capture_output=True, text=True
    )
    _git(path, "config", "user.name", "Graphify Test")
    _git(path, "config", "user.email", "graphify-test@example.invalid")
    (path / "module.py").write_text("def answer():\n    return 42\n", encoding="utf-8")
    _git(path, "add", "module.py")
    _git(path, "commit", "-q", "-m", "synthetic")
    if remote:
        _git(path, "remote", "add", "origin", remote)
    if dirty:
        (path / "untracked.txt").write_text("pending\n", encoding="utf-8")
    return path


class FakeRunner:
    def __init__(self, repo=None, version=f"graphify {PINNED}", exit_code=0,
                 create_graph=True, mutate=False):
        self.repo = repo
        self.version = version
        self.exit_code = exit_code
        self.create_graph = create_graph
        self.mutate = mutate
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, self.version + "\n", "")
        if self.mutate and self.repo is not None:
            (self.repo / "changed-during-run.txt").write_text("x", encoding="utf-8")
        if self.create_graph and "--out" in argv:
            out = pathlib.Path(argv[argv.index("--out") + 1])
            graph = out / "graphify-out" / "graph.json"
            graph.parent.mkdir(parents=True, exist_ok=True)
            graph.write_text(
                json.dumps({"nodes": [{"id": "a"}, {"id": "b"}], "links": [{"source": "a", "target": "b"}]}),
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(argv, self.exit_code, "extract ok\n", "")

    def extraction_calls(self):
        return [call for call in self.calls if call[0][1:2] == ["extract"]]


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_main_and_master_are_both_eligible(self):
        make_repo(self.root, "alpha", "https://github.com/hamedonassar95/alpha.git", "main")
        make_repo(self.root, "beta", "git@github.com:hamedonassar95/beta.git", "master")
        repos, skipped = gp.discover(self.root)
        self.assertEqual(skipped, [])
        self.assertEqual(sorted(r.name for r in repos), ["alpha", "beta"])
        self.assertTrue(all(r.eligible for r in repos))
        self.assertEqual({r.branch for r in repos}, {"main", "master"})

    def test_unlisted_owner_and_non_github_remote_are_blocked(self):
        make_repo(self.root, "foreign", "https://github.com/someone-else/foreign.git")
        make_repo(self.root, "local", str(self.root / "local"))
        repos, _ = gp.discover(self.root)
        by_name = {r.name: r for r in repos}
        self.assertFalse(by_name["foreign"].authorized)
        self.assertIn("origin owner 'someone-else' is not hamedonassar95", by_name["foreign"].reasons)
        self.assertIn("origin is not a supported github.com remote", by_name["local"].reasons)
        self.assertFalse(by_name["foreign"].eligible)
        self.assertFalse(by_name["local"].eligible)

    def test_feature_branch_and_dirty_tree_are_blocked(self):
        make_repo(self.root, "feature", "https://github.com/hamedonassar95/feature.git", "feature/x")
        make_repo(self.root, "dirty", "https://github.com/hamedonassar95/dirty.git", "main", dirty=True)
        repos, _ = gp.discover(self.root)
        by_name = {r.name: r for r in repos}
        self.assertIn("branch 'feature/x' is not one of main, master", by_name["feature"].reasons)
        self.assertIn("working tree has uncommitted changes", by_name["dirty"].reasons)
        self.assertFalse(by_name["dirty"].eligible)

    def test_duplicate_repository_names_are_refused(self):
        make_repo(self.root, "demo", "https://github.com/hamedonassar95/demo.git")
        other_root = self.root / "elsewhere"
        other_root.mkdir()
        make_repo(other_root, "demo", "https://github.com/hamedonassar95/demo.git")
        with self.assertRaisesRegex(gp.PortfolioError, "duplicate repository name 'demo'"):
            gp.discover(self.root, [other_root / "demo"])

    def test_linked_worktree_is_skipped_not_double_counted(self):
        make_repo(self.root, "real", "https://github.com/hamedonassar95/real.git")
        linked = self.root / "linked"
        linked.mkdir()
        (linked / ".git").write_text("gitdir: ../real/.git/worktrees/linked\n", encoding="utf-8")
        repos, skipped = gp.discover(self.root)
        self.assertEqual([r.name for r in repos], ["real"])
        self.assertEqual(skipped[0]["reason"], "linked worktree or submodule")

    def test_remote_parsing_variants(self):
        expected = ("hamedonassar95", "CineForge-AI")
        for url in (
            "https://github.com/hamedonassar95/CineForge-AI",
            "https://github.com/hamedonassar95/CineForge-AI.git",
            "https://github.com/hamedonassar95/CineForge-AI.git/",
            "git@github.com:hamedonassar95/CineForge-AI.git",
            "ssh://git@github.com/hamedonassar95/CineForge-AI.git",
        ):
            self.assertEqual(gp.parse_github_remote(url), expected, url)
        for url in (
            "https://gitlab.com/hamedonassar95/Devobs.git",
            "https://github.com/hamedonassar95/Devobs.git/extra",
            "file:///C:/repos/Devobs",
            "",
        ):
            self.assertIsNone(gp.parse_github_remote(url), url)


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "portfolio"
        self.root.mkdir()
        self.repo = make_repo(self.root, "demo", "https://github.com/hamedonassar95/demo.git")
        self.repos = [gp.inspect_repository(self.repo)]
        self.out = pathlib.Path(self.tmp.name) / "graphs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_output_root_inside_repository_is_refused(self):
        with self.assertRaisesRegex(gp.PortfolioError, "overlaps the source repository"):
            gp.validate_output_root(self.repo / "graphs", self.repos)

    def test_output_root_containing_repository_is_refused(self):
        with self.assertRaisesRegex(gp.PortfolioError, "overlaps the source repository"):
            gp.validate_output_root(self.root, self.repos)

    def test_external_output_root_is_accepted(self):
        self.assertEqual(gp.validate_output_root(self.out, self.repos), self.out.resolve())

    def test_plan_does_not_touch_disk(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        actions = gp.plan(self.repos, self.out, ["demo"])
        self.assertTrue(actions[0]["would_execute"])
        after = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        self.assertEqual(before, after)
        self.assertFalse(self.out.exists())

    def test_plan_rejects_unknown_selection(self):
        with self.assertRaisesRegex(gp.PortfolioError, "unknown repository selection"):
            gp.plan(self.repos, self.out, ["missing"])

    def test_execute_requires_explicit_repository_and_mode(self):
        out = io.StringIO()
        with contextlib.redirect_stderr(out):
            code = gp.main(["--root", str(self.root), "--out-root", str(self.out), "--execute", "--json"])
        self.assertEqual(code, 2)
        self.assertIn("--execute requires at least one explicit --only", out.getvalue())
        self.assertFalse(self.out.exists())

    def test_execute_of_blocked_repository_is_refused(self):
        make_repo(self.root, "pending", "https://github.com/hamedonassar95/pending.git", dirty=True)
        out = io.StringIO()
        with contextlib.redirect_stderr(out):
            code = gp.main(
                ["--root", str(self.root), "--out-root", str(self.out),
                 "--execute", "--only", "pending", "--json"]
            )
        self.assertEqual(code, 2)
        self.assertIn("not eligible", out.getvalue())
        self.assertFalse(self.out.exists())


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "portfolio"
        self.root.mkdir()
        self.repo = make_repo(self.root, "demo", "https://github.com/hamedonassar95/demo.git")
        self.repository = gp.inspect_repository(self.repo)
        self.out = pathlib.Path(self.tmp.name) / "graphs"

    def tearDown(self):
        self.tmp.cleanup()

    def test_command_is_offline_ast_only_and_writes_outside_repository(self):
        runner = FakeRunner(self.repo)
        record = gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        argv, kwargs = runner.extraction_calls()[0]
        self.assertEqual(
            argv, ["graphify", "extract", str(self.repo.resolve()), "--code-only",
                   "--out", str(self.out.resolve() / "demo" / self.repository.head)]
        )
        self.assertNotIn("--backend", argv)
        self.assertEqual(kwargs["env"]["GRAPHIFY_BACKEND"], "none")
        self.assertEqual(kwargs["env"]["GRAPHIFY_QUERY_LOG_DISABLE"], "1")
        for key in gp.PROVIDER_KEY_VARS:
            if key in kwargs["env"]:
                self.assertEqual(kwargs["env"][key], "")
        self.assertEqual(record["status"], "extracted")
        self.assertIsNone(record["failure"])
        self.assertEqual(record["graph"]["nodes"], 2)
        self.assertEqual(record["graph"]["edges"], 1)
        self.assertFalse(gp.is_within(pathlib.Path(record["graph"]["path"]), self.repo))
        self.assertTrue((self.out / "demo" / self.repository.head / "run.json").is_file())

    def test_run_record_never_contains_provider_values(self):
        runner = FakeRunner(self.repo)
        gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        record = json.loads((self.out / "demo" / self.repository.head / "run.json").read_text(encoding="utf-8"))
        self.assertEqual(
            set(record["environment"]),
            {"GRAPHIFY_BACKEND", "GRAPHIFY_QUERY_LOG_DISABLE", "provider_key_variables_blanked"},
        )
        self.assertEqual(
            record["environment"]["provider_key_variables_blanked"], list(gp.PROVIDER_KEY_VARS)
        )
        self.assertEqual(record["environment"]["GRAPHIFY_BACKEND"], "none")

    def test_version_mismatch_fails_closed_without_extraction(self):
        runner = FakeRunner(self.repo, version="graphify 0.9.200")
        with self.assertRaisesRegex(gp.PortfolioError, "not the pinned 0.9.112"):
            gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        self.assertEqual(runner.extraction_calls(), [])
        self.assertFalse(self.out.exists())

    def test_existing_output_directory_is_not_overwritten(self):
        runner = FakeRunner(self.repo)
        gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        with self.assertRaisesRegex(gp.PortfolioError, "refusing to overwrite"):
            gp.execute_repository(self.repository, self.out, "graphify", run=runner)

    def test_nonzero_exit_is_a_failure(self):
        runner = FakeRunner(self.repo, exit_code=7)
        record = gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        self.assertEqual(record["status"], "failed")
        self.assertIn("exited 7", record["failure"])
        self.assertIsNone(record["graph"])

    def test_missing_graph_json_is_a_failure(self):
        runner = FakeRunner(self.repo, create_graph=False)
        record = gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        self.assertEqual(record["status"], "failed")
        self.assertIn("did not write graph.json", record["failure"])

    def test_repository_mutation_during_run_is_a_failure(self):
        runner = FakeRunner(self.repo, mutate=True)
        record = gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        self.assertEqual(record["status"], "failed")
        self.assertFalse(record["repository_unchanged"])
        self.assertIn("changed during extraction", record["failure"])

    def test_ineligible_repository_is_rejected_before_any_command(self):
        (self.repo / "untracked.txt").write_text("pending\n", encoding="utf-8")
        dirty = gp.inspect_repository(self.repo)
        runner = FakeRunner(self.repo)
        with self.assertRaisesRegex(gp.PortfolioError, "not eligible"):
            gp.execute_repository(dirty, self.out, "graphify", run=runner)
        self.assertEqual(runner.calls, [])


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "portfolio"
        self.root.mkdir()
        self.out = pathlib.Path(self.tmp.name) / "graphs"
        make_repo(self.root, "alpha", "https://github.com/hamedonassar95/alpha.git", "main")
        make_repo(self.root, "gamma", "https://github.com/hamedonassar95/gamma.git", "feature/x")

    def tearDown(self):
        self.tmp.cleanup()

    def test_dry_run_is_default_and_writes_nothing(self):
        before = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = gp.main(["--root", str(self.root), "--out-root", str(self.out), "--json"])
        report = json.loads(stream.getvalue())
        after = sorted(p.relative_to(self.root) for p in self.root.rglob("*"))
        self.assertEqual(code, 0)
        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["status"], "dry-run")
        self.assertEqual(before, after)
        self.assertFalse(self.out.exists())
        states = {entry["name"]: entry["eligible"] for entry in report["plan"]}
        self.assertEqual(states, {"alpha": True, "gamma": False})
        self.assertNotIn("run", report["plan"][0])

    def test_missing_scan_root_fails_closed(self):
        stream = io.StringIO()
        with contextlib.redirect_stderr(stream):
            code = gp.main(["--root", str(self.root / "absent"), "--out-root", str(self.out), "--json"])
        self.assertEqual(code, 2)
        self.assertIn("scan root does not exist", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
