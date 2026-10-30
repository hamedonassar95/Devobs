import assert from 'node:assert/strict';
import test from 'node:test';
import { jointMetricDecision, AI9_JOINT_METRIC_V2_POLICY } from '../scripts/ai_intelligence/ai9_joint_metric_v2.mjs';

function stream(recent, base = 10) {
  const values = [...Array(30).fill(base), ...recent];
  const first = Date.parse('2026-10-30T00:00:00.000Z');
  return {
    values,
    events: values.map((_, i) => ({
      occurred_at: new Date(first + 60000 * i).toISOString(),
    })),
  };
}
const strong = () => stream([10, 20, 20]);
const flat = () => stream([10, 10, 10]);
function example(shifts, confirms = [true, true, true], serviceId = 'service-one') {
  const metricNames = ['cpu_percent', 'latency_ms', 'error_rate'];
  const metrics = metricNames.map((metric, i) => ({
    metric,
    stream: shifts[i] ? strong() : flat(),
    confirmed: confirms[i],
  }));
  return { serviceId, occurredAt: metrics[0].stream.events[32].occurred_at, index: 32, metrics };
}

test('two distinct strong metrics preserve third weak but already confirmed alert', () => {
  const result = jointMetricDecision(example([true, true, false]));
  assert.equal(result.policy_version, AI9_JOINT_METRIC_V2_POLICY.version);
  assert.equal(result.coherent_service_shift, true);
  assert.equal(result.robust_metric_count, 2);
  assert.deepEqual(result.metrics.map(m => m.candidate_confirmed), [true, true, true]);
  assert.deepEqual(result.metrics.map(m => m.robust_shift), [true, true, false]);
});

test('one strong metric or only spikes cannot confirm any metric', () => {
  const result = jointMetricDecision(example([true, false, false]));
  assert.equal(result.coherent_service_shift, false);
  assert.deepEqual(result.metrics.map(m => m.candidate_confirmed), [false, false, false]);
});

test('never creates positive when existing confirmation is false', () => {
  const result = jointMetricDecision(example([true, true, false], [false, true, true]));
  assert.deepEqual(result.metrics.map(m => m.candidate_confirmed), [false, true, true]);
});

test('service and timestamp boundaries remain isolated and repeatable', () => {
  const one = example([true, true, false]);
  const other = example([true, false, false], [true, true, true], 'another-service');
  assert.deepEqual(jointMetricDecision(one), jointMetricDecision(one));
  assert.equal(jointMetricDecision(other).coherent_service_shift, false);
});

test('reject duplicate metric names and cross-metric timestamp mismatch', () => {
  const duplicate = example([true, true, false]);
  duplicate.metrics[2].metric = duplicate.metrics[1].metric;
  assert.throws(() => jointMetricDecision(duplicate), { code: 'invalid_joint_metric_window' });
  const stale = example([true, true, false]);
  stale.metrics[2].stream.events[32].occurred_at = stale.metrics[2].stream.events[31].occurred_at;
  assert.throws(() => jointMetricDecision(stale), { code: 'invalid_joint_metric_window' });
});

test('reject invalid service context, confirmation type, metric count', () => {
  const bad = example([true, true, false]);
  bad.serviceId = '';
  assert.throws(() => jointMetricDecision(bad), { code: 'invalid_joint_metric_window' });
  const type = example([true, true, false]);
  type.metrics[1].confirmed = 'true';
  assert.throws(() => jointMetricDecision(type), { code: 'invalid_joint_metric_window' });
  const count = example([true, true, false]);
  count.metrics.pop();
  assert.throws(() => jointMetricDecision(count), { code: 'invalid_joint_metric_window' });
});
