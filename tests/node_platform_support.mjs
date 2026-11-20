/*
 * Host-capability probes shared by Node tests.
 *
 * These helpers only report capabilities and emit narrow skips. They never
 * relax production fail-closed behavior: callers keep explicit assertions for
 * the error code returned when a POSIX-only capability is unavailable.
 */

import { constants } from 'node:fs';
import { mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const NO_FOLLOW_SKIP = 'POSIX O_NOFOLLOW secure file operations are unavailable; production fails closed with platform_no_follow_unsupported';
const JOURNAL_SKIP = 'POSIX O_NOFOLLOW secure journal operations are unavailable; production fails closed with unsupported_journal_platform';
const SYMLINK_SKIP = 'unprivileged symlink creation is unavailable on this host';

export function hasNoFollowCapability() {
  return typeof constants.O_NOFOLLOW === 'number';
}

export function hasJournalCapability() {
  return hasNoFollowCapability();
}

export function noFollowErrorCode(code) {
  return hasNoFollowCapability() ? code : 'platform_no_follow_unsupported';
}

export function journalErrorCode(code) {
  return hasJournalCapability() ? code : 'unsupported_journal_platform';
}

export function requireNoFollowCapability(t, reason = NO_FOLLOW_SKIP) {
  if (hasNoFollowCapability()) return true;
  t.skip(reason);
  return false;
}

export function requireJournalCapability(t, reason = JOURNAL_SKIP) {
  if (hasJournalCapability()) return true;
  t.skip(reason);
  return false;
}

export function canCreateSymlink() {
  const directory = mkdtempSync(path.join(os.tmpdir(), 'devobs-symlink-probe-'));
  try {
    const target = path.join(directory, 'target');
    writeFileSync(target, '');
    symlinkSync(target, path.join(directory, 'link'));
    return true;
  } catch {
    return false;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

export function requireSymlinkCreation(t, reason = SYMLINK_SKIP) {
  if (canCreateSymlink()) return true;
  t.skip(reason);
  return false;
}
