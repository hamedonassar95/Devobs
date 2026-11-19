"""Behavioral tests for the offline Graphify portfolio orchestrator.

Every test uses synthetic local repositories and a fake Graphify runner; no
network call, real extraction, upload, hook or dependency on an installed
Graphify release is required.
"""
import contextlib
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

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
                 create_graph=True, mutate=False, graph_payload=None,
                 stray_output=False, raise_exc=None,
                 stdout="extract ok\n", stderr=""):
        self.repo = repo
        self.version = version
        self.exit_code = exit_code
        self.create_graph = create_graph
        self.mutate = mutate
        self.graph_payload = graph_payload
        self.stray_output = stray_output
        self.raise_exc = raise_exc
        self.stdout = stdout
        self.stderr = stderr
        self.calls = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), kwargs))
        if argv[1:] == ["--version"]:
            return subprocess.CompletedProcess(argv, 0, self.version + "\n", "")
        if self.raise_exc is not None:
            raise self.raise_exc
        if self.mutate and self.repo is not None:
            (self.repo / "changed-during-run.txt").write_text("x", encoding="utf-8")
        if self.stray_output and self.repo is not None:
            stray = self.repo / "graphify-out"
            stray.mkdir(exist_ok=True)
            (stray / "graph.json").write_text("{}", encoding="utf-8")
        if self.create_graph and "--out" in argv:
            out = pathlib.Path(argv[argv.index("--out") + 1])
            graph = out / "graphify-out" / "graph.json"
            graph.parent.mkdir(parents=True, exist_ok=True)
            payload = self.graph_payload
            if payload is None:
                payload = {
                    "nodes": [{"id": "a"}, {"id": "b"}],
                    "links": [{"source": "a", "target": "b"}],
                }
            if isinstance(payload, str):
                graph.write_text(payload, encoding="utf-8")
            else:
                graph.write_text(json.dumps(payload), encoding="utf-8")
        return subprocess.CompletedProcess(argv, self.exit_code, self.stdout, self.stderr)

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


