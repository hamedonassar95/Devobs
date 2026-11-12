export interface GmailMessageSummary {
  id: string;
  threadId: string;
  subject?: string;
  from?: string;
  to?: string;
  date?: string;
  snippet?: string;
}

export interface GmailProfile {
  emailAddress: string;
  messagesTotal: number;
  threadsTotal: number;
  historyId: string;
}

export async function getGmailProfile(token: string): Promise<GmailProfile | null> {
  const res = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/profile', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    return null;
  }
  return await res.json();
}

export async function listGmailMessages(
  token: string,
  query?: string,
  maxResults = 20
): Promise<GmailMessageSummary[]> {
  const params = new URLSearchParams({
    maxResults: maxResults.toString(),
  });
  if (query && query.trim()) {
    params.set('q', query);
  }

  const res = await fetch(
    `https://gmail.googleapis.com/gmail/v1/users/me/messages?${params.toString()}`,
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `فشل جلب رسائل البريد الإلكتروني (${res.status})`);
  }

  const data = await res.json();
  const rawList: { id: string; threadId: string }[] = data.messages || [];

  // Fetch headers for the first batch to get Subject, From, Date
  const detailedMessages = await Promise.all(
    rawList.slice(0, 15).map(async (item) => {
      try {
        const detailRes = await fetch(
          `https://gmail.googleapis.com/gmail/v1/users/me/messages/${item.id}?format=metadata&metadataHeaders=Subject&metadataHeaders=From&metadataHeaders=To&metadataHeaders=Date`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        if (!detailRes.ok) return { id: item.id, threadId: item.threadId };
        const detail = await detailRes.json();
        const headers = detail.payload?.headers || [];
        const subject = headers.find((h: any) => h.name.toLowerCase() === 'subject')?.value;
        const from = headers.find((h: any) => h.name.toLowerCase() === 'from')?.value;
        const to = headers.find((h: any) => h.name.toLowerCase() === 'to')?.value;
        const date = headers.find((h: any) => h.name.toLowerCase() === 'date')?.value;

        return {
          id: item.id,
          threadId: item.threadId,
          subject: subject || '(بدون عنوان)',
          from: from || 'غير محدد',
          to: to || '',
          date: date || '',
          snippet: detail.snippet || '',
        };
      } catch {
        return { id: item.id, threadId: item.threadId };
      }
    })
  );

  return detailedMessages;
}

export async function sendGmailEmail(
  token: string,
  options: {
    to: string;
    subject: string;
    body: string;
    isHtml?: boolean;
  }
): Promise<{ id: string; threadId: string }> {
  const { to, subject, body, isHtml } = options;

  // Build RFC 2822 message with UTF-8 support
  const utf8Subject = `=?utf-8?B?${btoa(unescape(encodeURIComponent(subject)))}?=`;
  const contentType = isHtml ? 'text/html; charset=UTF-8' : 'text/plain; charset=UTF-8';

  const rawMessage = [
    `To: ${to}`,
    `Subject: ${utf8Subject}`,
    'MIME-Version: 1.0',
    `Content-Type: ${contentType}`,
    'Content-Transfer-Encoding: 8bit',
    '',
    body,
  ].join('\r\n');

  // Convert string to base64url
  const utf8Bytes = new TextEncoder().encode(rawMessage);
  let binary = '';
  for (let i = 0; i < utf8Bytes.length; i++) {
    binary += String.fromCharCode(utf8Bytes[i]);
  }
  const base64UrlMessage = btoa(binary)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');

  const res = await fetch('https://gmail.googleapis.com/gmail/v1/users/me/messages/send', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      raw: base64UrlMessage,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `فشل إرسال البريد الإلكتروني عبر Gmail (${res.status})`);
  }

  return await res.json();
}
