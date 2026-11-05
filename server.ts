import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';
import path from 'path';

dotenv.config();

const app = express();
const port = parseInt(process.env.PORT || '3000', 10);

app.use(express.json());

// Initialize Google GenAI client (Server-side only)
const apiKey = process.env.GEMINI_API_KEY;
const ai = apiKey
  ? new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        },
      },
    })
  : null;

// Route 1: Analyze server incident with Gemini
app.post('/api/ai/analyze-incident', async (req, res) => {
  try {
    const { server, incident, allServers } = req.body;

    if (!ai) {
      return res.status(200).json({
        analysis: `⚠️ لم يتم العثور على مفتاح GEMINI_API_KEY، إليك تحليل استدلالي محلي:
- التشخيص الأولي: حدث تعطل أو ارتفاع في زمن الاستجابة على الخادم [${server?.name || 'غير محدد'}].
- السبب المرجح: تجاوز حدود الذاكرة العشوائية أو اختناق في اتصالات قاعدة البيانات (Connection Pool Exhaustion).
- الإجراء الفوري: قم بتنفيذ إعادة تشغيل سلسة (Graceful Restart) ومراقبة مؤشر استهلاك الذاكرة.`,
      });
    }

    const prompt = `أنت مهندس موثوقية مواقع وخوادم محترف (Senior SRE & Cloud Architect).
حلل حادثة الخادم التالية باللغة العربية بأسلوب هندسي دقيق وعملي:

معلومات الخادم المعني:
- الاسم: ${server?.name} (${server?.ip})
- البيئة والمنطقة: ${server?.environment} - ${server?.region}
- نوع الخدمة: ${server?.type}
- استهلاك المعالج: ${server?.cpu}%
- استهلاك الذاكرة: ${server?.memory}%
- استهلاك القرص: ${server?.disk}%

تفاصيل الخطأ المسجل:
- كود الخطأ: ${incident?.code || 'N/A'}
- الرسالة: ${incident?.message}
- مستوى الخطورة: ${incident?.severity}
- توقيت الحدوث: ${incident?.timestamp}
- تفاصيل تتبع الخطأ (Stack Trace): ${incident?.stackTrace || 'غير متوفر'}

يرجى تقديم التقرير بالصيغة التالية المنظمة:
1. **تشخيص السبب الجذري (Root Cause Analysis)**: ما الذي تسبب في هذا الخطأ تقنياً؟
2. **تقييم مدى الخطورة والأثر (Impact Assessment)**: كيف يؤثر هذا على المستخدمين وتدفق البيانات؟
3. **خطة التدخل الفوري (Immediate Remediation)**: خطوات وأوامر تنفيذية محددة لحل المشكلة فوراً.
4. **تدابير وقائية طويلة الأمد (Prevention & Hardening)**: كيف نتجنب تكرار هذا مستقبلاً؟`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'أنت مهندس بنية تحتية سحابية محترف يقدم تحليلات تقنية واضحة ودقيقة باللغة العربية.',
      },
    });

    res.json({ analysis: response.text });
  } catch (error: any) {
    console.error('Incident analysis error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد تحليل الذكاء الاصطناعي للحادثة',
    });
  }
});

// Route 2: Generate Infrastructure Health Audit Report
app.post('/api/ai/generate-audit-report', async (req, res) => {
  try {
    const { servers, incidents, deployments, systemStats } = req.body;

    if (!ai) {
      return res.status(200).json({
        report: `## تقرير فحص البنية التحتية الدوري (محلي)
- إجمالي الخوادم المسجلة: ${servers?.length || 0}
- الحوادث المفتوحة: ${incidents?.filter((i: any) => !i.resolved).length || 0}
- التوصية العامة: يُنصح بربط مفتاح Gemini للحصول على تدقيق معمق لسلامة البنية التحتية وتنبؤات بأعطال الأنظمة.`,
      });
    }

    const prompt = `قم بإعداد تقرير تدقيق هندسي دوري وشامل (Infrastructure Health & Reliability Audit Report) لحالة مجموعة الخوادم والأنظمة باللغة العربية.

البيانات الإحصائية الحالية:
- إجمالي الخوادم: ${servers?.length}
- الخوادم السليمة: ${servers?.filter((s: any) => s.status === 'healthy').length}
- الخوادم التي بها تحذيرات: ${servers?.filter((s: any) => s.status === 'warning').length}
- الخوادم المتعطلة أو الحرجة: ${servers?.filter((s: any) => s.status === 'critical').length}

بيانات الخوادم:
${JSON.stringify(servers?.map((s: any) => ({ name: s.name, type: s.type, status: s.status, cpu: s.cpu, memory: s.memory, region: s.region })), null, 2)}

الحوادث النشطة والأخيرة:
${JSON.stringify(incidents?.slice(0, 8), null, 2)}

آخر عمليات النشر البرمجي:
${JSON.stringify(deployments?.slice(0, 5), null, 2)}

نسق التقرير بتنسيق Markdown احترافي يتضمن:
- 📊 **الملخص التنفيذي لحالة المنظومة (Executive Summary)**
- ⚠️ **أبرز نقاط الضعف ونقاط الاختناق المحتملة (Identified Bottlenecks & Risks)**
- 🚀 **تقييم موثوقية عمليات النشر واستقرار الإصدارات (Deployment Reliability)**
- 💡 **خارطة طريق التوصيات الهندسية ذات الأولوية (Actionable Recommendations)**`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'أنت مهندس موثوقية بنية تحتية سحابية يقدم تقارير تنفيذية عالية الجودة باللغة العربية.',
      },
    });

    res.json({ report: response.text });
  } catch (error: any) {
    console.error('Audit report error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد تقرير التدقيق بالذكاء الاصطناعي',
    });
  }
});

// Setup Vite middleware in dev or static files in production
async function startServer() {
  if (process.env.NODE_ENV === 'production') {
    app.use(express.static(path.resolve(__dirname, 'dist')));
    app.get('*', (req, res) => {
      res.sendFile(path.resolve(__dirname, 'dist', 'index.html'));
    });
  } else {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  }

  app.listen(port, '0.0.0.0', () => {
    console.log(`Server listening on http://0.0.0.0:${port}`);
  });
}

startServer();
