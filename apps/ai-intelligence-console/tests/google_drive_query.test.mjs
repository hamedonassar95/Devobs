import assert from 'node:assert/strict';
import test from 'node:test';

import { escapeDriveQueryLiteral } from '../src/services/googleDriveService.ts';

test('Drive query literals escape backslashes and apostrophes', () => {
  assert.equal(
    escapeDriveQueryLiteral(String.raw`Team\O'Brien`),
    String.raw`Team\\O\'Brien`,
  );
  assert.equal(escapeDriveQueryLiteral('ordinary folder name'), 'ordinary folder name');
});

test('Drive query literals cannot terminate a quoted filter value', () => {
  const escaped = escapeDriveQueryLiteral("x' or trashed = true or name contains '");
  assert.equal(escaped, String.raw`x\' or trashed = true or name contains \'`);
});
