import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import { parseEventLines } from '../scripts/ai_intelligence/event_schema.mjs';
import {
  convertText,
  MAX_INPUT_BYTES,
} from '../scripts/integrations/cloudevents_ci_adapter.mjs';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const SCRIPT = path.join(ROOT, 'scripts/integrations/cloudevents_ci_adapter.mjs');
const SOURCES = [
  ['https://github.com/hamedonassar95/Devobs', 'Devobs'],
  ['https://github.com/hamedonassar95/devobs-saas', 'devobs-saas'],
  ['https://github.com/hamedonassar95/phone-repair-assistant-v2', 'phone-repair-assistant-v2'],
  ['https://github.com/hamedonassar95/al-dala-mobile', 'al-dala-mobile'],
  ['https://github.com/hamedonassar95/LiveOps-Integration', 'LiveOps-Integration'],
  ['https://github.com/hamedonassar95/DevObs-ai-Intelligence-', 'DevObs-ai-Intelligence-'],
];

function event(overrides = {}) {
  return {
    specversion: '1.0',
    id: 'ci-run-001',
    source: SOURCES[0][0],
    type: 'devobs.ci.result.v1',
    time: '2026-11-14T12:00:00+03:00',
    datacontenttype: 'application/json',
    data: {
      workflow: 'CI build',
      job: 'Node tests',
      conclusion: 'success',
      commit_sha: 'a'.repeat(40),
    },
    ...overrides,
  };
}

function jsonl(events) {
  return `${events.map(item => JSON.stringify(item)).join('\n')}\n`;
}

function tempDir(t) {
  let directory;
  return mkdtemp(path.join(os.tmpdir(), 'devobs-cloudevents-')).then(value => {
    directory = value;
    t.after(async () => rm(directory, { recursive: true, force: true }));
    return directory;
  });
}

test('converts allowlisted structured CloudEvents and reuses the exact AI-1 input schema', () => {
  const input = SOURCES.map(([source], index) => event({
    id: `run-${index + 1}`,
    source,
    data: { ...event().data, workflow: 'CI build' },
  }));
  const output = convertText(jsonl(input));
  const parsed = parseEventLines(output);

  assert.equal(parsed.events.length, SOURCES.length);
  assert.equal(parsed.duplicatesInBatch, 0);
  assert.deepEqual(Object.keys(JSON.parse(output.trim().split('\n')[0])).sort(), [
    'data', 'kind', 'occurred_at', 'schema_version', 'severity', 'source',
  ]);
  for (let index = 0; index < SOURCES.length; index++) {
    const actual = parsed.events[index];
    assert.equal(actual.source, 'github_actions');
    assert.equal(actual.kind, 'ci_result');
    assert.equal(actual.occurred_at, '2026-11-14T09:00:00.000Z');
    assert.equal(actual.data.workflow, `${SOURCES[index][1]} - CI build`);
    assert.equal(actual.data.job, 'Node tests');
    assert.equal(actual.data.conclusion, 'success');
    assert.equal(actual.data.commit_sha, 'a'.repeat(40));
  }
});

test('maps every supported conclusion to a deterministic AI-1 severity', () => {
  const mapping = {
    success: 'info',
    neutral: 'info',
    skipped: 'warning',
    cancelled: 'warning',
    action_required: 'warning',
    failure: 'error',
    timed_out: 'error',
    unknown: 'unknown',
  };
  for (const [conclusion, severity] of Object.entries(mapping)) {
    const parsed = parseEventLines(convertText(jsonl([event({
      id: `result-${conclusion}`,
      data: { ...event().data, conclusion },
    })])));
    assert.equal(parsed.events[0].severity, severity, conclusion);
  }
});

test('rejects unsupported CloudEvents versions, types, sources, content types, and attributes', () => {
  const cases = [
    [event({ specversion: '0.3' }), 'unsupported_specversion'],
    [event({ type: 'devobs.ci.result.v2' }), 'unsupported_type'],
    [event({ source: 'https://github.com/other/repo' }), 'unknown_source'],
    [event({ datacontenttype: 'application/json; charset=utf-8' }), 'unsupported_content_type'],
    [event({ extension: 'unexpected' }), 'invalid_cloudevent_fields'],
    [event({ time: undefined }), 'invalid_cloudevent_fields'],
    [event({ id: '' }), 'invalid_id'],
    [event({ data: [] }), 'invalid_ci_data_fields'],
  ];
  for (const [input, code] of cases) {
    assert.throws(() => convertText(jsonl([input])), { code });
  }
});

test('rejects duplicate JSON keys and duplicate source/id pairs', () => {
  assert.throws(() => convertText('{"specversion":"1.0",broken}\n'), { code: 'invalid_json' });
  assert.throws(() => convertText(`${jsonl([event()]).trim()}\n\n`), { code: 'empty_line' });
  const duplicateKey = '{"specversion":"1.0","id":"same","id":"different"}\n';
  assert.throws(() => convertText(duplicateKey), { code: 'duplicate_json_key' });
  assert.throws(() => convertText(jsonl([event(), event()])), { code: 'duplicate_source_id' });
});

