import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, writeFileSync, rmSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { PUBLIC_TARGETS } from '../assets/public-ci/portfolio-api.mjs';
import { inspectAndAnalyzePublicCi } from '../scripts/portfolio_ci_ai7_live.mjs';
import { buildActionArtifact } from '../scripts/portfolio_ai7_action_report.mjs';

const SHA = 'a'.repeat(40);
function response(url, value, status = 200) {
  const result = Response.json(value, { status });
  Object.defineProperty(result, 'url', { value: url });
  return result;
}
function fakePublicGitHub({ incomplete = new Set() } = {}) {
  return async (url, options) => {
    assert.equal(options.method, 'GET');
    assert.equal(options.credentials, 'omit');
    const target = PUBLIC_TARGETS.find(x => url.startsWith('https://api.github.com/repos/' + x.repo + '/'));
    assert.ok(target, 'unexpected GitHub API target');
    const i = PUBLIC_TARGETS.indexOf(target);
    if (incomplete.has(i)) return response(url, { error: 'PRIVATE_RAW_TEXT' }, 429);
    if (url.includes('/branches/')) {
      return response(url, { name: 'main', commit: { sha: SHA } });
    }
    return response(url, {
      total_count: 1,
      workflow_runs: [{
        id: 800 + i, run_attempt: 1, created_at: '2026-11-16T18:00:00Z',
        path: '.github/workflows/ci.yml', event: 'push', head_branch: 'main',
        head_sha: SHA, status: 'completed',
        conclusion: ['success', 'failure', 'timed_out', 'cancelled'][i],
        repository: { full_name: target.repo, private: false },
        head_repository: { full_name: target.repo, private: false },
        name: 'PRIVATE_RAW_TEXT',
      }],
    });
  };
}
const script = fileURLToPath(new URL('../scripts/portfolio_ai7_action_report.mjs', import.meta.url));

test('real one-command public CI and AI-7 output becomes a bounded reviewed artifact', async () => {
  const source = await inspectAndAnalyzePublicCi(fakePublicGitHub());
  const { artifact, markdown } = buildActionArtifact(source);
  assert.equal(artifact.status, 'complete_observation');
  assert.equal(artifact.eligible_count, 4);
  assert.equal(artifact.analysis.summary.ci_event_count, 4);
  assert.equal(artifact.analysis.summary.failed_ci_count, 2);
  assert.equal(artifact.analysis.summary.recommendation_count, 0);
  assert.deepEqual(artifact.analysis.pipeline.map(x => x.id),
    ['AI-1', 'AI-2', 'AI-3', 'AI-4', 'AI-5', 'AI-6', 'AI-7']);
  assert.deepEqual(artifact.observations.map(x => x.repository), PUBLIC_TARGETS.map(x => x.repo));
  assert.match(markdown, /Complete observation does not mean passing CI/);
  assert.doesNotMatch(JSON.stringify({ artifact, markdown }), /PRIVATE_RAW_TEXT|advisory|limitations|token/);
});

test('rate-limit and other partial evidence remain visibly incomplete', async () => {
  const source = await inspectAndAnalyzePublicCi(fakePublicGitHub({
    incomplete: new Set([1]),
  }));
  const { artifact, markdown } = buildActionArtifact(source);
  assert.equal(artifact.status, 'partial_observation');
  assert.equal(artifact.eligible_count, 3);
  assert.equal(artifact.excluded_count, 1);
  assert.equal(artifact.observations[1].status, 'unverified');
  assert.equal(artifact.analysis.summary.missing_project_count, 1);
  assert.match(markdown, /unverified/);
  assert.doesNotMatch(JSON.stringify(artifact), /PRIVATE_RAW_TEXT/);
});

test('no qualifying evidence yields no invented AI-7 analysis', async () => {
  const source = await inspectAndAnalyzePublicCi(async url => {
    const target = PUBLIC_TARGETS.find(x => url.startsWith('https://api.github.com/repos/' + x.repo + '/'));
    assert.ok(target);
    return response(url, url.includes('/branches/')
      ? { name: 'main', commit: { sha: SHA } }
      : { total_count: 0, workflow_runs: [] });
  });
  const { artifact } = buildActionArtifact(source);
  assert.equal(artifact.status, 'no_eligible_evidence');
  assert.equal(artifact.analysis, null);
  assert.equal(artifact.eligible_count, 0);
});

test('altered claims, extra private fields and unknown CI states fail closed', async () => {
  const source = await inspectAndAnalyzePublicCi(fakePublicGitHub());
  for (const change of [
    x => { x.production_ready = true; },
    x => { x.raw_token = 'PRIVATE_RAW_TEXT'; },
    x => { x.observations[0].repository = 'other/private'; },
    x => { x.observations[1].status = 'unknown_future_status'; },
    x => { x.eligible_count = 3; },
    x => { x.analysis.summary.recommendation_count = 1; },
    x => { x.analysis.projects[0].conclusion = 'timed_out'; },
  ]) {
    const altered = structuredClone(source);
    change(altered);
    assert.throws(() => buildActionArtifact(altered), /invalid_public_ci_action_report/);
  }
});

test('CLI creates only sanitized artifact and trusted GitHub step summary', async t => {
  const temp = mkdtempSync(join(tmpdir(), 'devobs-public-action-'));
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const input = join(temp, 'raw.json');
  const output = join(temp, 'sanitized.json');
  const summary = join(temp, 'step.md');
  const source = await inspectAndAnalyzePublicCi(fakePublicGitHub());
  writeFileSync(input, JSON.stringify(source));
  const result = spawnSync(process.execPath, [script, '--input', input, '--output', output], {
    encoding: 'utf8', env: { PATH: process.env.PATH ?? '', GITHUB_STEP_SUMMARY: summary },
    timeout: 10_000,
  });
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stderr, '');
  assert.equal(result.stdout, '');
  assert.deepEqual(JSON.parse(readFileSync(output, 'utf8')), buildActionArtifact(source).artifact);
  assert.match(readFileSync(summary, 'utf8'), /AI-7/);
  assert.equal((JSON.parse(readFileSync(output, 'utf8'))).external_provenance_verified, false);
});

test('invalid provider-derived JSON cannot generate any artifact or leak raw error text', t => {
  const temp = mkdtempSync(join(tmpdir(), 'devobs-public-action-'));
  t.after(() => rmSync(temp, { recursive: true, force: true }));
  const input = join(temp, 'raw.json');
  const output = join(temp, 'sanitized.json');
  writeFileSync(input, '{ "private": "PRIVATE_RAW_TEXT" }');
  const result = spawnSync(process.execPath, [script, '--input', input, '--output', output], {
    encoding: 'utf8', env: { PATH: process.env.PATH ?? '' }, timeout: 10_000,
  });
  assert.equal(result.status, 2);
  assert.equal(existsSync(output), false);
  assert.doesNotMatch(result.stderr, /PRIVATE_RAW_TEXT/);
});
