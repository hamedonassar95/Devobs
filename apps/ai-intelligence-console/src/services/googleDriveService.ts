export interface DriveFile {
  id: string;
  name: string;
  mimeType: string;
  modifiedTime?: string;
  size?: string;
  webViewLink?: string;
  iconLink?: string;
  parents?: string[];
}

export interface DriveStorageQuota {
  limit?: string;
  usage?: string;
  usageInDrive?: string;
  usageInDriveTrash?: string;
}

export async function listDriveFiles(
  token: string,
  folderId?: string,
  searchQuery?: string
): Promise<DriveFile[]> {
  let q = "trashed = false";
  if (folderId) {
    q += ` and '${folderId}' in parents`;
  }
  if (searchQuery && searchQuery.trim()) {
    q += ` and name contains '${searchQuery.replace(/'/g, "\\'")}'`;
  }

  const params = new URLSearchParams({
    q,
    pageSize: '50',
    fields: 'files(id, name, mimeType, modifiedTime, size, webViewLink, iconLink, parents)',
    orderBy: 'folder,modifiedTime desc',
  });

  const res = await fetch(`https://www.googleapis.com/drive/v3/files?${params.toString()}`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `خطأ في جلب ملفات Google Drive (${res.status})`);
  }

  const data = await res.json();
  return data.files || [];
}

export async function createDriveFolder(
  token: string,
  folderName: string,
  parentId?: string
): Promise<DriveFile> {
  const metadata: any = {
    name: folderName,
    mimeType: 'application/vnd.google-apps.folder',
  };

  if (parentId) {
    metadata.parents = [parentId];
  }

  const res = await fetch('https://www.googleapis.com/drive/v3/files', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(metadata),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `فشل إنشاء المجلد في Google Drive (${res.status})`);
  }

  return await res.json();
}

export async function uploadDriveFile(
  token: string,
  name: string,
  content: string,
  mimeType = 'text/plain',
  parentId?: string
): Promise<DriveFile> {
  const metadata: any = {
    name,
    mimeType,
  };

  if (parentId) {
    metadata.parents = [parentId];
  }

  const boundary = '-------314159265358979323846';
  const delimiter = `\r\n--${boundary}\r\n`;
  const closeDelimiter = `\r\n--${boundary}--`;

  const multipartRequestBody =
    delimiter +
    'Content-Type: application/json; charset=UTF-8\r\n\r\n' +
    JSON.stringify(metadata) +
    delimiter +
    `Content-Type: ${mimeType}; charset=UTF-8\r\n\r\n` +
    content +
    closeDelimiter;

  const res = await fetch('https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': `multipart/related; boundary=${boundary}`,
    },
    body: multipartRequestBody,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `فشل رفع الملف إلى Google Drive (${res.status})`);
  }

  return await res.json();
}

export async function deleteDriveFile(token: string, fileId: string): Promise<void> {
  const res = await fetch(`https://www.googleapis.com/drive/v3/files/${fileId}`, {
    method: 'DELETE',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.error?.message || `فشل حذف الملف من Google Drive (${res.status})`);
  }
}

export async function getDriveStorageQuota(token: string): Promise<DriveStorageQuota> {
  const res = await fetch('https://www.googleapis.com/drive/v3/about?fields=storageQuota,user', {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    return {};
  }

  const data = await res.json();
  return data.storageQuota || {};
}
