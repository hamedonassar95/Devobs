import test from 'node:test';
import assert from 'node:assert/strict';
import { previewDemoAction } from '../src/utils/demoActionPreview.ts';

for (const action of ['restart', 'redeploy', 'rollback']) {
  test(`${action} is advisory-only and does not claim an infrastructure change`, () => {
    const result = previewDemoAction(action);
    assert.equal(result.action, action);
    assert.equal(result.performed, false);
    assert.equal(result.modifiedInfrastructure, false);
    assert.equal(result.mode, 'demo_only');
    assert.match(result.message, /محاكاة/);
    assert.match(result.message, /لم .*تنفيذ/);
    assert.ok(Object.isFrozen(result));
  });
}
