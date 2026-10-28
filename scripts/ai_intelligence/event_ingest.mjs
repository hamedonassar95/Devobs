#!/usr/bin/env node
import { randomUUID } from 'node:crypto';
import { constants } from 'node:fs';
import {
  chmod,
  lstat,
  mkdir,
  open,
  readFile,
  rename,
  unlink,
} from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import {
  canonicalJson,
  EventIngestError,
  EVENT_SCHEMA_VERSION,
  MAX_INPUT_BYTES,
  normalizeEvent,
  parseEventLines,
  parseJsonLine,
  parseStoredEvent,
} from './event_schema.mjs';

export { EventIngestError, normalizeEvent };

function reject(code) {
  throw new EventIngestError(code);
}

export const MAX_STORE_BYTES = 52_428_800;

async function openNoFollow(filePath, flags, mode = 0o600) {
  if (typeof constants.O_NOFOLLOW !== 'number') reject('platform_no_follow_unsupported');
  try {
    return await open(filePath, flags | constants.O_NOFOLLOW, mode);
  } catch (error) {
    if (error?.code === 'ELOOP') reject('unsafe_path');
    if (error?.code === 'ENOENT') throw error;
    if (error?.code === 'EEXIST') reject('store_locked');
    reject('storage_unavailable');
  }
}

async function readBoundedFile(filePath, maximum, errorCode, requirePrivateMode = false) {
  let handle;
  try {
    handle = await openNoFollow(filePath, constants.O_RDONLY);
    const info = await handle.stat();
    if (!info.isFile()) reject('unsafe_path');
    if (requirePrivateMode && (info.mode & 0o077) !== 0) reject('unsafe_store_permissions');
    if (info.size > maximum) reject(errorCode);
    const bytes = await handle.readFile();
    if (bytes.length > maximum) reject(errorCode);
    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(bytes);
    } catch {
      reject('invalid_utf8');
    }
  } catch (error) {
    if (error instanceof EventIngestError) throw error;
    if (error?.code === 'ENOENT') throw error;
    reject('storage_unavailable');
  } finally {
    await handle?.close().catch(() => {});
  }
}

export async function readInputFile(inputPath) {
  if (typeof inputPath !== 'string' || inputPath.length === 0) reject('invalid_input_path');
  if (inputPath === '-') {
    if (process.stdin.isTTY) reject('input_required');
    const chunks = [];
    let total = 0;
    for await (const chunk of process.stdin) {
      total += chunk.length;
      if (total > MAX_INPUT_BYTES) reject('input_too_large');
      chunks.push(chunk);
    }
    try {
      return new TextDecoder('utf-8', { fatal: true }).decode(Buffer.concat(chunks));
    } catch {
      reject('invalid_utf8');
    }
  }
  try {
    return await readBoundedFile(path.resolve(inputPath), MAX_INPUT_BYTES, 'input_too_large');
  } catch (error) {
    if (error instanceof EventIngestError) throw error;
    if (error?.code === 'ENOENT') reject('input_unavailable');
    throw error;
  }
}

export async function readEventStore(storePath) {
  if (typeof storePath !== 'string' || storePath.length === 0 || storePath === '-') reject('invalid_store_path');
  const resolved = path.resolve(storePath);
  let raw;
  try {
    raw = await readBoundedFile(resolved, MAX_STORE_BYTES, 'store_too_large', true);
  } catch (error) {
    if (error instanceof EventIngestError && error.code === 'storage_unavailable') {
      try {
        await lstat(resolved);
      } catch (statError) {
        if (statError?.code === 'ENOENT') return [];
      }
    }
    if (error?.code === 'ENOENT') return [];
    if (error instanceof EventIngestError && error.code === 'unsafe_path') reject('unsafe_store_path');
    if (error instanceof EventIngestError && error.code === 'store_too_large') throw error;
    if (error instanceof EventIngestError) reject('invalid_store');
    reject('storage_unavailable');
  }
  if (raw === '') return [];
  if (!raw.endsWith('\n')) reject('invalid_store');
  const lines = raw.slice(0, -1).split('\n');
  const events = [];
  const ids = new Set();
  try {
    for (const line of lines) {
      const event = parseStoredEvent(parseJsonLine(line));
      if (ids.has(event.event_id)) reject('invalid_store');
      ids.add(event.event_id);
      events.push(event);
    }
  } catch {
    reject('invalid_store');
  }
  return events;
}

