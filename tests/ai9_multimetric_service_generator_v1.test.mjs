import assert from 'node:assert/strict';
import test from 'node:test';
import {
  digestAi9MultimetricInputV1,
  generateAi9MultimetricServicesV1,
} from '../scripts/ai_intelligence/ai9_multimetric_service_generator_v1.mjs';

test('multimetric generator is deterministic and preserves the preregistered low prevalence', () => {
  const first = generateAi9MultimetricServicesV1(424242);
  const second = generateAi9MultimetricServicesV1(424242);

  assert.equal(first.classification, 'synthetic_development_only');
  assert.equal(first.services.length, 56);
  assert.ok(first.services.every(service => service.metrics.length === 3));
  assert.equal(digestAi9MultimetricInputV1(first), digestAi9MultimetricInputV1(second));

  let scoredWindows = 0;
  let positiveWindows = 0;
  for (const service of first.services) {
    const [firstMetric] = service.metrics;
    assert.ok(service.metrics.every(metric => metric.events.length === firstMetric.events.length));
    assert.ok(service.metrics.every(metric => metric.events.every((event, index) =>
      event.occurred_at === firstMetric.events[index].occurred_at)));
    for (const metric of service.metrics) {
      assert.ok(metric.events.every(event => event.data.name === metric.metric && event.data.unit === metric.unit));
      const labels = metric.labels.slice(first.baseline_points);
      scoredWindows += labels.length;
      positiveWindows += labels.filter(Boolean).length;
      if (service.group === 'injected_fault') assert.equal(labels.filter(Boolean).length, 5);
      else assert.equal(labels.filter(Boolean).length, 0);
    }
  }
  assert.equal(scoredWindows, 45_240);
  assert.equal(positiveWindows, 90);
  assert.equal(positiveWindows / scoredWindows, 30 / 15_080);
});
