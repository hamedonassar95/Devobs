import { buildGoogleChatReport } from './google_chat_export.mjs';

export const GOOGLE_GMAIL_SCOPE = 'https://www.googleapis.com/auth/gmail.send';

const GMAIL_SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send';

function isRecord(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function validAccessToken(value) {
  return typeof value === 'string' && value.length >= 16 && value.length <= 4096
    && !/[\s\x00-\x1f\x7f]/.test(value);
}

export function isValidGoogleGmailAddress(value) {
  if (typeof value !== 'string' || value.length > 254 || value !== value.trim()
    || /[\s\x00-\x1f\x7f,;<>]/.test(value)) return false;
  const parts = value.split('@');
  if (parts.length !== 2) return false;
  const [local, domain] = parts;
  if (local.length < 1 || local.length > 64 || local.startsWith('.') || local.endsWith('.')
    || local.includes('..') || !/^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$/.test(local)) return false;
  const labels = domain.split('.');
  return labels.length >= 2 && labels.every(label => label.length >= 1 && label.length <= 63
    && /^[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?$/.test(label));
}

function validDate(value) {
  return value instanceof Date && Number.isFinite(value.getTime());
}

/** Build a fixed email preview from aggregate AI-7 counts; raw event content is ignored. */
export function buildGoogleGmailReport(snapshot, recipient, createdAt = new Date()) {
  if (!validDate(createdAt) || !isValidGoogleGmailAddress(recipient)) {
    throw new TypeError('invalid_google_gmail_report_input');
  }
  const chatReport = buildGoogleChatReport(snapshot, createdAt);
  return {
    createdAt: createdAt.toISOString(),
    recipient,
    subject: `Devobs AI-7 aggregate summary ${createdAt.toISOString().slice(0, 10)}`,
    body: chatReport.message,
  };
}

function base64Utf8(value) {
  const bytes = new TextEncoder().encode(value);
  let binary = '';
  for (let index = 0; index < bytes.length; index++) binary += String.fromCharCode(bytes[index]);
  return btoa(binary);
}

function wrapBase64(value) {
  return value.match(/.{1,76}/g)?.join('\r\n') ?? '';
}

function buildRawMessage(report) {
  const body = wrapBase64(base64Utf8(report.body));
  const mime = [
    `To: ${report.recipient}`,
    `Subject: ${report.subject}`,
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: base64',
    '',
    body,
  ].join('\r\n');
  return base64Utf8(mime).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/** Send one explicitly approved aggregate message; this connector never reads Gmail. */
export async function sendGoogleGmailSummary({
  accessToken,
  snapshot,
  recipient,
  createdAt = new Date(),
  fetchImpl = fetch,
}) {
  if (!validAccessToken(accessToken) || typeof fetchImpl !== 'function') {
    throw new TypeError('invalid_google_gmail_request');
  }
  const report = buildGoogleGmailReport(snapshot, recipient, createdAt);
  let response;
  try {
    response = await fetchImpl(GMAIL_SEND_URL, {
      method: 'POST',
      redirect: 'error',
      cache: 'no-store',
      credentials: 'omit',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ raw: buildRawMessage(report) }),
    });
  } catch {
    throw new Error('google_gmail_send_failed');
  }
  if (!response || response.ok !== true) throw new Error('google_gmail_send_failed');

  let sent;
  try {
    sent = await response.json();
  } catch {
    throw new Error('google_gmail_invalid_response');
  }
  if (!isRecord(sent) || typeof sent.id !== 'string' || !/^[A-Za-z0-9_-]{1,256}$/.test(sent.id)
    || typeof sent.threadId !== 'string' || !/^[A-Za-z0-9_-]{1,256}$/.test(sent.threadId)) {
    throw new Error('google_gmail_invalid_response');
  }
  return { sent: true };
}