class EvidenceHardeningTests(unittest.TestCase):
    """Evidence written to run.json must not carry private or secret content."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "portfolio"
        self.root.mkdir()
        self.repo = make_repo(self.root, "demo", "https://github.com/hamedonassar95/demo.git")
        self.repository = gp.inspect_repository(self.repo)
        self.out = pathlib.Path(self.tmp.name) / "graphs"

    def tearDown(self):
        self.tmp.cleanup()

    def _execute(self, **kwargs):
        runner = FakeRunner(self.repo, **kwargs)
        record = gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        evidence = (self.out / "demo" / self.repository.head / "run.json").read_text(
            encoding="utf-8"
        )
        return record, evidence, runner

    def test_raw_process_output_is_never_retained(self):
        secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        record, evidence, _ = self._execute(
            stdout=f"token={secret}\n",
            stderr=f"Authorization: Bearer {secret}\nprivate_module.py\n",
        )
        for key in ("stdout_tail", "stderr_tail", "diagnostics", "stdout", "stderr"):
            self.assertNotIn(key, record)
        self.assertNotIn(secret, evidence)
        self.assertNotIn("private_module.py", evidence)
        self.assertNotIn("Authorization", evidence)
        self.assertEqual(record["status"], "extracted")
        self.assertGreater(record["stdout_bytes"], 0)
        self.assertGreater(record["stderr_bytes"], 0)

    def test_network_upload_state_is_explicitly_unverified(self):
        record, evidence, _ = self._execute()
        self.assertEqual(record["evidence"]["network_uploads"], "UNVERIFIED")
        self.assertEqual(record["evidence"]["hooks_installed"], "NOT_PERFORMED")
        self.assertEqual(record["evidence"]["process_output"], "NOT_RETAINED")
        self.assertNotIn("network_uploads", record)
        self.assertNotIn("hooks_installed", record)
        self.assertEqual(json.loads(evidence)["evidence"]["network_uploads"], "UNVERIFIED")

    def test_origin_credentials_are_redacted_in_reports(self):
        secret = "ghp_" + "Z9y8X7w6V5u4T3s2R1q0P9o8N7m6L5k4J3i2"
        remote = f"https://x-access-token:{secret}@github.com/hamedonassar95/leaky.git"
        make_repo(self.root, "leaky", remote)
        leaky = gp.inspect_repository(self.root / "leaky")
        rendered = json.dumps(leaky.as_dict())
        self.assertNotIn(secret, rendered)
        self.assertIn("[REDACTED]", leaky.as_dict()["remote"])
        self.assertIn("github.com/hamedonassar95/leaky.git", leaky.as_dict()["remote"])

        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = gp.main(["--root", str(self.root), "--out-root", str(self.out), "--json"])
        self.assertEqual(code, 0)
        self.assertNotIn(secret, stream.getvalue())

    def test_version_probe_does_not_inherit_provider_keys(self):
        with unittest.mock.patch.dict(gp.os.environ, {"OPENAI_API_KEY": "sk-" + "x" * 32}):
            _, _, runner = self._execute()
        probes = [call for call in runner.calls if call[0][1:] == ["--version"]]
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0][1]["env"]["OPENAI_API_KEY"], "")

    def test_unpinned_version_text_is_redacted(self):
        secret = "sk-" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        runner = FakeRunner(self.repo, version=f"graphify {secret}")
        with self.assertRaises(gp.PortfolioError) as caught:
            gp.execute_repository(self.repository, self.out, "graphify", run=runner)
        self.assertNotIn(secret, str(caught.exception))
        self.assertIn("[REDACTED]", str(caught.exception))

    def test_withholding_fallback_writes_no_repository_content(self):
        with unittest.mock.patch.object(
            gp, "_assert_no_sensitive_material", side_effect=gp.PortfolioError("forced")
        ):
            record = gp.execute_repository(
                self.repository, self.out, "graphify", run=FakeRunner(self.repo)
            )
        self.assertEqual(record["status"], "failed")
        self.assertTrue(record["sensitive_evidence_withheld"])
        evidence = (self.out / "demo" / self.repository.head / "run.json").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("demo", evidence)
        self.assertNotIn("module.py", evidence)


class RedactionTests(unittest.TestCase):
    def test_secret_shapes_are_removed(self):
        values = [
            "ghp_" + "a" * 36,
            "github_pat_" + "b" * 30,
            "sk-" + "c" * 32,
            "AKIA" + "D" * 16,
            "AIza" + "e" * 35,
        ]
        for value in values:
            with self.subTest(value=value[:10]):
                rendered = json.dumps(gp._sanitize({"field": value}))
                self.assertNotIn(value, rendered)
                self.assertIn(gp._REDACTED, rendered)

    def test_hashes_and_paths_survive(self):
        sha = "ba66e853378bbbc9ca2b22ec57990ed37a1b4d80fee9b2d40565b85732d5c403"
        head = "4f9c2ab1e6d7c8b9a0f1e2d3c4b5a69788796a5b4c3d2e1f0091827364554637"
        sanitized = gp._sanitize(
            {"sha256": sha, "head": head, "path": r"C:\DevProjects\CineForge-AI"}
        )
        self.assertEqual(sanitized["sha256"], sha)
        self.assertEqual(sanitized["head"], head)
        self.assertEqual(sanitized["path"], r"C:\DevProjects\CineForge-AI")

    def test_url_userinfo_is_redacted_but_host_is_kept(self):
        value = gp.redact("https://user:pw@github.com/hamedonassar95/Devobs.git")
        self.assertEqual(value, "https://[REDACTED]@github.com/hamedonassar95/Devobs.git")

    def test_sanitizer_is_idempotent(self):
        once = gp.redact("https://user:pw@example.invalid/x?token=abcdef123456")
        self.assertEqual(gp.redact(once), once)


class GraphValidationTests(unittest.TestCase):
    """A structurally invalid graph must never be reported as extracted."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "portfolio"
        self.root.mkdir()
        self.repo = make_repo(self.root, "demo", "https://github.com/hamedonassar95/demo.git")
        self.repository = gp.inspect_repository(self.repo)
        self.counter = 0

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, payload, **kwargs):
        self.counter += 1
        out = pathlib.Path(self.tmp.name) / f"graphs-{self.counter}"
        record = gp.execute_repository(
            self.repository,
            out,
            "graphify",
            run=FakeRunner(self.repo, graph_payload=payload, **kwargs),
        )
        return record, out

    def test_malformed_json_fails_closed(self):
        record, out = self._run("{not valid json")
        self.assertEqual(record["status"], "failed")
        self.assertIn("not valid JSON", record["failure"])
        self.assertIsNone(record["graph"])
        self.assertTrue((out / "demo" / self.repository.head / "run.json").is_file())

    def test_non_object_root_fails_closed(self):
        record, _ = self._run([{"id": "a"}])
        self.assertEqual(record["status"], "failed")
        self.assertIn("root is not a JSON object", record["failure"])

    def test_missing_nodes_fails_closed(self):
        record, _ = self._run({"links": []})
        self.assertIn("'nodes' is missing", record["failure"])

    def test_empty_nodes_fails_closed(self):
        record, _ = self._run({"nodes": [], "links": []})
        self.assertIn("'nodes' is empty", record["failure"])

    def test_duplicate_node_ids_fail_without_echoing_ids(self):
        identifier = "private_owner_secret_module.py:handler"
        record, _ = self._run(
            {"nodes": [{"id": identifier}, {"id": identifier}], "links": []}
        )
        self.assertEqual(record["status"], "failed")
        self.assertIn("repeats an earlier id", record["failure"])
        self.assertNotIn(identifier, json.dumps(record))

    def test_dangling_link_fails_closed(self):
        record, _ = self._run(
            {"nodes": [{"id": "a"}], "links": [{"source": "a", "target": "b"}]}
        )
        self.assertIn("target that is not a node id", record["failure"])

    def test_non_string_node_id_fails_closed(self):
        record, _ = self._run({"nodes": [{"id": 7}], "links": []})
        self.assertIn("non-empty string id", record["failure"])

    def test_valid_graph_reports_file_derived_counts(self):
        payload = {
            "directed": False,
            "multigraph": False,
            "graph": {"schema_version": 1},
            "nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}],
            "links": [{"source": "a", "target": "b"}, {"source": "b", "target": "c"}],
        }
        record, out = self._run(payload)
        self.assertEqual(record["status"], "extracted")
        self.assertEqual(record["graph"]["nodes"], 3)
        self.assertEqual(record["graph"]["edges"], 2)
        written = out / "demo" / self.repository.head / "graphify-out" / "graph.json"
        self.assertEqual(
            record["graph"]["sha256"], hashlib.sha256(written.read_bytes()).hexdigest()
        )
        self.assertEqual(record["graph"]["bytes"], written.stat().st_size)

    def test_stray_ignored_output_in_repository_is_a_failure(self):
        (self.repo / ".gitignore").write_text("graphify-out/\n", encoding="utf-8")
        _git(self.repo, "add", ".gitignore")
        _git(self.repo, "commit", "-q", "-m", "ignore local graph output")
        repository = gp.inspect_repository(self.repo)
        record = gp.execute_repository(
            repository,
            pathlib.Path(self.tmp.name) / "graphs-stray",
            "graphify",
            run=FakeRunner(self.repo, stray_output=True),
        )
        self.assertEqual(record["status"], "failed")
        self.assertTrue(record["stray_graphify_out_in_repository"])
        self.assertTrue(record["repository_unchanged"])
        self.assertIn("graphify-out was created inside the source repository", record["failure"])

    def test_runner_exception_is_a_failure_not_a_crash(self):
        record, _ = self._run(
            None, raise_exc=subprocess.TimeoutExpired(cmd="graphify", timeout=1)
        )
        self.assertEqual(record["status"], "failed")
        self.assertIn("did not complete", record["failure"])
        self.assertIsNone(record["graph"])


if __name__ == "__main__":
    unittest.main()
