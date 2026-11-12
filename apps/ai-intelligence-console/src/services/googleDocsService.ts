import { Incident, Server } from '../types/serverDashboard';

export interface DocFileItem {
  id: string;
  name: string;
  createdTime?: string;
  modifiedTime?: string;
  webViewLink?: string;
}

export interface DocumentDetails {
  documentId: string;
  title: string;
  body?: {
    content?: any[];
  };
}

// 1. List Google Docs from Google Drive
export async function listGoogleDocs(accessToken: string): Promise<DocFileItem[]> {
  try {
    const q = "mimeType='application/vnd.google-apps.document' and trashed=false";
    const url = `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(
      q
    )}&fields=files(id,name,createdTime,modifiedTime,webViewLink)&orderBy=modifiedTime desc&pageSize=20`;

    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Failed to list documents: ${res.status}`);
    }

    const data = await res.json();
    return data.files || [];
  } catch (error: any) {
    console.error('List Google Docs error:', error);
    throw error;
  }
}

// 2. Get Document Structure and Text Content
export async function getGoogleDoc(
  accessToken: string,
  documentId: string
): Promise<DocumentDetails> {
  const safeId = encodeURIComponent(documentId.trim());
  const res = await fetch(`https://docs.googleapis.com/v1/documents/${safeId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to get document ${documentId}: ${res.status}`);
  }

  return res.json();
}

// 3. Create a New Document
export async function createGoogleDoc(
  accessToken: string,
  title: string
): Promise<DocumentDetails> {
  const res = await fetch('https://docs.googleapis.com/v1/documents', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ title }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to create document: ${res.status}`);
  }

  return res.json();
}

// 4. Insert Text into Document
export async function insertTextToDocument(
  accessToken: string,
  documentId: string,
  text: string,
  index: number = 1
): Promise<any> {
  const safeId = encodeURIComponent(documentId.trim());
  const res = await fetch(`https://docs.googleapis.com/v1/documents/${safeId}:batchUpdate`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      requests: [
        {
          insertText: {
            location: { index },
            text,
          },
        },
      ],
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to insert text: ${res.status}`);
  }

  return res.json();
}

// 5. High-level DevOps Helper: Export Incident Post-Mortem / RCA to a new Google Doc
export async function exportIncidentRcaToDoc(
  accessToken: string,
  incident: Incident,
  rcaText: string
): Promise<{ doc: DocumentDetails; webViewLink?: string }> {
  const docTitle = `تقرير الحادثة الهندسية (Incident RCA) - [${incident.code}] @${incident.serverName}`;
  const newDoc = await createGoogleDoc(accessToken, docTitle);

  const documentContent = `=====================================================
تقرير تحليل السبب الجذري للحادثة (Post-Mortem & Incident RCA)
=====================================================
كود الحادثة: ${incident.code}
الخادم المتأثر: ${incident.serverName}
مستوى الخطورة: ${incident.severity.toUpperCase()}
تاريخ وتوقيت الحدوث: ${incident.timestamp}
حالة الإغلاق: ${incident.resolved ? 'تمت المعالجة (Resolved)' : 'قيد المعالجة (Active)'}

رسالة الخطأ المسجلة:
${incident.message}

تفاصيل تتبع الخطأ (Stack Trace):
${incident.stackTrace || 'غير متوفر'}

-----------------------------------------------------
تحليل الذكاء الاصطناعي الهندسي (Gemini SRE Analysis):
-----------------------------------------------------
${rcaText || 'تم إغلاق الحادثة بعد المراجعة الميدانية.'}

=====================================================
تم إنشاء هذا التقرير تلقائياً عبر منظومة ServerOps Console
`;

  await insertTextToDocument(accessToken, newDoc.documentId, documentContent);

  // Get drive webViewLink
  let webViewLink = `https://docs.google.com/document/d/${newDoc.documentId}/edit`;
  try {
    const driveRes = await fetch(
      `https://www.googleapis.com/drive/v3/files/${newDoc.documentId}?fields=webViewLink`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    if (driveRes.ok) {
      const data = await driveRes.json();
      if (data.webViewLink) webViewLink = data.webViewLink;
    }
  } catch (e) {
    console.warn(e);
  }

  return { doc: newDoc, webViewLink };
}

// 6. High-level DevOps Helper: Export Infrastructure Audit Report to a new Google Doc
export async function exportAuditReportToDoc(
  accessToken: string,
  reportMarkdown: string,
  customTitle?: string
): Promise<{ doc: DocumentDetails; webViewLink?: string }> {
  const docTitle =
    customTitle ||
    `تقرير فحص البنية التحتية الشامل - Infrastructure Audit ${new Date().toLocaleDateString('ar-EG')}`;
  const newDoc = await createGoogleDoc(accessToken, docTitle);

  const header = `=====================================================
تقرير التدقيق الهندسي الشامل للبنية التحتية (Infrastructure Audit)
تاريخ الإنشاء: ${new Date().toLocaleString('ar-EG')}
المصدر: Gemini SRE Engine & ServerOps Console
=====================================================\n\n`;

  await insertTextToDocument(accessToken, newDoc.documentId, header + reportMarkdown);

  let webViewLink = `https://docs.google.com/document/d/${newDoc.documentId}/edit`;
  try {
    const driveRes = await fetch(
      `https://www.googleapis.com/drive/v3/files/${newDoc.documentId}?fields=webViewLink`,
      { headers: { Authorization: `Bearer ${accessToken}` } }
    );
    if (driveRes.ok) {
      const data = await driveRes.json();
      if (data.webViewLink) webViewLink = data.webViewLink;
    }
  } catch (e) {
    console.warn(e);
  }

  return { doc: newDoc, webViewLink };
}
