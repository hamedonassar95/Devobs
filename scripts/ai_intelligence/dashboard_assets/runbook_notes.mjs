/* Adapted from hamedonassar95/DevObs-ai-Intelligence- under MIT; see licenses/DEVOBS_AI_INTELLIGENCE_MIT.txt. */
export const MAX_RUNBOOK_NOTES = 200;
const MAX_TITLE_LENGTH = 120;
const MAX_CONTENT_LENGTH = 5_000;

export function isRunbookNote(value) {
  return Boolean(
    value
      && typeof value === 'object'
      && typeof value.id === 'string'
      && value.id.trim().length > 0
      && value.id.length <= 120
      && typeof value.title === 'string'
      && value.title.trim().length > 0
      && value.title.length <= MAX_TITLE_LENGTH
      && typeof value.content === 'string'
      && value.content.trim().length > 0
      && value.content.length <= MAX_CONTENT_LENGTH
      && typeof value.isArchived === 'boolean'
      && typeof value.isPinned === 'boolean'
      && typeof value.createdAt === 'string'
      && typeof value.updatedAt === 'string'
      && Number.isFinite(Date.parse(value.createdAt))
      && Number.isFinite(Date.parse(value.updatedAt))
      && (value.wasPinnedBeforeArchive === undefined || typeof value.wasPinnedBeforeArchive === 'boolean'),
  );
}

export function readRunbookNotes(serializedNotes) {
  if (typeof serializedNotes !== 'string' || serializedNotes.length === 0) return [];

  try {
    const parsed = JSON.parse(serializedNotes);
    return Array.isArray(parsed) ? parsed.filter(isRunbookNote).slice(0, MAX_RUNBOOK_NOTES) : [];
  } catch {
    return [];
  }
}

export function setRunbookNoteArchived(notes, noteId, isArchived, updatedAt = new Date().toISOString()) {
  if (!Array.isArray(notes) || typeof noteId !== 'string' || typeof isArchived !== 'boolean') {
    return Array.isArray(notes) ? notes : [];
  }

  return notes.map((note) => {
    if (note.id !== noteId || note.isArchived === isArchived) return note;

    if (isArchived) {
      return {
        ...note,
        isArchived: true,
        wasPinnedBeforeArchive: note.isPinned,
        isPinned: false,
        updatedAt,
      };
    }

    return {
      ...note,
      isArchived: false,
      isPinned: note.wasPinnedBeforeArchive ?? note.isPinned,
      wasPinnedBeforeArchive: undefined,
      updatedAt,
    };
  });
}

export function setRunbookNotePinned(notes, noteId, isPinned, updatedAt = new Date().toISOString()) {
  if (!Array.isArray(notes) || typeof noteId !== 'string' || typeof isPinned !== 'boolean') {
    return Array.isArray(notes) ? notes : [];
  }

  return notes.map((note) => {
    if (note.id !== noteId || note.isArchived || note.isPinned === isPinned) return note;
    return { ...note, isPinned, updatedAt };
  });
}
