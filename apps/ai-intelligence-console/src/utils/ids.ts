let lastFallbackTimestamp = 0;
let fallbackSequence = 0;

/** Create a stable-prefix, collision-resistant identifier for local records. */
export function createRecordId(prefix: string): string {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi?.randomUUID === 'function') {
    return `${prefix}-${cryptoApi.randomUUID()}`;
  }

  const timestamp = Date.now();
  fallbackSequence = timestamp === lastFallbackTimestamp ? fallbackSequence + 1 : 0;
  lastFallbackTimestamp = timestamp;
  return `${prefix}-${timestamp.toString(36)}-${fallbackSequence.toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
