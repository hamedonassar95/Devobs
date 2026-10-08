"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const { execFileSync } = require("node:child_process");

async function evaluateLiveIncident({ github, context, core }) {
  const rawNumber = context.payload.inputs?.incident_number;
  if (!/^[1-9][0-9]*$/.test(String(rawNumber)) ||
      !Number.isSafeInteger(Number(rawNumber))) {
    core.setOutput("eligible", "false");
    core.setFailed("Phase 8B stopped: invalid incident number.");
    return;
  }

  const incidentNumber = Number(rawNumber);
  const { owner, repo } = context.repo;
  let issue;
  try {
    issue = (await github.rest.issues.get({
      owner, repo, issue_number: incidentNumber
    })).data;
  } catch {
    core.setOutput("eligible", "false");
    core.setFailed("Phase 8B stopped: incident evidence is unavailable.");
    return;
  }

  const evidenceErrors = [];
  let workflowRun = null;
  let comments = null;
  let openPullRequests = null;
  const markers = [...(issue.body || "").matchAll(/<!-- incident-run-id:([^\s]+) -->/g)]
    .map(match => match[1]);

  if (markers.length === 1 && /^[1-9][0-9]*$/.test(markers[0]) &&
      Number.isSafeInteger(Number(markers[0]))) {
    const runId = Number(markers[0]);
    try {
      const response = await github.rest.actions.getWorkflowRun({ owner, repo, run_id: runId });
      const jobs = await github.paginate(github.rest.actions.listJobsForWorkflowRun, {
        owner, repo, run_id: runId, per_page: 100
      });
      workflowRun = {
        id: response.data.id,
        name: response.data.name,
        status: response.data.status,
        conclusion: response.data.conclusion,
        head_branch: response.data.head_branch,
        head_sha: response.data.head_sha,
        jobs: jobs.map(job => ({ name: job.name, conclusion: job.conclusion }))
      };
    } catch {
      evidenceErrors.push("source workflow run or jobs unavailable");
    }
  }

  try {
    const values = await github.paginate(github.rest.issues.listComments, {
      owner, repo, issue_number: incidentNumber, per_page: 100
    });
    comments = values.map(comment => ({
      user: comment.user?.login || "",
      body: comment.body || ""
    }));
  } catch {
    evidenceErrors.push("incident comments unavailable");
  }

  try {
    const values = await github.paginate(github.rest.pulls.list, {
      owner, repo, state: "open", per_page: 100
    });
    openPullRequests = values.map(pr => ({
      head_ref: pr.head?.ref || "",
      body: pr.body || ""
    }));
  } catch {
    evidenceErrors.push("open pull requests unavailable");
  }

  const record = {
    issue: {
      number: issue.number,
      title: issue.title,
      state: issue.state,
      user: issue.user?.login || "",
      body: issue.body || ""
    },
    workflow_run: workflowRun,
    comments,
    open_pull_requests: openPullRequests,
    evidence_errors: evidenceErrors
  };

  const tmpPath = path.join(os.tmpdir(), `phase8-live-policy-${process.pid}.json`);
  let plan;
  try {
    fs.writeFileSync(tmpPath, JSON.stringify(record), { mode: 0o600 });
    plan = JSON.parse(execFileSync(
      "python3",
      ["scripts/phase8_live_planner.py", tmpPath],
      { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }
    ));
  } catch {
    core.setOutput("eligible", "false");
    core.setFailed("Phase 8B stopped: deterministic live policy evaluation failed.");
    return;
  } finally {
    try { fs.unlinkSync(tmpPath); } catch {}
  }

  core.setOutput("eligible", String(plan.eligible === true));
  if (plan.eligible !== true || plan.status !== "ELIGIBLE" ||
      plan.phase8b_authorized !== false || plan.repository_write_authority !== false) {
    core.setFailed("Phase 8B stopped: live recovery policy did not pass.");
    return;
  }
  core.info(`Live Phase 8A gate passed for incident #${incidentNumber}; safe-output restrictions remain active.`);
}

module.exports = { evaluateLiveIncident };
