import assert from 'node:assert/strict';
import test from 'node:test';

import { escapeCSVField, serializeCSV } from '../src/utils/dashboardUtils.ts';

test('CSV exports quote and escape every field without shifting columns', () => {
  const csv = serializeCSV(
    ['server', 'region', 'status'],
    [['edge "blue", primary', 'us-east', 'healthy']],
  );

  assert.equal(csv, '\uFEFF"server","region","status"\n"edge ""blue"", primary","us-east","healthy"');
});

test('CSV text fields are protected from spreadsheet formula execution', () => {
  assert.equal(escapeCSVField('=HYPERLINK("https://example.invalid")'), '"\'=HYPERLINK(""https://example.invalid"")"');
  assert.equal(escapeCSVField(-12), '"-12"');
});
