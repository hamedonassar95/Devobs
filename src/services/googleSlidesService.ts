import { Incident, Server } from '../types/serverDashboard';

export interface GoogleSlidePresentation {
  id: string;
  name: string;
  createdTime?: string;
  modifiedTime?: string;
  webViewLink?: string;
}

export interface SlidePresentationDetails {
  presentationId: string;
  title: string;
  slides: Array<{
    objectId: string;
    pageElements?: any[];
  }>;
}

/**
 * List Google Slides presentations from Google Drive
 */
export async function listGooglePresentations(accessToken: string): Promise<GoogleSlidePresentation[]> {
  const query = encodeURIComponent("mimeType='application/vnd.google-apps.presentation' and trashed=false");
  const res = await fetch(
    `https://www.googleapis.com/drive/v3/files?q=${query}&fields=files(id,name,createdTime,modifiedTime,webViewLink)&orderBy=modifiedTime desc&pageSize=30`,
    {
      headers: {
        Authorization: `Bearer ${accessToken}`,
      },
    }
  );

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب عروض التقديم: ${res.statusText}`);
  }

  const data = await res.json();
  return data.files || [];
}

/**
 * Get details of a Google Slides presentation
 */
export async function getPresentationDetails(accessToken: string, presentationId: string): Promise<SlidePresentationDetails> {
  const res = await fetch(`https://slides.googleapis.com/v1/presentations/${presentationId}`, {
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.error?.message || `فشل جلب تفاصيل العرض التقديمي: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Create a new empty presentation
 */
export async function createPresentation(accessToken: string, title: string): Promise<{ presentationId: string; webViewLink?: string }> {
  const res = await fetch('https://slides.googleapis.com/v1/presentations', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      title,
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `فشل إنشاء العرض التقديمي: ${res.statusText}`);
  }

  const data = await res.json();
  const presentationId = data.presentationId;
  const webViewLink = `https://docs.google.com/presentation/d/${presentationId}/edit`;

  return { presentationId, webViewLink };
}

/**
 * Execute batch update on a presentation
 */
export async function batchUpdatePresentation(accessToken: string, presentationId: string, requests: any[]): Promise<any> {
  const res = await fetch(`https://slides.googleapis.com/v1/presentations/${presentationId}:batchUpdate`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ requests }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || `فشل تحديث شرائح العرض: ${res.statusText}`);
  }

  return await res.json();
}

/**
 * Generate an SRE Incident Post-Mortem Presentation Deck in Google Slides
 */
export async function exportIncidentToSlideDeck(
  accessToken: string,
  incident: Incident,
  server?: Server
): Promise<{ presentationId: string; webViewLink: string }> {
  const title = `[تقرير حادثة SRE] - ${incident.code}: ${incident.message} (${new Date().toISOString().split('T')[0]})`;
  const { presentationId, webViewLink } = await createPresentation(accessToken, title);

  // We add slides using batchUpdate
  const slide1Id = 'slide_summary_' + Date.now();
  const slide2Id = 'slide_root_cause_' + (Date.now() + 1);
  const slide3Id = 'slide_action_items_' + (Date.now() + 2);

  const requests: any[] = [
    // Slide 1: Incident Summary
    {
      createSlide: {
        objectId: slide1Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
    // Slide 2: Root Cause & Diagnostics
    {
      createSlide: {
        objectId: slide2Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
    // Slide 3: Action Items & Mitigations
    {
      createSlide: {
        objectId: slide3Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
  ];

  await batchUpdatePresentation(accessToken, presentationId, requests);

  // Fetch created slides to locate title and body shape IDs
  const presentation = await getPresentationDetails(accessToken, presentationId);
  const updateRequests: any[] = [];

  for (const slide of presentation.slides) {
    if (slide.objectId === slide1Id) {
      // Find title and body placeholders
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: `ملخص الحادثة: ${incident.code} - ${incident.message}`,
          },
        });
      }
      if (bodyShape) {
        const bodyText = `• مستوى الخطورة: ${incident.severity.toUpperCase()}\n` +
          `• الخادم المتأثر: ${server ? server.name + ' (' + server.ip + ')' : incident.serverName || incident.serverId}\n` +
          `• الحالة الراهنة: ${incident.resolved ? 'تم الحل والتعافي' : 'نشطة وقيد المتابعة'}\n` +
          `• وقت الرصد: ${incident.timestamp}\n` +
          `• التفاصيل والأثر:\n${incident.message}\n` +
          `${incident.aiAnalysis ? '\nتحليل الذكاء الاصطناعي (Gemini):\n' + incident.aiAnalysis : ''}`;
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text: bodyText,
          },
        });
      }
    } else if (slide.objectId === slide2Id) {
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: 'تحليل السبب الجذري ومسار التتبع (Stack Trace)',
          },
        });
      }
      if (bodyShape) {
        const bodyText = `1. تتبع الخطأ (Stack Trace):\n${incident.stackTrace || 'No stack trace recorded'}\n\n` +
          `2. التحليل التقني:\n   - تعطل العمليات أو اختناق في الموارد الحوسبية والشبكية.\n` +
          `3. الأثر المباشر:\n   - تأثر زمن الاستجابة لمستخدمي المنظومة أو تدني مستوى الخدمة SLA.\n` +
          `4. التدارك المبدئي:\n   - عزل الموارد المتضررة وتفعيل مسارات التكرار (Failover).`;
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text: bodyText,
          },
        });
      }
    } else if (slide.objectId === slide3Id) {
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: 'الإجراءات الوقائية وخطة العمل (Action Items)',
          },
        });
      }
      if (bodyShape) {
        const bodyText = `✔ أتمتة اختبارات الجاهزية وإجراءات الاسترجاع الفوري (Failover Testing).\n` +
          `✔ تحديث عتبات التنبيه التلقائي عبر مراكز القيادة (Prometheus & Grafana Alert Rules).\n` +
          `✔ مراجعة وتحديث دليل التشغيل (SRE Runbook) الخاص بالتعامل مع هذا النوع من الأعطال.\n` +
          `✔ توثيق ومشاركة مخرجات الحادثة في اجتماع المراجعة الأسبوعي لفرق التطوير والعمليات.`;
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text: bodyText,
          },
        });
      }
    }
  }

  if (updateRequests.length > 0) {
    await batchUpdatePresentation(accessToken, presentationId, updateRequests);
  }

  return { presentationId, webViewLink: webViewLink || `https://docs.google.com/presentation/d/${presentationId}/edit` };
}

