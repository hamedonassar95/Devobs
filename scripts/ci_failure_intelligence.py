"""Read-only GitHub Actions CI failure intelligence for Devobs.

Deterministic, evidence-based diagnostics. Never modifies code, reruns workflows,
merges PRs, or deploys. Findings are labeled VERIFIED/INFERRED/UNVERIFIED.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FINDING_VERIFIED = "VERIFIED"
FINDING_INFERRED = "INFERRED"
FINDING_UNVERIFIED = "UNVERIFIED"

CATEGORY_CODE = "code"
CATEGORY_INFRASTRUCTURE = "infrastructure"
CATEGORY_FLAKY_OR_EXTERNAL = "flaky-or-external"
CATEGORY_AMBIGUOUS = "ambiguous"

SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s\"']+"),
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password|passwd|pwd|client_secret|private_key)\s*[=:]\s*)([^\s\"',;]+)"),
    re.compile(r"(?i)(\"(?:api_key|token|secret|password|client_secret|private_key|authorization)\"\s*:\s*\")([^\"]+)"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----)(?:.|\n)*?(-----END [A-Z ]*PRIVATE KEY-----)"),
]

FAILURE_SIGNATURE_RULES: list[tuple[str, re.Pattern[str], str, str]] = [
    ("test-failure", re.compile(r"(?im)\bFAILED\b|AssertionError|Traceback \(most recent call last\)|\bFAIL:\s"), CATEGORY_CODE, FINDING_VERIFIED),
    ("lint-or-type", re.compile(r"(?im)\bruff\b.*error|mypy\b.*error|eslint\b|TS\d{4,5}|type check failed"), CATEGORY_CODE, FINDING_VERIFIED),
    ("dependency-install", re.compile(r"(?im)\bnpm ERR!|\bpip(?:3)? install\b.*(failed|error)|Could not find a version|ResolutionImpossible|ETARGET"), CATEGORY_CODE, FINDING_INFERRED),
    ("build-failure", re.compile(r"(?im)\bbuild failed\b|compilation failed|SyntaxError|ModuleNotFoundError|ImportError"), CATEGORY_CODE, FINDING_VERIFIED),
    ("timeout", re.compile(r"(?im)\btimed? out\b|timeout exceeded|ETIMEDOUT"), CATEGORY_INFRASTRUCTURE, FINDING_INFERRED),
    ("rate-limit", re.compile(r"(?im)\brate limit\b|secondary rate limit|429\b.*rate|abuse detection"), CATEGORY_INFRASTRUCTURE, FINDING_VERIFIED),
    ("network", re.compile(r"(?im)\bconnection reset\b|ECONNRESET|ENOTFOUND|EAI_AGAIN|Temporary failure in name resolution|Could not resolve host|502 Bad Gateway|503 Service Unavailable"), CATEGORY_INFRASTRUCTURE, FINDING_VERIFIED),
    ("runner-infra", re.compile(r"(?im)\brunner lost communication\b|No space left on device|disk quota exceeded|killed signal|out of memory|OOMKilled|internal server error from github"), CATEGORY_INFRASTRUCTURE, FINDING_VERIFIED),
    ("auth-permission", re.compile(r"(?im)\bResource not accessible by integration\b|Bad credentials|403 Forbidden|401 Unauthorized|permission denied"), CATEGORY_AMBIGUOUS, FINDING_INFERRED),
]


class AISummarizer(Protocol):
    def summarize(self, report: dict[str, Any]) -> str: ...


@dataclass
class NullAISummarizer:
    def summarize(self, report: dict[str, Any]) -> str:
        top = report.get("top_findings", [])
        if not top:
            return "Deterministic analysis found no failed jobs. AI summary unavailable."
        first = top[0]
        return (
            f"Deterministic summary: {first.get('category', 'ambiguous')} failure in "
            f"{first.get('job', 'unknown job')} / {first.get('step', 'unknown step')}. "
            f"Confidence {first.get('confidence', 'UNVERIFIED')}. AI summary unavailable."
        )


class GitHubActionsClient:
    """Read-only GitHub Actions API client."""

    def __init__(self, token: str | None = None, api_root: str = "https://api.github.com"):
        self.token = token
        self.api_root = api_root.rstrip("/")

    def _get_json(self, path: str) -> dict[str, Any]:
        url = path if path.startswith("http") else f"{self.api_root}{path}"
        req = Request(url, headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "devobs-ci-failure-intelligence",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
        })
        try:
            with urlopen(req, timeout=30) as resp:  # nosec B310 - controlled GitHub API URL
                return json.loads(resp.read().decode("utf-8"))
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"github_api_error:{exc.code}:{redact_secrets(body)}") from exc
        except URLError as exc:
            raise RuntimeError(f"github_api_unreachable:{exc.reason}") from exc

    def get_workflow_run(self, repo: str, run_id: str | int) -> dict[str, Any]:
        return self._get_json(f"/repos/{repo}/actions/runs/{run_id}")

    def get_jobs_for_run(self, repo: str, run_id: str | int) -> dict[str, Any]:
        return self._get_json(f"/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100")


def redact_secrets(text: Any) -> str:
    if text is None:
        return ""
    value = str(text)
    for pat in SECRET_PATTERNS:
        if pat.pattern.startswith("(?i)(-----BEGIN"):
            value = pat.sub(r"\1\n[REDACTED_PRIVATE_KEY]\n\2", value)
        elif pat.groups >= 2:
            value = pat.sub(lambda m: m.group(1) + "[REDACTED]", value)
        else:
            value = pat.sub("[REDACTED]", value)
    return value


def normalize_log(text: str) -> str:
    redacted = redact_secrets(text)
    redacted = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "<TS>", redacted)
    redacted = re.sub(r"0x[0-9a-fA-F]+", "<HEX>", redacted)
    redacted = re.sub(r"\b[0-9a-f]{40}\b", "<SHA>", redacted)
    redacted = re.sub(r"\b\d+\b", "<N>", redacted)
    redacted = re.sub(r"\s+", " ", redacted).strip().lower()
    return redacted[:400]


def signature_id(text: str) -> str:
    return hashlib.sha256(normalize_log(text).encode("utf-8")).hexdigest()[:16]
def classify_failure(text: str, job_name: str = "", step_name: str = "") -> dict[str, Any]:
    haystack = "\n".join([job_name, step_name, text or ""])
    for sig_name, pat, category, confidence in FAILURE_SIGNATURE_RULES:
        m = pat.search(haystack)
        if m:
            excerpt = redact_secrets(m.group(0))[:160]
            return {
                "signature_name": sig_name,
                "category": category,
                "confidence": confidence,
                "evidence_excerpt": excerpt,
                "rule": pat.pattern,
            }
    return {
        "signature_name": "unknown-failure",
        "category": CATEGORY_AMBIGUOUS,
        "confidence": FINDING_UNVERIFIED,
        "evidence_excerpt": redact_secrets((text or "").strip())[:160],
        "rule": "no-match",
    }


def _safe_jobs(run_metadata: dict[str, Any] | None, jobs_data: dict[str, Any] | None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    jobs: list[dict[str, Any]] = []
    if not isinstance(run_metadata, dict):
        findings.append(_finding("run-metadata", "missing-run-metadata", CATEGORY_AMBIGUOUS, FINDING_UNVERIFIED,
                                 "unknown", "unknown", "Workflow run metadata is missing or invalid.",
                                 "metadata.run", "Fail closed: cannot diagnose without run metadata."))
        return jobs, findings
    if not isinstance(jobs_data, dict):
        findings.append(_finding("jobs", "missing-jobs", CATEGORY_AMBIGUOUS, FINDING_UNVERIFIED,
                                 "unknown", "unknown", "Jobs payload is missing or invalid.",
                                 "metadata.jobs", "Fail closed: cannot identify failing jobs."))
        return jobs, findings
    raw_jobs = jobs_data.get("jobs")
    if not isinstance(raw_jobs, list):
        findings.append(_finding("jobs", "missing-jobs", CATEGORY_AMBIGUOUS, FINDING_UNVERIFIED,
                                 "unknown", "unknown", "Jobs payload has no jobs list.",
                                 "metadata.jobs", "Fail closed: jobs list missing."))
        return jobs, findings
    for j in raw_jobs:
        if isinstance(j, dict):
            jobs.append(j)
    return jobs, findings


def _finding(job: str, step: str, category: str, confidence: str, sig: str, sig_id: str, message: str, evidence_ref: str, detail: str) -> dict[str, Any]:
    return {
        "job": job,
        "step": step,
        "category": category,
        "confidence": confidence,
        "signature": sig,
        "signature_id": sig_id,
        "message": redact_secrets(message),
        "evidence_ref": evidence_ref,
        "detail": redact_secrets(detail),
    }


def _job_failed(job: dict[str, Any]) -> bool:
    conclusion = str(job.get("conclusion") or "").lower()
    return conclusion in {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}


def _step_failed(step: dict[str, Any]) -> bool:
    conclusion = str(step.get("conclusion") or "").lower()
    return conclusion in {"failure", "timed_out", "cancelled", "action_required", "startup_failure"}


def detect_repeated_signatures(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, dict[str, Any]] = {}
    for f in findings:
        sid = f.get("signature_id")
        if not sid or sid == "none":
            continue
        entry = counts.setdefault(sid, {"signature_id": sid, "signature": f.get("signature"), "count": 0, "occurrences": []})
        entry["count"] += 1
        entry["occurrences"].append({"job": f.get("job"), "step": f.get("step"), "evidence_ref": f.get("evidence_ref")})
    repeated = [v for v in counts.values() if v["count"] > 1]
    repeated.sort(key=lambda x: (-x["count"], x["signature_id"]))
    return repeated
def correlate_with_commit(run_metadata: dict[str, Any], findings: list[dict[str, Any]]) -> dict[str, Any]:
    sha = str(run_metadata.get("head_sha") or run_metadata.get("head_commit", {}).get("id") or "")
    branch = str(run_metadata.get("head_branch") or "")
    repo = str(run_metadata.get("repository", {}).get("full_name") or run_metadata.get("repository") or "")
    msg = str(run_metadata.get("head_commit", {}).get("message") or "")
    evidence = {
        "head_sha": sha or "UNKNOWN",
        "head_branch": branch or "UNKNOWN",
        "repository": repo or "UNKNOWN",
        "head_commit_message": redact_secrets(msg)[:200] if msg else "UNKNOWN",
        "confidence": FINDING_VERIFIED if sha else FINDING_UNVERIFIED,
        "notes": [],
    }
    if not sha:
        evidence["notes"].append("Missing head_sha; commit correlation cannot be verified.")
    code_related = [f for f in findings if f.get("category") == CATEGORY_CODE]
    infra_related = [f for f in findings if f.get("category") == CATEGORY_INFRASTRUCTURE]
    if code_related and sha:
        evidence["notes"].append("Code-category failures present; inspect changed files at head_sha before proposing fixes.")
    if infra_related and not code_related:
        evidence["notes"].append("Only infrastructure-category failures detected; code correlation is weak/inferred.")
    if not findings:
        evidence["notes"].append("No failing jobs detected.")
    return evidence


def _extract_log_text(job: dict[str, Any], step: dict[str, Any] | None = None) -> str:
    chunks = []
    for src in (step or {}, job):
        for key in ("log", "logs", "log_excerpt", "output", "message"):
            val = src.get(key)
            if isinstance(val, str) and val.strip():
                chunks.append(val)
    return "\n".join(chunks)


def analyze_run(
    run_metadata: dict[str, Any] | None,
    jobs_data: dict[str, Any] | None,
    *,
    ai_summarizer: AISummarizer | None = None,
) -> dict[str, Any]:
    jobs, meta_findings = _safe_jobs(run_metadata, jobs_data)
    findings: list[dict[str, Any]] = list(meta_findings)
    run = run_metadata if isinstance(run_metadata, dict) else {}

    for idx, job in enumerate(jobs):
        name = str(job.get("name") or f"job-{idx}")
        job_ref = f"jobs[{idx}]"
        if not _job_failed(job):
            continue
        steps = job.get("steps") if isinstance(job.get("steps"), list) else []
        failed_steps = [s for s in steps if isinstance(s, dict) and _step_failed(s)]
        if not failed_steps:
            log_text = _extract_log_text(job)
            cls = classify_failure(log_text, name, "")
            findings.append(_finding(name, "unknown", cls["category"], cls["confidence"], cls["signature_name"],
                                     signature_id(name + cls["signature_name"] + log_text), "Job failed without failed step details.",
                                     job_ref, cls["evidence_excerpt"] or "No log excerpt available."))
            continue
        for sidx, step in enumerate(failed_steps):
            step_name = str(step.get("name") or f"step-{sidx}")
            log_text = _extract_log_text(job, step)
            cls = classify_failure(log_text, name, step_name)
            evidence_ref = f"{job_ref}.steps[{sidx}]"
            detail = cls["evidence_excerpt"] or "No log excerpt available; classification may be ambiguous."
            confidence = cls["confidence"]
            if not log_text.strip():
                confidence = FINDING_UNVERIFIED if cls["category"] == CATEGORY_AMBIGUOUS else FINDING_INFERRED
                detail = "No log excerpt available; classification based on limited metadata."
            findings.append(_finding(name, step_name, cls["category"], confidence, cls["signature_name"],
                                     signature_id(cls["signature_name"] + "|" + normalize_log(log_text or (name + " " + step_name))),
                                     f"Failed step classified as {cls['signature_name']}.", evidence_ref, detail))

    repeated = detect_repeated_signatures(findings)
    correlation = correlate_with_commit(run, findings)
    if repeated:
        for f in findings:
            if any(f.get("signature_id") == r["signature_id"] for r in repeated):
                f["repeated"] = True
                f.setdefault("detail", "")
    else:
        for f in findings:
            f["repeated"] = False

    categories = sorted({f.get("category", CATEGORY_AMBIGUOUS) for f in findings})
    has_code = CATEGORY_CODE in categories
    has_infra = CATEGORY_INFRASTRUCTURE in categories
    overall = CATEGORY_AMBIGUOUS
    if has_code and has_infra:
        overall = "mixed"
    elif has_code:
        overall = CATEGORY_CODE
    elif has_infra:
        overall = CATEGORY_INFRASTRUCTURE
    elif findings:
        overall = categories[0]

    summarizer = ai_summarizer or NullAISummarizer()
    try:
        ai_summary = redact_secrets(summarizer.summarize({"top_findings": findings[:5], "overall_category": overall, "run": correlation}))
        ai_status = "available" if not isinstance(summarizer, NullAISummarizer) else "unavailable"
    except Exception as exc:  # fail closed, deterministic report still returned
        ai_summary = f"AI summary unavailable: {redact_secrets(type(exc).__name__)}"
        ai_status = "error"

    report = {
        "schema_version": "1.0",
        "tool": "devobs-ci-failure-intelligence",
        "mode": "read-only",
        "run": {
            "repository": str(run.get("repository", {}).get("full_name") or run.get("repository") or "UNKNOWN"),
            "run_id": str(run.get("id") or run.get("run_id") or "UNKNOWN"),
            "workflow_name": str(run.get("name") or run.get("workflow_name") or "UNKNOWN"),
            "conclusion": str(run.get("conclusion") or "UNKNOWN"),
            "head_sha": str(run.get("head_sha") or "UNKNOWN"),
            "head_branch": str(run.get("head_branch") or "UNKNOWN"),
            "html_url": str(run.get("html_url") or "UNKNOWN"),
        },
        "overall_category": overall,
        "top_findings": findings,
        "repeated_signatures": repeated,
        "commit_correlation": correlation,
        "ai_summary": {"status": ai_status, "text": ai_summary},
        "guardrails": {
            "read_only": True,
            "modifies_code": False,
            "reruns_workflows": False,
            "merges_prs": False,
            "deploys": False,
        },
        "limitations": [
            "Diagnostic only; root cause is not invented when evidence is missing.",
            "GitHub API access may be unavailable; report can be generated from provided metadata/logs.",
            "Logs and metadata are treated as untrusted and redacted before reporting.",
        ],
    }
    return report
def render_markdown(report: dict[str, Any]) -> str:
    run = report.get("run", {})
    lines = [
        "# CI Failure Intelligence Report",
        "",
        f"- Repository: `{run.get('repository','UNKNOWN')}`",
        f"- Workflow: `{run.get('workflow_name','UNKNOWN')}`",
        f"- Run ID: `{run.get('run_id','UNKNOWN')}`",
        f"- Conclusion: `{run.get('conclusion','UNKNOWN')}`",
        f"- Head SHA: `{run.get('head_sha','UNKNOWN')}`",
        f"- Head branch: `{run.get('head_branch','UNKNOWN')}`",
        f"- Overall category: `{report.get('overall_category','ambiguous')}`",
        f"- AI summary status: `{report.get('ai_summary',{}).get('status','unavailable')}`",
        "",
        "## Top findings",
        "",
    ]
    findings = report.get("top_findings", [])
    if not findings:
        lines.append("- No failed jobs detected.")
    for f in findings:
        lines.append(
            f"- [{f.get('confidence','UNVERIFIED')}] `{f.get('category')}` {f.get('job')} / {f.get('step')} - "
            f"{f.get('message')} (sig={f.get('signature')}, repeated={f.get('repeated', False)}, ref={f.get('evidence_ref')})"
        )
        lines.append(f"  - detail: {f.get('detail','')}")
    lines.extend(["", "## Repeated signatures", ""])
    reps = report.get("repeated_signatures", [])
    if not reps:
        lines.append("- None detected.")
    for r in reps:
        lines.append(f"- `{r.get('signature_id')}` {r.get('signature')} count={r.get('count')}")
    corr = report.get("commit_correlation", {})
    lines.extend([
        "", "## Commit correlation", "",
        f"- confidence: `{corr.get('confidence','UNVERIFIED')}`",
        f"- head_sha: `{corr.get('head_sha','UNKNOWN')}`",
    ])
    for note in corr.get("notes", []):
        lines.append(f"- {note}")
    lines.extend(["", "## AI summary", "", redact_secrets(report.get('ai_summary',{}).get('text','')) , "", "## Guardrails", ""])
    for k, v in report.get("guardrails", {}).items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    return "\n".join(lines)


def load_json_file(path: str | Path) -> dict[str, Any]:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(f"invalid_json:{Path(path)}:{type(exc).__name__}") from exc


def _write_output(report: dict[str, Any], json_out: str | None, md_out: str | None) -> None:
    if json_out:
        Path(json_out).write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    if md_out:
        Path(md_out).write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only CI failure intelligence analyzer")
    parser.add_argument("--repo", help="owner/repo for GitHub API")
    parser.add_argument("--run-id", help="GitHub Actions run id")
    parser.add_argument("--token-env", default="GITHUB_TOKEN", help="Env var containing read-only token")
    parser.add_argument("--run-json", help="Path to workflow run metadata JSON (offline mode)")
    parser.add_argument("--jobs-json", help="Path to jobs JSON (offline mode)")
    parser.add_argument("--json-out", help="Write JSON report")
    parser.add_argument("--md-out", help="Write Markdown report")
    args = parser.parse_args(argv)

    run_meta = None
    jobs = None
    try:
        if args.run_json:
            run_meta = load_json_file(args.run_json)
        if args.jobs_json:
            jobs = load_json_file(args.jobs_json)
        if (run_meta is None or jobs is None) and args.repo and args.run_id:
            import os
            token = os.environ.get(args.token_env)
            client = GitHubActionsClient(token=token)
            run_meta = run_meta or client.get_workflow_run(args.repo, args.run_id)
            jobs = jobs or client.get_jobs_for_run(args.repo, args.run_id)
        if run_meta is None or jobs is None:
            report = analyze_run(run_meta, jobs)
            report["overall_category"] = CATEGORY_AMBIGUOUS
            report["top_findings"].append(_finding("input", "missing-input", CATEGORY_AMBIGUOUS, FINDING_UNVERIFIED,
                                                   "missing-input", "none", "Missing run/jobs input; cannot fetch GitHub data.",
                                                   "cli.args", "Provide --run-json and --jobs-json, or --repo and --run-id with API access."))
            _write_output(report, args.json_out, args.md_out)
            print(json.dumps({"status": "error", "reason": "missing_input"}, sort_keys=True))
            return 2
        report = analyze_run(run_meta, jobs)
        _write_output(report, args.json_out, args.md_out)
        print(json.dumps({"status": "ok", "overall_category": report["overall_category"], "findings": len(report["top_findings"])}, sort_keys=True))
        return 0
    except Exception as exc:
        report = analyze_run(run_meta if isinstance(run_meta, dict) else {}, jobs if isinstance(jobs, dict) else {})
        report["overall_category"] = CATEGORY_AMBIGUOUS
        report["top_findings"].append(_finding("runtime", "error", CATEGORY_AMBIGUOUS, FINDING_UNVERIFIED,
                                               "runtime-error", "none", "Analyzer failed closed.",
                                               "runtime", redact_secrets(f"{type(exc).__name__}:{exc}")))
        _write_output(report, args.json_out, args.md_out)
        print(json.dumps({"status": "error", "reason": type(exc).__name__}, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
