const { test } = require('node:test');
const assert = require('node:assert/strict');
const { incidentGuard } = require('../scripts/incident_guard.cjs');

function fixture({ input = '30', issue = {}, comments = [], failApi = false } = {}) {
  const state = { outputs: {}, failures: [], reads: 0, pages: 0 };
  const trusted = {
    number: 30, state: 'open', user: { login: 'github-actions[bot]' },
    title: 'incident: controlled drill',
    body: '<!-- incident-run-id:simulation-37511616721 -->', ...issue,
  };
  const listComments = () => { throw Error('Must paginate comments'); };
  return {
    state,
    args: {
      context: { repo: { owner: 'owner', repo: 'repo' }, payload: { inputs: { issue_number: input } } },
      core: {
        setOutput: (k, v) => { state.outputs[k] = v; },
        info: () => {}, setFailed: message => state.failures.push(message),
      },
      github: {
        rest: { issues: {
          get: async params => {
            state.reads++;
            assert.equal(params.issue_number, Number(input));
            if (failApi) throw Error('API unavailable');
            return { data: trusted };
          }, listComments,
        } },
        paginate: async (method, params) => {
          assert.equal(method, listComments);
          assert.equal(params.per_page, 100);
          state.pages++;
          return comments;
        },
      },
    },
  };
}
const analysis = { user: { login: 'github-actions[bot]' }, body: '## AI Incident Investigation\nPENDING HUMAN APPROVAL' };

test('trusted new incident is eligible without a write API', async () => {
  const f = fixture();
  assert.equal(await incidentGuard(f.args), true);
  assert.equal(f.state.outputs.eligible, 'true');
});

test('opened and dispatched events resolve the same incident', async () => {
  const f = fixture();
  f.args.context.payload = { issue: { number: 30 } };
  assert.equal(await incidentGuard(f.args), true);
});

for (const input of ['', '030', '-1', '1.0', '1e2', '30/../31', '9007199254740992', undefined]) {
  test(`reject non-canonical input ${String(input)}`, async () => {
    const f = fixture({ input });
    if (input === undefined) f.args.context.payload.inputs = {};
    assert.equal(await incidentGuard(f.args), false);
    assert.equal(f.state.reads, 0);
    assert.equal(f.state.outputs.eligible, 'false');
  });
}

for (const issue of [
  { pull_request: {} }, { state: 'closed' }, { user: { login: 'someone' } },
  { title: 'ordinary issue' }, { body: 'incident-run-id:untrusted' }, { body: null },
]) {
  test(`untrusted issue is skipped: ${JSON.stringify(issue)}`, async () => {
    const f = fixture({ issue });
    assert.equal(await incidentGuard(f.args), false);
    assert.equal(f.state.pages, 0);
  });
}

test('existing investigation on a later page skips the agent', async () => {
  const f = fixture({ comments: [...Array(101).fill({ body: 'discussion' }), analysis] });
  assert.equal(await incidentGuard(f.args), false);
  assert.equal(f.state.failures.length, 0);
});

test('stable marker detects an investigation with a changed heading', async () => {
  const f = fixture({ comments: [{ ...analysis, body: '<!-- devobs-investigation:v1 -->' }] });
  assert.equal(await incidentGuard(f.args), false);
});

test('untrusted comment cannot impersonate a completed investigation', async () => {
  const f = fixture({ comments: [{ ...analysis, user: { login: 'someone' } }] });
  assert.equal(await incidentGuard(f.args), true);
});

test('replay after a completed writer creates no second comment', async () => {
  const comments = [];
  let writes = 0;
  // Workflow-level concurrency serializes the complete executions.
  for (let run = 0; run < 2; run++) {
    const f = fixture({ comments });
    if (await incidentGuard(f.args)) {
      if (await incidentGuard(f.args, true)) { comments.push(analysis); writes++; }
    }
  }
  assert.equal(writes, 1);
});

test('final writer fails closed if another comment appeared after activation', async () => {
  const comments = [];
  const f = fixture({ comments });
  assert.equal(await incidentGuard(f.args), true);
  comments.push(analysis);
  assert.equal(await incidentGuard(f.args, true), false);
  assert.equal(f.state.failures.length, 1);
});

test('API errors never authorize an investigation', async () => {
  const f = fixture({ failApi: true });
  await assert.rejects(incidentGuard(f.args), /API unavailable/);
  assert.equal(f.state.outputs.eligible, 'false');
});
