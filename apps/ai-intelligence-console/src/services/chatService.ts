export interface ChatSpace {
  name: string;
  displayName?: string;
  type?: 'SPACE' | 'GROUP_CHAT' | 'DIRECT_MESSAGE';
  spaceType?: string;
  spaceThreadingState?: string;
}

export interface ChatMessage {
  name: string;
  text: string;
  createTime?: string;
  sender?: {
    name?: string;
    displayName?: string;
    type?: string;
  };
}

export async function listChatSpaces(token: string): Promise<ChatSpace[]> {
  const res = await fetch('https://chat.googleapis.com/v1/spaces', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message = err?.error?.message || `فشل في الاتصال بـ Google Chat API (${res.status})`;

    if (res.status === 404 || message.includes('not found')) {
      throw new Error(
        'Google Chat app not found. To create a Chat app, you must turn on the Chat API and configure the app in the Google Cloud console: https://console.cloud.google.com/apis/api/chat.googleapis.com/hangouts-chat?project=warm-aegis-350823'
      );
    }
    if (res.status === 403) {
      throw new Error(
        'يتطلب Google Chat API حساب عمل أو مؤسسة Google Workspace نشط، ولا تدعم حسابات @gmail.com الشخصية الاتصال المباشر بهذه الواجهة البرمجية.'
      );
    }
    throw new Error(message);
  }

  const data = await res.json();
  return data.spaces || [];
}

export async function sendChatMessage(
  token: string,
  spaceName: string,
  text: string
): Promise<ChatMessage> {
  const res = await fetch(`https://chat.googleapis.com/v1/${spaceName}/messages`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const message = err?.error?.message || `فشل إرسال الرسالة إلى Google Chat (${res.status})`;
    throw new Error(message);
  }

  return await res.json();
}
