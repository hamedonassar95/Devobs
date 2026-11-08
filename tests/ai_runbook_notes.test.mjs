import assert from 'node:assert/strict';
import test from 'node:test';

import {
  MAX_RUNBOOK_NOTES,
  readRunbookNotes,
  setRunbookNoteArchived,
  setRunbookNotePinned,
} from '../scripts/ai_intelligence/dashboard_assets/runbook_notes.mjs';

const pinnedNote = {
  id: 'note-1',
  title: 'استعادة اتصال الخدمة',
  content: 'تحقق من الحالة ثم راجع سجل التغيير.',
  isArchived: false,
  isPinned: true,
  createdAt: '2026-11-07T10:00:00.000Z',
  updatedAt: '2026-11-07T10:00:00.000Z',
};

test('local note reader rejects malformed JSON and invalid note records', () => {
  assert.deepEqual(readRunbookNotes(null), []);
  assert.deepEqual(readRunbookNotes('{'), []);
  assert.deepEqual(readRunbookNotes(JSON.stringify([pinnedNote, { id: 'bad' }])), [pinnedNote]);
  assert.deepEqual(readRunbookNotes(JSON.stringify([{ ...pinnedNote, content: 'x'.repeat(5_001) }])), []);
});

test('archiving unpins a note and restoring it restores its previous pin state', () => {
  const archived = setRunbookNoteArchived([pinnedNote], pinnedNote.id, true, '2026-11-07T11:00:00.000Z');
  assert.equal(archived[0].isArchived, true);
  assert.equal(archived[0].isPinned, false);
  assert.equal(archived[0].wasPinnedBeforeArchive, true);
  assert.equal(archived[0].updatedAt, '2026-11-07T11:00:00.000Z');

  const restored = setRunbookNoteArchived(archived, pinnedNote.id, false, '2026-11-07T12:00:00.000Z');
  assert.equal(restored[0].isArchived, false);
  assert.equal(restored[0].isPinned, true);
  assert.equal(restored[0].wasPinnedBeforeArchive, undefined);
  assert.equal(restored[0].updatedAt, '2026-11-07T12:00:00.000Z');
});

test('archive state updates are idempotent and leave other records unchanged', () => {
  const other = { ...pinnedNote, id: 'note-2', isPinned: false };
  const notes = [pinnedNote, other];
  const unchanged = setRunbookNoteArchived(notes, pinnedNote.id, false);
  assert.equal(unchanged[0], pinnedNote);
  assert.equal(unchanged[1], other);
  assert.equal(setRunbookNoteArchived(notes, 'missing', true)[0], pinnedNote);
});

test('only active notes can be pinned and note reads are bounded', () => {
  const archived = { ...pinnedNote, isArchived: true, isPinned: false };
  assert.equal(setRunbookNotePinned([archived], archived.id, true)[0], archived);
  const updated = setRunbookNotePinned([pinnedNote], pinnedNote.id, false, '2026-11-07T13:00:00.000Z');
  assert.equal(updated[0].isPinned, false);
  assert.equal(updated[0].updatedAt, '2026-11-07T13:00:00.000Z');

  const many = Array.from({ length: MAX_RUNBOOK_NOTES + 1 }, (_, index) => ({ ...pinnedNote, id: `note-${index}` }));
  assert.equal(readRunbookNotes(JSON.stringify(many)).length, MAX_RUNBOOK_NOTES);
});