test('rejects missing or extra result fields, malformed SHA values, and unsafe labels', () => {
  const cases = [
    [event({ data: { workflow: 'CI build', job: 'Node tests', conclusion: 'success' } }), 'invalid_ci_data_fields'],
    [event({ data: { ...event().data, extra: 'value' } }), 'invalid_ci_data_fields'],
    [event({ data: { ...event().data, commit_sha: 'abc123' } }), 'invalid_commit_sha'],
    [event({ data: { ...event().data, conclusion: 'passed' } }), 'invalid_conclusion'],
    [event({ id: 'operator@example.test' }), 'invalid_or_sensitive_id'],
    [event({ id: '1234567890' }), 'invalid_or_sensitive_id'],
    [event({ id: 'run-555-123-4567' }), 'invalid_or_sensitive_id'],
    [event({ data: { ...event().data, workflow: 'workflow https://example.invalid' } }), 'invalid_ai1_event'],
    [event({ data: { ...event().data, job: 'Authorization: Bearer abc' } }), 'invalid_ai1_event'],
    [event({ data: { ...event().data, job: '555-123-4567' } }), 'invalid_ci_data'],
    [event({ data: { ...event().data, workflow: 'w'.repeat(100) } }), 'invalid_ai1_event'],
  ];
  for (const [input, code] of cases) {
    assert.throws(() => convertText(jsonl([input])), { code });
  }
});

test('accepts only valid RFC3339 timestamps and normalizes offsets to UTC', () => {
  for (const time of [
    '2026-02-30T12:00:00Z',
    '2026-11-14T12:00:00',
    '2026-11-14T12:00:60Z',
    '2026-11-14T12:00:00+24:00',
    'not-a-time',
  ]) {
    assert.throws(() => convertText(jsonl([event({ time })])), { code: 'invalid_timestamp' });
  }
  const parsed = parseEventLines(convertText(jsonl([event({ time: '2026-11-14T12:00:00.123456Z' })])));
  assert.equal(parsed.events[0].occurred_at, '2026-11-14T12:00:00.123Z');
  const earlyYear = parseEventLines(convertText(jsonl([event({ time: '0099-01-01T00:00:00Z' })])));
  assert.equal(earlyYear.events[0].occurred_at, '0099-01-01T00:00:00.000Z');
});

test('rejects same AI-1 event under different CloudEvent IDs instead of dropping one', () => {
  assert.throws(() => convertText(jsonl([
    event({ id: 'run-001' }),
    event({ id: 'run-002' }),
  ])), { code: 'duplicate_ai1_event' });
});

test('enforces the shared one MiB and 100-event batch limits', () => {
  assert.equal(MAX_INPUT_BYTES, 1_048_576);
  assert.throws(() => convertText(' '.repeat(MAX_INPUT_BYTES + 1)), { code: 'input_too_large' });
  const batch = Array.from({ length: 101 }, (_, index) => event({ id: `run-${index}` }));
  assert.throws(() => convertText(jsonl(batch)), { code: 'invalid_batch_size' });
});

test('CLI reads a file or stdin and writes only a complete normalized batch', async t => {
  const directory = await tempDir(t);
  const inputPath = path.join(directory, 'input.jsonl');
  await writeFile(inputPath, jsonl([event()]), 'utf8');
  const fromFile = spawnSync(process.execPath, [SCRIPT, '--input', inputPath], {
    encoding: 'utf8', timeout: 10_000,
  });
  assert.equal(fromFile.status, 0, fromFile.stderr);
  assert.equal(fromFile.stderr, '');
  assert.equal(parseEventLines(fromFile.stdout).events.length, 1);

  const fromStdin = spawnSync(process.execPath, [SCRIPT, '--input', '-'], {
    input: jsonl([event()]), encoding: 'utf8', timeout: 10_000,
  });
  assert.equal(fromStdin.status, 0, fromStdin.stderr);
  assert.equal(parseEventLines(fromStdin.stdout).events.length, 1);

  const invalidBatch = jsonl([event(), event({ id: 'bad-run', type: 'invalid.type' })]);
  const failed = spawnSync(process.execPath, [SCRIPT, '--input', '-'], {
    input: invalidBatch, encoding: 'utf8', timeout: 10_000,
  });
  assert.equal(failed.status, 2);
  assert.equal(failed.stdout, '');
  assert.match(failed.stderr, /^cloudevents-ci-adapter: unsupported_type\n$/);
  assert.equal(failed.stderr.includes('bad-run'), false);
});

test('CLI reports only fixed error categories and never echoes sensitive-looking input', async t => {
  const directory = await tempDir(t);
  const inputPath = path.join(directory, 'sensitive.jsonl');
  const marker = 'operator@example.invalid';
  await writeFile(inputPath, jsonl([event({ id: marker })]), 'utf8');
  const result = spawnSync(process.execPath, [SCRIPT, '--input', inputPath], {
    encoding: 'utf8', timeout: 10_000,
  });
  assert.equal(result.status, 2);
  assert.equal(result.stdout, '');
  assert.match(result.stderr, /^cloudevents-ci-adapter: invalid_or_sensitive_id\n$/);
  assert.equal(result.stderr.includes(marker), false);
  assert.equal(result.stderr.includes(inputPath), false);
  assert.equal((await readFile(inputPath, 'utf8')).includes(marker), true);
});