async function writeStoreAtomically(storePath, events) {
  const resolved = path.resolve(storePath);
  const directory = path.dirname(resolved);
  const lockPath = `${resolved}.lock`;
  await mkdir(directory, { recursive: true, mode: 0o700 }).catch(() => reject('storage_unavailable'));
  let lockHandle;
  let tempPath;
  let tempHandle;
  try {
    lockHandle = await openNoFollow(lockPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, 0o600);
  } catch (error) {
    if (error instanceof EventIngestError) throw error;
    reject('store_locked');
  }
  try {
    const existing = await readEventStore(resolved);
    const byId = new Map(existing.map(event => [event.event_id, event]));
    const additions = [];
    let duplicates = 0;
    for (const event of events) {
      const previous = byId.get(event.event_id);
      if (previous) {
        if (canonicalJson(previous) !== canonicalJson(event)) reject('event_id_conflict');
        duplicates++;
      } else {
        byId.set(event.event_id, event);
        additions.push(event);
      }
    }
    if (additions.length === 0) return { accepted: 0, duplicateIgnored: duplicates };
    const contents = [...existing, ...additions].map(canonicalJson).join('\n') + '\n';
    if (Buffer.byteLength(contents, 'utf8') > MAX_STORE_BYTES) reject('store_too_large');
    tempPath = `${resolved}.tmp-${randomUUID()}`;
    tempHandle = await openNoFollow(tempPath, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL, 0o600);
    await tempHandle.writeFile(contents, 'utf8');
    await tempHandle.sync();
    await tempHandle.close();
    tempHandle = undefined;
    await rename(tempPath, resolved);
    tempPath = undefined;
    await chmod(resolved, 0o600);
    return { accepted: additions.length, duplicateIgnored: duplicates };
  } catch (error) {
    if (error instanceof EventIngestError) throw error;
    reject('storage_unavailable');
  } finally {
    await tempHandle?.close().catch(() => {});
    if (tempPath) await unlink(tempPath).catch(() => {});
    await lockHandle?.close().catch(() => {});
    await unlink(lockPath).catch(() => {});
  }
}

export async function ingestText(text, storePath) {
  if (typeof storePath !== 'string' || storePath.length === 0 || storePath === '-') reject('invalid_store_path');
  const batch = parseEventLines(text);
  const result = await writeStoreAtomically(storePath, batch.events);
  return { accepted: result.accepted, duplicateIgnored: result.duplicateIgnored + batch.duplicatesInBatch };
}

function usage() {
  return 'Usage: node scripts/ai_intelligence/event_ingest.mjs --input <jsonl-file|-> --store <local-jsonl-file>';
}

function parseArgs(args) {
  if (args.length === 1 && (args[0] === '--help' || args[0] === '-h')) return { help: true };
  const values = {};
  for (let index = 0; index < args.length; index += 2) {
    const name = args[index];
    if (!['--input', '--store'].includes(name) || typeof args[index + 1] !== 'string'
      || args[index + 1].length === 0 || args[index + 1].startsWith('--') || Object.hasOwn(values, name)) {
      reject('invalid_arguments');
    }
    values[name] = args[index + 1];
  }
  if (!values['--input'] || !values['--store']) reject('invalid_arguments');
  return { input: values['--input'], store: values['--store'] };
}

export async function main(args = process.argv.slice(2)) {
  try {
    const options = parseArgs(args);
    if (options.help) {
      process.stdout.write(`${usage()}\n`);
      return 0;
    }
    const input = await readInputFile(options.input);
    const result = await ingestText(input, options.store);
    process.stdout.write(`${JSON.stringify({ schema_version: EVENT_SCHEMA_VERSION, ...result })}\n`);
    return 0;
  } catch (error) {
    const code = error instanceof EventIngestError ? error.code : 'internal_error';
    process.stderr.write(`event-ingest: ${code}\n${usage()}\n`);
    return 2;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  process.exitCode = await main();
}