/**
 * Generate an Executive SRE Infrastructure Overview Slide Deck
 */
export async function exportExecutiveReportToSlideDeck(
  accessToken: string,
  servers: Server[],
  incidents: Incident[]
): Promise<{ presentationId: string; webViewLink: string }> {
  const dateStr = new Date().toLocaleDateString('ar-EG');
  const title = `عرض القيادة التنفيذية - جاهزية البنية التحتية (${dateStr})`;
  const { presentationId, webViewLink } = await createPresentation(accessToken, title);

  const healthyServers = servers.filter((s) => s.status === 'healthy').length;
  const avgCpu = Math.round(servers.reduce((acc, s) => acc + s.cpu, 0) / (servers.length || 1));
  const avgMemory = Math.round(servers.reduce((acc, s) => acc + s.memory, 0) / (servers.length || 1));
  const activeIncidents = incidents.filter((i) => !i.resolved).length;
  const criticalIncidents = incidents.filter((i) => i.severity === 'critical' && !i.resolved).length;

  const slide1Id = 'slide_exec_summary_' + Date.now();
  const slide2Id = 'slide_servers_overview_' + (Date.now() + 1);
  const slide3Id = 'slide_incidents_overview_' + (Date.now() + 2);

  const requests: any[] = [
    {
      createSlide: {
        objectId: slide1Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
    {
      createSlide: {
        objectId: slide2Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
    {
      createSlide: {
        objectId: slide3Id,
        slideLayoutReference: { predefinedLayout: 'TITLE_AND_BODY' },
      },
    },
  ];

  await batchUpdatePresentation(accessToken, presentationId, requests);

  const presentation = await getPresentationDetails(accessToken, presentationId);
  const updateRequests: any[] = [];

  for (const slide of presentation.slides) {
    if (slide.objectId === slide1Id) {
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: `الملخص التنفيذي لمنظومة السحابة - ${dateStr}`,
          },
        });
      }
      if (bodyShape) {
        const text = `• إجمالي الخوادم المراقبة: ${servers.length} خادم عبر مختلف المناطق السحابية.\n` +
          `• نسبة التوافر والتشغيل النشط: ${Math.round((healthyServers / (servers.length || 1)) * 100)}% (${healthyServers} سليم تماماً).\n` +
          `• متوسط استهلاك المعالجات (CPU): ${avgCpu}%\n` +
          `• متوسط استهلاك الذاكرة (RAM): ${avgMemory}%\n` +
          `• الحوادث النشطة الحالية: ${activeIncidents} (منها ${criticalIncidents} حرجة).`;
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text,
          },
        });
      }
    } else if (slide.objectId === slide2Id) {
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: 'توزيع الخوادم والجاهزية الجغرافية',
          },
        });
      }
      if (bodyShape) {
        const serverSummary = servers.slice(0, 6).map((s) => `• [${s.status.toUpperCase()}] ${s.name} (${s.ip}) - CPU: ${s.cpu}%, RAM: ${s.memory}%`).join('\n');
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text: `نظرة تفصيلية على الخوادم الرئيسية:\n${serverSummary}\n\n* تم الربط المباشر مع قواعد بيانات السحابة والمراقبة الحية في الوقت الفعلي.`,
          },
        });
      }
    } else if (slide.objectId === slide3Id) {
      const titleShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'TITLE');
      const bodyShape = slide.pageElements?.find((pe: any) => pe.shape?.placeholder?.type === 'BODY');
      if (titleShape) {
        updateRequests.push({
          insertText: {
            objectId: titleShape.objectId,
            text: 'سجل الحوادث والسلامة التشغيلية (Reliability Index)',
          },
        });
      }
      if (bodyShape) {
        const incidentSummary = incidents.slice(0, 4).map((i) => `• [${i.severity.toUpperCase()}] ${i.code}: ${i.message} - الحالة: ${i.resolved ? 'تم الحل' : 'نشطة'}`).join('\n');
        updateRequests.push({
          insertText: {
            objectId: bodyShape.objectId,
            text: `أهم البلاغات والحوادث المرصودة حديثاً:\n${incidentSummary || 'لا توجد حوادث مسجلة حالياً، المنظومة تعمل باستقرار تام.'}\n\nتوصيات SRE:\n- الحفاظ على كفاءة خطوط التوسع التلقائي (Auto-scaling).\n- إجراء تدريبات محاكاة الطوارئ الدورية.`,
          },
        });
      }
    }
  }

  if (updateRequests.length > 0) {
    await batchUpdatePresentation(accessToken, presentationId, updateRequests);
  }

  return { presentationId, webViewLink: webViewLink || `https://docs.google.com/presentation/d/${presentationId}/edit` };
}
