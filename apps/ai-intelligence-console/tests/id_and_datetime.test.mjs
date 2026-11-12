import assert from 'node:assert/strict';
import test from 'node:test';

import { toLocalDateTimeInput } from '../src/utils/dateTime.ts';
import { createRecordId } from '../src/utils/ids.ts';

test('record identifiers remain distinct during rapid creation', () => {
  const ids = Array.from({ length: 1000 }, () => createRecordId('record'));

  assert.equal(new Set(ids).size, ids.length);
  assert.ok(ids.every((id) => id.startsWith('record-')));
});

test('datetime-local formatting preserves the local clock fields', () => {
  const date = new Date(2026, 10, 12, 12, 30);
  const expected = [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, '0'),
    String(date.getDate()).padStart(2, '0'),
  ].join('-') + `T${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;

  assert.equal(toLocalDateTimeInput(date), expected);
});
