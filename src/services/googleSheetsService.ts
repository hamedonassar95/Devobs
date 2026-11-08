import { Server, Incident, Deployment } from '../types/serverDashboard';

export interface SpreadsheetFileItem {
  id: string;
  name: string;
  createdTime?: string;
  modifiedTime?: string;
  webViewLink?: string;
}

export interface SheetMetadata {
  spreadsheetId: string;
  properties: {
    title: string;
    locale?: string;
  };
  sheets?: {
    properties: {
      sheetId: number;
      title: string;
      index: number;
      gridProperties?: {
        rowCount: number;
        columnCount: number;
      };
    };
  }[];
  spreadsheetUrl?: string;
}

// 1. List spreadsheets from user's Drive
export async function listGoogleSpreadsheets(accessToken: string): Promise<SpreadsheetFileItem[]> {
  try {
    const q = "mimeType='application/vnd.google-apps.spreadsheet' and trashed=false";
    const url = `https://www.googleapis.com/drive/v3/files?q=${encodeURIComponent(
      q
    )}&fields=files(id,name,createdTime,modifiedTime,webViewLink)&orderBy=modifiedTime desc&pageSize=20`;

    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error?.message || `Failed to list spreadsheets: ${res.status}`);
    }

    const data = await res.json();
    return data.files || [];
  } catch (error: any) {
    console.error('List spreadsheets error:', error);
    throw error;
  }
}

// 2. Get Spreadsheet Details
export async function getSpreadsheetDetails(
  accessToken: string,
  spreadsheetId: string
): Promise<SheetMetadata> {
  const safeId = encodeURIComponent(spreadsheetId.trim());
  const res = await fetch(`https://sheets.googleapis.com/v4/spreadsheets/${safeId}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to get spreadsheet ${spreadsheetId}: ${res.status}`);
  }

  return res.json();
}

// 3. Read Values from Range
export async function readSpreadsheetValues(
  accessToken: string,
  spreadsheetId: string,
  range: string
): Promise<any[][]> {
  const safeId = encodeURIComponent(spreadsheetId.trim());
  const safeRange = encodeURIComponent(range.trim());
  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${safeId}/values/${safeRange}`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to read range ${range}: ${res.status}`);
  }

  const data = await res.json();
  return data.values || [];
}

// 4. Create New Spreadsheet
export async function createGoogleSpreadsheet(
  accessToken: string,
  title: string,
  sheetTitles: string[] = ['Sheet1']
): Promise<SheetMetadata> {
  const res = await fetch('https://sheets.googleapis.com/v4/spreadsheets', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      properties: { title },
      sheets: sheetTitles.map((t) => ({
        properties: { title: t },
      })),
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to create spreadsheet: ${res.status}`);
  }

  return res.json();
}

// 5. Append Rows to Sheet Range
export async function appendSpreadsheetRows(
  accessToken: string,
  spreadsheetId: string,
  range: string,
  rows: (string | number)[][]
): Promise<any> {
  const safeId = encodeURIComponent(spreadsheetId.trim());
  const safeRange = encodeURIComponent(range.trim());
  const res = await fetch(
    `https://sheets.googleapis.com/v4/spreadsheets/${safeId}/values/${safeRange}:append?valueInputOption=USER_ENTERED`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        values: rows,
      }),
    }
  );

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `Failed to append rows to sheet: ${res.status}`);
  }

  return res.json();
}

// 6. High-level DevOps Helper: Export Server Inventory to a new Google Sheet
export async function exportServerInventoryToNewSheet(
  accessToken: string,
  servers: Server[],
  title?: string
): Promise<SheetMetadata> {
  const sheetTitle = title || `سجل خوادم المنظومة - Server Inventory ${new Date().toLocaleDateString('ar-EG')}`;
  const newSheet = await createGoogleSpreadsheet(accessToken, sheetTitle, ['Servers']);

  const headers = [
    'اسم الخادم',
    'عنوان IP',
    'النوع',
    'البيئة',
    'المنطقة الجغرافية',
    'الحالة التشغيلية',
    'المعالج %',
    'الذاكرة %',
    'القرص %',
    'سرعة الشبكة (Mbps)',
    'زمن التشغيل (أيام)',
    'نظام التشغيل',
  ];

  const rows: (string | number)[][] = [headers];
  for (const s of servers) {
    rows.push([
      s.name,
      s.ip,
      s.type,
      s.environment,
      s.region,
      s.status,
      s.cpu,
      s.memory,
      s.disk,
      s.networkMbps,
      s.uptimeDays,
      s.os,
    ]);
  }

  await appendSpreadsheetRows(accessToken, newSheet.spreadsheetId, 'Servers!A1', rows);
  return newSheet;
}

// 7. High-level DevOps Helper: Export Incidents to a new Google Sheet
export async function exportIncidentsToNewSheet(
  accessToken: string,
  incidents: Incident[],
  title?: string
): Promise<SheetMetadata> {
  const sheetTitle = title || `سجل حوادث وأخطاء الخوادم - Incidents Log ${new Date().toLocaleDateString('ar-EG')}`;
  const newSheet = await createGoogleSpreadsheet(accessToken, sheetTitle, ['Incidents']);

  const headers = [
    'معرف الحادثة',
    'اسم الخادم',
    'مستوى الخطورة',
    'كود الخطأ',
    'رسالة العطل',
    'التوقيت',
    'تمت المعالجة',
  ];

  const rows: (string | number)[][] = [headers];
  for (const inc of incidents) {
    rows.push([
      inc.id,
      inc.serverName,
      inc.severity,
      inc.code,
      inc.message,
      inc.timestamp,
      inc.resolved ? 'نعم' : 'لا',
    ]);
  }

  await appendSpreadsheetRows(accessToken, newSheet.spreadsheetId, 'Incidents!A1', rows);
  return newSheet;
}
