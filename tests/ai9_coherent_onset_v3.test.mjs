import assert from 'node:assert/strict';
import test from 'node:test';
import { coherentOnsetDecision, AI9_COHERENT_ONSET_V3_POLICY } from '../scripts/ai_intelligence/ai9_coherent_onset_v3.mjs';

function stream(mode = 'quiet', start = '2026-10-30T00:00:00.000Z') {
  // Median=10, MAD=1 for the 30 causal reference observations.
  const values = Array.from({ length: 30 }, (_, i) => i % 2 ? 11 : 9);
  if (mode === 'onset') values.push(10, 10, 40);
  else if (mode === 'persistent') values.push(10, 40, 40);
  else if (mode === 'noisy-preceding') values.push(40, 10, 40);
  else if (mode === 'quiet') values.push(10, 10, 10);
  else if (mode === 'zero-mad') values.splice(0, 30, ...Array(30).fill(10)), values.push(10, 10, 40);
  const t0 = Date.parse(start);
  return { values, events: values.map((_, i) => ({ occurred_at: new Date(t0 + i * 60_000).toISOString() })) };
}
function example(modes, confirmations = [true, true, true], id = 'service-a') {
  const metrics = ['cpu_percent', 'latency_ms', 'error_rate'].map((metric, i) => ({
    metric, stream: stream(modes[i]), confirmed: confirmations[i],
  }));
  return { serviceId: id, occurredAt: metrics[0].stream.events[32].occurred_at, index: 32, metrics };
}

test('two independent first-onset shifts restore only already confirmed metrics', () => {
  const x = coherentOnsetDecision(example(['onset','onset','quiet']));
  assert.equal(x.policy_version, AI9_COHERENT_ONSET_V3_POLICY.version);
  assert.equal(x.coherent_service_shift_v2, false);
  assert.equal(x.coherent_onset, true);
  assert.equal(x.onset_metric_count, 2);
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [true, true, true]);
});

test('single onset does not bypass the v2 coherent-shift gate', () => {
  const x = coherentOnsetDecision(example(['onset','quiet','quiet']));
  assert.equal(x.coherent_onset, false);
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [false,false,false]);
});

test('existing false confirmation never produces a candidate positive', () => {
  const x = coherentOnsetDecision(example(['onset','onset','quiet'], [false,true,false]));
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [false,true,false]);
});

test('two earlier abnormal points are not a first onset', () => {
  const x = coherentOnsetDecision(example(['noisy-preceding','onset','quiet']));
  assert.equal(x.coherent_onset, false);
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [false,false,false]);
});

test('previous v2 persistence detections remain identical', () => {
  const x = coherentOnsetDecision(example(['persistent','persistent','quiet']));
  assert.equal(x.coherent_service_shift_v2, true);
  assert.equal(x.coherent_onset, false);
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [true,true,true]);
});

test('MAD=0 is not proof of onset', () => {
  const x = coherentOnsetDecision(example(['zero-mad','onset','quiet']));
  assert.equal(x.coherent_onset, false);
  assert.deepEqual(x.metrics.map(m => m.candidate_confirmed), [false,false,false]);
});

test('malformed timestamps fail closed without sharing across services', () => {
  const x = example(['onset','onset','quiet']);
  x.metrics[1].stream.events[31].occurred_at = x.metrics[1].stream.events[30].occurred_at;
  // The frozen v2 validator runs first and must reject timestamp drift.
  assert.throws(() => coherentOnsetDecision(x), { code: 'invalid_temporal_order' });
  const isolated = coherentOnsetDecision(example(['onset','quiet','quiet'], [true,true,true], 'service-b'));
  assert.equal(isolated.coherent_onset, false);
});

test('invalid input and insufficient history never lead to onset alerts', () => {
  const x = example(['onset','onset','quiet']);
  x.metrics[1].metric = x.metrics[0].metric;
  assert.throws(() => coherentOnsetDecision(x), { code: 'invalid_joint_metric_window' });
  const start = example(['onset','onset','quiet']);
  start.index = 31;
  start.occurredAt = start.metrics[0].stream.events[31].occurred_at;
  assert.equal(coherentOnsetDecision(start).coherent_onset, false);
});
