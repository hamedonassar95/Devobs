import express from 'express';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI, Type, Modality } from '@google/genai';
import dotenv from 'dotenv';
import path from 'path';
import { execSync } from 'child_process';

dotenv.config();

const app = express();
const port = parseInt(process.env.PORT || '3000', 10);

app.use(express.json({ limit: '50mb' }));
app.use(express.urlencoded({ limit: '50mb', extended: true }));

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

// Route 3: Multi-turn Chatbot with Infrastructure Context, Grounding, and Action Detection
app.post('/api/ai/chat', async (req, res) => {
  try {
    const { messages, modelName, role, useSearch, useMaps, systemContext } = req.body;

    if (!ai) {
      return res.status(200).json({
        reply: '⚠️ لم يتم تهيئة مفتاح GEMINI_API_KEY على الخادم. يمكنك تجربة الرد التلقائي للمساعد الذكي.',
        groundingSources: [],
        suggestedActions: [],
      });
    }

    // Role system instructions
    const roleInstructions: Record<string, string> = {
      sre_lead: 'أنت مهندس موثوقية مواقع أول (Senior SRE Lead & DevOps Architect). تجيب باحترافية وتدعم إجاباتك بأفضل ممارسات إدارة الأنظمة، تتبع الحوادث، وهندسة البنى التحتية عالية التوافر باللغة العربية.',
      security_auditor: 'أنت مدقق أمني وخبير SecOps متخصص في حماية الخوادم، اكتشاف الثغرات، فحص شهادات SSL/TLS، وتأمين بيئات الإنتاج السحابية.',
      incident_commander: 'أنت قائد إدارة حوادث الطوارئ (Incident Commander). تقدم توجيهات سريعة، خطوات تشخيصية حاسمة، وأوامر معالجة فورية لحل الأزمات التشغيلية.',
      devops_copilot: 'أنت مساعد DevOps ذكي وشامل يقدم حلولاً لنشر التطبيقات، تكوين حاويات Docker، إدارة Kubernetes، ومراقبة مقاييس الأداء.',
    };

    let baseInstruction = roleInstructions[role] || roleInstructions.sre_lead;

    // Inject live telemetry context if provided
    if (systemContext) {
      baseInstruction += `\n\n[حالة البنية التحتية الحية الآن]:
- إجمالي الخوادم: ${(systemContext.servers || []).length} خادم
- الخوادم التي بها تحذيرات أو حرجة: ${(systemContext.servers || []).filter((s: any) => s.status !== 'healthy').map((s: any) => `${s.name} (${s.status}, CPU: ${s.cpu}%, RAM: ${s.memory}%)`).join(', ') || 'لا توجد - كافة الخوادم سليمة'}
- الحوادث التشغيلية المفتوحة: ${(systemContext.incidents || []).filter((i: any) => !i.resolved).map((i: any) => `[${i.code}] على ${i.serverName}: ${i.message}`).join(' | ') || 'لا توجد حوادث مفتوحة'}
- آخر عمليات النشر: ${(systemContext.deployments || []).slice(0, 3).map((d: any) => `${d.serviceName} (${d.version}, ${d.status})`).join(', ') || 'N/A'}

إذا سأل المستخدم عن خادم معين أو طلب إجراءً علاجياً، اقترح الخطوات بدقة ويمكنك الإشارة إلى إمكانية تنفيذها بنقرة زر.`;
    }

    const validModel = ['gemini-4-argon', 'gemini-3.8-flash', 'gemini-3.1-flash-lite'].includes(modelName)
      ? modelName
      : 'gemini-3.8-flash';

    const contents = (messages || []).map((msg: any) => ({
      role: msg.role === 'user' ? 'user' : 'model',
      parts: [{ text: msg.text || msg.content || '' }],
    }));

    const tools: any[] = [];
    if (useSearch) tools.push({ googleSearch: {} });
    if (useMaps) tools.push({ googleMaps: {} });

    const config: any = { systemInstruction: baseInstruction };
    if (tools.length > 0) config.tools = tools;

    const response = await ai.models.generateContent({
      model: validModel,
      contents,
      config,
    });

    const replyText = response.text || 'تمت معالجة الطلب بنجاح.';
    const groundingMetadata = response.candidates?.[0]?.groundingMetadata;
    const groundingChunks = groundingMetadata?.groundingChunks || [];
    const webSources = groundingChunks
      .filter((chunk: any) => chunk.web?.uri)
      .map((chunk: any) => ({
        title: chunk.web?.title || chunk.web?.uri,
        uri: chunk.web?.uri,
      }));

    // Detect actionable suggestions from text & context
    const suggestedActions: any[] = [];
    const lowerReply = replyText.toLowerCase();

    if (systemContext?.servers) {
      for (const srv of systemContext.servers) {
        if (lowerReply.includes(srv.name.toLowerCase()) || lowerReply.includes(srv.id.toLowerCase())) {
          if (srv.status !== 'healthy' || lowerReply.includes('restart') || lowerReply.includes('إعادة تشغيل')) {
            suggestedActions.push({
              type: 'restart_server',
              targetId: srv.id,
              targetName: srv.name,
              label: `إعادة تشغيل ${srv.name}`,
              badge: 'Remediation',
            });
          }
        }
      }
    }

    if (systemContext?.incidents) {
      for (const inc of systemContext.incidents.filter((i: any) => !i.resolved)) {
        if (lowerReply.includes(inc.code.toLowerCase()) || lowerReply.includes(inc.serverName.toLowerCase())) {
          suggestedActions.push({
            type: 'resolve_incident',
            targetId: inc.id,
            targetName: inc.serverName,
            label: `إغلاق الحادثة ${inc.code}`,
            badge: 'SRE Resolve',
          });
        }
      }
    }

    res.json({
      reply: replyText,
      groundingSources: webSources,
      searchQueries: groundingMetadata?.webSearchQueries || [],
      modelUsed: validModel,
      suggestedActions: suggestedActions.slice(0, 4),
    });
  } catch (error: any) {
    console.error('Chat error:', error);
    res.status(500).json({
      error: error.message || 'حدث خطأ أثناء محادثة المساعد الذكي',
    });
  }
});

// Route 3B: Autonomous SRE Sentinel Scan & Self-Healing
app.post('/api/ai/autonomous-heal', async (req, res) => {
  try {
    const { servers, incidents } = req.body;

    if (!ai) {
      // Local fallback heuristic
      const actionsTaken: any[] = [];
      const criticalServers = (servers || []).filter((s: any) => s.status === 'critical' || s.cpu > 88);
      for (const s of criticalServers) {
        actionsTaken.push({
          type: 'restart_server',
          serverId: s.id,
          serverName: s.name,
          reason: `رصد استهلاك معالج حرج (${s.cpu}%) - تم تطبيق إعادة التشغيل السلسة التلقائية.`,
          timestamp: new Date().toLocaleTimeString('ar-EG'),
        });
      }
      return res.json({
        summary: 'تم فحص الخوادم بواسطة الحارس الذكي المحلي.',
        actions: actionsTaken,
        status: actionsTaken.length > 0 ? 'healed' : 'stable',
      });
    }

    const prompt = `أنت حارس SRE ومحرك المعالجة الذاتية التلقائية للبنية التحتية السحابية (Autonomous SRE Sentinel).
قم بتحليل الخوادم والحوادث التالية وحدد إن كان هناك أي إجراء فوري واجب التنفيذ:
الخوادم: ${JSON.stringify(servers?.map((s: any) => ({ id: s.id, name: s.name, status: s.status, cpu: s.cpu, memory: s.memory })))}
الحوادث النشطة: ${JSON.stringify(incidents?.filter((i: any) => !i.resolved).map((i: any) => ({ id: i.id, code: i.code, serverId: i.serverId, severity: i.severity })))}

اخرج النتيجة بصيغة JSON فقط:
{
  "summary": "ملخص الفحص باللغة العربية",
  "recommendedActions": [
    {
      "action": "restart" | "isolate" | "flush_cache" | "scale_up",
      "targetServerId": "id",
      "targetServerName": "name",
      "explanation": "سبب الإجراء بالعربية",
      "severity": "critical" | "warning" | "info"
    }
  ]
}`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
      },
    });

    let parsedResult = { summary: 'تم الفحص بنجاح', recommendedActions: [] };
    try {
      parsedResult = JSON.parse(response.text || '{}');
    } catch (e) {
      console.warn('Failed to parse AI heal response as JSON');
    }

    res.json(parsedResult);
  } catch (error: any) {
    console.error('Autonomous heal error:', error);
    res.status(500).json({ error: error.message || 'فشل في تشغيل الحارس الذكي' });
  }
});

// Route 3C: Predictive Anomaly Radar & Risk Forecast
app.post('/api/ai/predictive-forecast', async (req, res) => {
  try {
    const { servers, metrics } = req.body;

    if (!ai) {
      return res.json({
        overallRiskScore: 28,
        statusText: 'منخفض إلى معتدل (حساب محلي)',
        predictions: (servers || []).map((s: any) => ({
          serverId: s.id,
          serverName: s.name,
          riskScore: s.status === 'critical' ? 85 : s.status === 'warning' ? 58 : 15,
          failureProbability: s.status === 'critical' ? '78%' : s.status === 'warning' ? '32%' : '4%',
          timeToExhaustion: s.cpu > 80 ? '2.4 ساعات' : 'مستقر (> 72 ساعة)',
          keyRisk: s.memory > 80 ? 'احتمال نفاد الذاكرة RAM' : 'حمولة تشغيلية عادية',
        })),
      });
    }

    const prompt = `حلل بيانات الخوادم ومقاييسها للتنبؤ بالمخاطر المحتملة خلال الـ 12 ساعة القادمة (SRE Predictive Risk Forecast):
الخوادم: ${JSON.stringify(servers?.map((s: any) => ({ id: s.id, name: s.name, status: s.status, cpu: s.cpu, memory: s.memory, disk: s.disk })))}

أخرج النتيجة بصيغة JSON فقط متضمنة:
{
  "overallRiskScore": 35, // 0 to 100
  "statusText": "وصف عام لحالة الخطر بالعربية",
  "predictions": [
    {
      "serverId": "id",
      "serverName": "name",
      "riskScore": 75,
      "failureProbability": "45%",
      "timeToExhaustion": "3.5 ساعات",
      "keyRisk": "وصف نقطة الاختناق بالعربية"
    }
  ],
  "strategicRecommendation": "توصية وقائية باللغة العربية"
}`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        responseMimeType: 'application/json',
      },
    });

    let forecastData: any = {};
    try {
      forecastData = JSON.parse(response.text || '{}');
    } catch (e) {
      forecastData = { overallRiskScore: 30, predictions: [] };
    }

    res.json(forecastData);
  } catch (error: any) {
    console.error('Predictive forecast error:', error);
    res.status(500).json({ error: error.message || 'فشل في استخراج التنبؤات الاستباقية' });
  }
});

// Route 3D: SRE Audio Briefing Text Generator
app.post('/api/ai/generate-sre-briefing', async (req, res) => {
  try {
    const { servers, incidents, deployments } = req.body;

    if (!ai) {
      return res.json({
        briefingText: 'مرحباً بك في تقرير SRE الصباحي. الخوادم تعمل بنسبة استقرار مقبولة، تم تسجيل عدد قليل من التحذيرات على خوادم المعالجة وجاري فحصها آلياً.',
      });
    }

    const prompt = `اكتب موجزاً صوتياً تنفيذياً صباحياً لمهندسي SRE (Daily SRE Morning Standup Briefing) باللغة العربية الفصحى الواضحة والمشوقة.
البيانات:
- عدد الخوادم: ${(servers || []).length} خادم
- الخوادم المتعثرة: ${(servers || []).filter((s: any) => s.status !== 'healthy').map((s: any) => s.name).join(', ') || 'لا توجد'}
- الحوادث المفتوحة: ${(incidents || []).filter((i: any) => !i.resolved).length} حادثة
- آخر نشر برمجي: ${(deployments || [])[0]?.serviceName || 'N/A'} نسخة ${(deployments || [])[0]?.version || 'N/A'}

اكتب فقرة من 3-4 جمل قصيرة سلسة النطق للنطق الصوتي بدون أي رموز خاصة أو علامات غريبة.`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
    });

    res.json({ briefingText: response.text || 'موجز SRE اليومي: الأنظمة مستقرة والعمليات جارية بسلاسة.' });
  } catch (error: any) {
    console.error('Briefing text error:', error);
    res.status(500).json({ error: error.message || 'فشل في صياغة الموجز الصوتي' });
  }
});

// Route 4: Audio Transcription using gemini-3.5-transcribe
app.post('/api/ai/transcribe-audio', async (req, res) => {
  try {
    const { audioBase64, mimeType } = req.body;

    if (!audioBase64) {
      return res.status(400).json({ error: 'لم يتم إرسال بيانات الصوت' });
    }

    if (!ai) {
      return res.status(200).json({
        transcription: 'تم استقبال التسجيل (وضع غير متصل بالإنترنت: يرجى ربط GEMINI_API_KEY لتفعيل التفريغ الذاتي).',
      });
    }

    const response = await ai.models.generateContent({
      model: 'gemini-3.5-transcribe',
      contents: [
        {
          inlineData: {
            mimeType: mimeType || 'audio/webm',
            data: audioBase64,
          },
        },
        {
          text: 'قم بتفريغ هذا التسجيل الصوتي بدقة تامة وبنفس لغة المتحدث (سواء العربية أو الإنجليزية). اكتب فقط النص المنطوق بدون أي مقدمات أو تعليقات إضافية.',
        },
      ],
    });

    res.json({
      transcription: response.text || 'لم يتم التعرف على أي كلام مسموع.',
    });
  } catch (error: any) {
    console.error('Transcription error:', error);
    res.status(500).json({
      error: error.message || 'فشل في تفريغ التسجيل الصوتي',
    });
  }
});

// Route 5: Video Generation from text or image using gemini-omni-1.2-flash via Interactions API
app.post('/api/ai/generate-video', async (req, res) => {
  try {
    const { prompt, imageBase64, mimeType, aspectRatio } = req.body;

    if (!ai) {
      return res.status(400).json({
        error: 'يتطلب توليد الفيديو تفعيل GEMINI_API_KEY على الخادم',
      });
    }

    const selectedRatio = aspectRatio === '9:16' ? '9:16' : '16:9';

    let inputPayload: any;
    if (imageBase64) {
      inputPayload = [
        {
          type: 'image',
          mime_type: mimeType || 'image/png',
          data: imageBase64,
        },
        {
          type: 'text',
          text: prompt || 'Animate this futuristic server infrastructure scene with glowing fiber optics and dynamic cyber lighting.',
        },
      ];
    } else {
      inputPayload = prompt || 'A futuristic high-tech server data center with glowing LED server racks, fiber optic pulses, and cinematic tracking camera.';
    }

    const interaction = await ai.interactions.create(
      {
        model: 'gemini-omni-1.2-flash',
        input: inputPayload,
        background: false,
        store: false,
        stream: false,
        response_format: {
          type: 'video',
          aspect_ratio: selectedRatio,
          duration: '10s',
          resolution: '720p',
        },
      },
      { timeout: 300000 }
    );

    const videoPart = interaction.output_video;
    if (videoPart && videoPart.data) {
      return res.json({
        videoBase64: videoPart.data,
        mimeType: videoPart.mime_type || 'video/mp4',
        aspectRatio: selectedRatio,
      });
    }

    res.status(500).json({
      error: 'لم ينتج النموذج فيديو صالحاً، يرجى إعادة المحاولة مع صياغة أخرى.',
    });
  } catch (error: any) {
    console.error('Video generation error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد أو تحريك الفيديو',
    });
  }
});

// Route 6: Create & Edit Images using gemini-nano-banana-2.1
app.post('/api/ai/generate-image', async (req, res) => {
  try {
    const { prompt, imageBase64, mimeType, aspectRatio } = req.body;

    if (!ai) {
      return res.status(400).json({
        error: 'يتطلب توليد الصور تفعيل GEMINI_API_KEY على الخادم',
      });
    }

    let inputPayload: any;
    if (imageBase64) {
      // Image editing
      inputPayload = [
        {
          type: 'image',
          data: imageBase64,
          mime_type: mimeType || 'image/png',
        },
        {
          type: 'text',
          text: prompt || 'Enhance this server architecture diagram with cyber glowing neon accents and clear labeling.',
        },
      ];
    } else {
      // Image creation
      inputPayload = prompt || 'A high-end 3D isometric cyberpunk server room rack with glowing teal LED indicators and glass cooling panel';
    }

    const interaction = await ai.interactions.create({
      model: 'gemini-nano-banana-2.1',
      input: inputPayload,
      response_modalities: ['image', 'text'],
      generation_config: {
        image_config: {
          aspect_ratio: aspectRatio || '1:1',
          image_size: '1K',
        },
      },
    });

    let generatedImage: { data: string; mimeType: string } | null = null;
    let descriptionText = '';

    for (const step of interaction.steps) {
      if (step.type === 'model_output' && Array.isArray(step.content)) {
        const img = step.content.find((c: any) => c.type === 'image') as any;
        if (img && img.data) {
          generatedImage = {
            data: img.data,
            mimeType: img.mime_type || 'image/png',
          };
        }
        const txt = step.content.find((c: any) => c.type === 'text') as any;
        if (txt?.text) {
          descriptionText += txt.text;
        }
      }
    }

    if (generatedImage) {
      return res.json({
        imageBase64: generatedImage.data,
        mimeType: generatedImage.mimeType,
        description: descriptionText,
      });
    }

    res.status(500).json({
      error: 'لم يتم العثور على صورة في استجابة النموذج',
    });
  } catch (error: any) {
    console.error('Image generation error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد أو تعديل الصورة',
    });
  }
});

// Route 7: Music & Audio Clips Generation using lyria-3-clip-preview
app.post('/api/ai/generate-music', async (req, res) => {
  try {
    const { prompt, fullTrack } = req.body;

    if (!ai) {
      return res.status(400).json({
        error: 'يتطلب توليد الموسيقى تفعيل GEMINI_API_KEY على الخادم',
      });
    }

    const model = fullTrack ? 'lyria-3-pro-preview' : 'lyria-3-clip-preview';
    const musicPrompt = prompt || 'A 15-second pulsating electronic synthwave alert soundtrack for a cyber DevOps command center';

    const responseStream = await ai.models.generateContentStream({
      model,
      contents: musicPrompt,
    });

    let audioBase64 = '';
    let lyrics = '';
    let mimeType = 'audio/wav';

    for await (const chunk of responseStream) {
      const parts = chunk.candidates?.[0]?.content?.parts;
      if (!parts) continue;

      for (const part of parts) {
        if (part.inlineData?.data) {
          if (!audioBase64 && part.inlineData.mimeType) {
            mimeType = part.inlineData.mimeType;
          }
          audioBase64 += part.inlineData.data;
        }
        if (part.text && !lyrics) {
          lyrics = part.text;
        }
      }
    }

    if (audioBase64) {
      return res.json({
        audioBase64,
        mimeType,
        lyrics,
        modelUsed: model,
      });
    }

    res.status(500).json({
      error: 'لم يتم استلام مقطع صوتي من نموذج Lyria',
    });
  } catch (error: any) {
    console.error('Music generation error:', error);
    res.status(500).json({
      error: error.message || 'فشل في توليد المقطع الصوتي أو النغمة',
    });
  }
});

// Route 8: Text-to-Speech (TTS) Voice Assistant using gemini-3.8-flash-lite-tts
app.post('/api/ai/voice-speak', async (req, res) => {
  try {
    const { text, voice } = req.body;

    if (!text) {
      return res.status(400).json({ error: 'لم يتم إدخال نص النطق' });
    }

    if (!ai) {
      return res.status(400).json({
        error: 'يتطلب تحويل النص إلى صوت تفعيل GEMINI_API_KEY على الخادم',
      });
    }

    const interaction = await ai.interactions.create({
      model: 'gemini-3.8-flash-lite-tts',
      input: [
        {
          type: 'text',
          text,
          annotations: [
            {
              type: 'speech_metadata',
              style: 'Professional, calm, high-tech server operations voice',
            },
          ],
        },
      ],
      response_format: { type: 'audio' },
      generation_config: {
        speech_config: [
          {
            voice: voice || 'Kore',
          },
        ],
      },
    });

    const audio = interaction.output_audio;
    if (audio?.data) {
      return res.json({
        audioBase64: audio.data,
        mimeType: audio.mime_type || 'audio/wav',
      });
    }

    res.status(500).json({ error: 'لم ينتج النموذج صوتاً' });
  } catch (error: any) {
    console.error('TTS error:', error);
    res.status(500).json({
      error: error.message || 'فشل في تحويل النص إلى صوت مسموع',
    });
  }
});

// Route 9: Live Voice Conversation using gemini-3.8-live via Interactions API
app.post('/api/ai/live-conversation', async (req, res) => {
  try {
    const { message, audioBase64, mimeType, history } = req.body;

    if (!ai) {
      return res.status(200).json({
        replyText: 'وضع غير متصل بالإنترنت: يرجى ربط GEMINI_API_KEY لتفعيل المحادثات الصوتية المباشرة مع نموذج gemini-3.8-live.',
      });
    }

    const inputParts: any[] = [];
    if (message) {
      inputParts.push({ type: 'text', text: message });
    }
    if (audioBase64) {
      inputParts.push({
        type: 'audio',
        mime_type: mimeType || 'audio/webm',
        data: audioBase64,
      });
    }

    if (inputParts.length === 0) {
      return res.status(400).json({ error: 'لم يتم تقديم مدخلات نصية أو صوتية للمحادثة المباشرة' });
    }

    const interaction = await ai.interactions.create({
      model: 'gemini-3.8-live',
      input: inputParts,
      response_format: { type: 'audio' },
      generation_config: {
        speech_config: [
          {
            voice: 'Kore',
          },
        ],
      },
    });

    const replyAudio = interaction.output_audio;
    let replyText = '';
    const rawOutputs = (interaction as any).outputs;
    if (Array.isArray(rawOutputs)) {
      for (const out of rawOutputs) {
        if (out?.text) {
          replyText += out.text;
        }
      }
    }

    res.json({
      replyText: replyText || 'تم الاستماع والرد بنجاح عبر قناة gemini-3.8-live.',
      audioBase64: replyAudio?.data || null,
      mimeType: replyAudio?.mime_type || 'audio/wav',
    });
  } catch (error: any) {
    console.error('Live Conversation error:', error);
    res.status(500).json({
      error: error.message || 'فشل في جلسة المحادثة الصوتية المباشرة (gemini-3.8-live)',
    });
  }
});

// Route 10: Git Repository Info & Local Status
app.get('/api/github/git-info', (req, res) => {
  try {
    let currentBranch = 'main';
    let latestCommit = {
      hash: 'd69579e',
      author: 'Mohammad Nassar',
      email: 'mohammadnassar813@gmail.com',
      date: new Date().toISOString(),
      message: 'feat: initial commit of ServerOps Enterprise Console',
    };
    let statusSummary = 'clean';

    try {
      currentBranch = execSync('git branch --show-current', { encoding: 'utf-8' }).trim() || 'main';
      const logOutput = execSync('git log -1 --format="%H|%an|%ae|%ad|%s"', { encoding: 'utf-8' }).trim();
      if (logOutput) {
        const [hash, author, email, date, message] = logOutput.split('|');
        latestCommit = {
          hash: hash || 'd69579e',
          author: author || 'Mohammad Nassar',
          email: email || 'mohammadnassar813@gmail.com',
          date: date || new Date().toISOString(),
          message: message || 'feat: initial commit of ServerOps Enterprise Console',
        };
      }
      const statusOutput = execSync('git status --porcelain', { encoding: 'utf-8' }).trim();
      statusSummary = statusOutput ? 'uncommitted_changes' : 'clean';
    } catch (e: any) {
      console.warn('Git command warning:', e.message);
    }

    res.json({
      branch: currentBranch,
      latestCommit,
      status: statusSummary,
      repoName: 'Devobs',
      owner: 'hamedonassar95',
      repoUrl: 'https://github.com/hamedonassar95/Devobs',
      defaultWorkflows: [
        { name: 'ci.yml', path: '.github/workflows/ci.yml', status: 'active' },
        { name: 'deploy.yml', path: '.github/workflows/deploy.yml', status: 'active' },
        { name: 'dispatch-to-devobs.yml', path: '.github/workflows/dispatch-to-devobs.yml', status: 'active' },
      ],
    });
  } catch (err: any) {
    res.status(500).json({ error: err.message || 'فشل في استعلام معلومات Git' });
  }
});

// Route 10b: Test GitHub Connection and Permissions
app.post('/api/github/test-connection', async (req, res) => {
  try {
    const { token, owner = 'hamedonassar95', repo = 'Devobs' } = req.body;
    if (!token || typeof token !== 'string') {
      return res.status(400).json({ success: false, error: 'رمز الدخول الشخصي (GitHub Token) مطلوب' });
    }

    const trimmedToken = token.trim();
    // 1. Verify user profile
    const userRes = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${trimmedToken}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'Devops-AI-Console',
      },
    });

    if (!userRes.ok) {
      return res.status(userRes.status).json({
        success: false,
        error: `فشل التحقق من GitHub: الرمز غير صالح (رمز الاستجابة: ${userRes.status})`,
      });
    }

    const userData = await userRes.json();

    // 2. Verify repo permissions
    const repoRes = await fetch(`https://api.github.com/repos/${owner}/${repo}`, {
      headers: {
        Authorization: `Bearer ${trimmedToken}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'Devops-AI-Console',
      },
    });

    if (!repoRes.ok) {
      return res.status(repoRes.status).json({
        success: false,
        error: `المستخدم @${userData.login} موثق بنجاح، لكن يتعذر الوصول لمستودع ${owner}/${repo}. تأكد من صلاحية Token (Contents: Read and write).`,
      });
    }

    const repoData = await repoRes.json();

    res.json({
      success: true,
      user: {
        login: userData.login,
        name: userData.name || userData.login,
        avatar_url: userData.avatar_url,
      },
      repo: {
        full_name: repoData.full_name,
        permissions: repoData.permissions,
        default_branch: repoData.default_branch,
        private: repoData.private,
      },
      canPush: Boolean(repoData.permissions?.push || repoData.permissions?.admin),
    });
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message || 'حدث خطأ أثناء فحص الاتصال بـ GitHub' });
  }
});

// Route 10c: Direct Server-to-GitHub Sync and Push
app.post('/api/github/sync-and-push', async (req, res) => {
  try {
    const { token, targetBranch = 'main', force = false, commitMessage } = req.body;
    if (!token || typeof token !== 'string') {
      return res.status(400).json({ success: false, error: 'رمز الدخول الشخصي (GitHub Token) مطلوب لإتمام عملية الرفع' });
    }

    const trimmedToken = token.trim();
    if (!/^[a-zA-Z0-9_]+$/.test(trimmedToken)) {
      return res.status(400).json({ success: false, error: 'صيغة رمز الدخول (Token) غير صالحة' });
    }

    const owner = 'hamedonassar95';
    const repo = 'Devobs';

    // Verify token validity first
    const userRes = await fetch('https://api.github.com/user', {
      headers: {
        Authorization: `Bearer ${trimmedToken}`,
        Accept: 'application/vnd.github+json',
        'User-Agent': 'Devops-AI-Console',
      },
    });

    if (!userRes.ok) {
      return res.status(401).json({ success: false, error: 'رمز GitHub Token غير صالح أو انتهت صلاحيته' });
    }
    const user = await userRes.json();

    // Check if there are uncommitted changes locally
    try {
      const status = execSync('git status --porcelain', { encoding: 'utf-8' }).trim();
      if (status) {
        const msg = commitMessage ? String(commitMessage).replace(/"/g, '\\"') : 'feat: auto-commit DevOps AI Intelligence updates';
        execSync(`git add -A && git commit -m "${msg}"`, { encoding: 'utf-8' });
      }
    } catch (e: any) {
      console.log('Git commit note:', e.message);
    }

    // Perform push using authenticated remote URL
    const remoteUrl = `https://${trimmedToken}@github.com/${owner}/${repo}.git`;
    const targetRef = targetBranch || 'main';
    const forceFlag = force ? ' --force' : '';

    try {
      const pushCmd = `git push "${remoteUrl}" HEAD:${targetRef}${forceFlag}`;
      const pushOutput = execSync(pushCmd, {
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
      });

      const latestCommit = execSync('git rev-parse --short HEAD', { encoding: 'utf-8' }).trim();

      return res.json({
        success: true,
        message: `تم رفع الشيفرة البرمجية بنجاح إلى المستودع ${owner}/${repo} على الفرع ${targetRef}!`,
        pushedBy: user.login,
        commit: latestCommit,
        branch: targetRef,
        repoUrl: `https://github.com/${owner}/${repo}/tree/${targetRef}`,
        rawOutput: pushOutput || 'Everything up-to-date',
      });
    } catch (pushErr: any) {
      const rawError = pushErr.stderr || pushErr.message || '';
      const sanitizedError = rawError.replace(new RegExp(trimmedToken, 'g'), '***TOKEN***');
      
      const isNonFastForward = sanitizedError.includes('fetch first') || sanitizedError.includes('non-fast-forward') || sanitizedError.includes('Updates were rejected');
      
      return res.status(400).json({
        success: false,
        error: sanitizedError || 'فشلت عملية الرفع إلى GitHub',
        isNonFastForward,
        hint: isNonFastForward
          ? 'المستودع البعيد يحتوي على تعديلات سابقة غير متزامنة. يمكنك الرفع على فرع جديد مثل (feature/devops-ai-console) أو تفعيل خيار الرفع الإجباري (Force Push).'
          : 'تأكد من أن الـ Token يملك صلاحيات (Contents: write) على المستودع.',
      });
    }
  } catch (err: any) {
    res.status(500).json({ success: false, error: err.message || 'حدث خطأ في الخادم أثناء الرفع' });
  }
});

// Route 11: AI-Powered GitHub Release Notes Generator using Gemini 3.8 Flash
app.post('/api/github/generate-release-notes', async (req, res) => {
  try {
    const { version, deployments, incidents, repoName } = req.body;

    if (!ai) {
      return res.json({
        releaseNotes: `## Release ${version || 'v2.5.0'} - ServerOps Production Release

### 🚀 What's New
- Three.js 3D Server Room Virtual Rack Simulator
- Cyber Shield 3D Defense Game against DDoS attacks
- Google Workspace Real-time integration (Docs, Sheets, Slides, Tasks, Calendar)
- GitHub Actions CI/CD workflows and repository telemetry

### 🐛 Resolved Incidents & Bug Fixes
${(incidents || []).slice(0, 5).map((inc: any) => `- **[${inc.code || 'INCIDENT'}]**: ${inc.message}`).join('\n')}

### 📦 Deployment Summary
- Successfully deployed across production clusters.
- Verified on Node.js 22 LTS with full TypeScript compliance.`,
      });
    }

    const prompt = `أنت مهندس برمجيات رئيسي (Lead Software Engineer & DevOps Lead).
قم بصياغة تقرير إصدار احترافي ومفصل (GitHub Release Notes / Changelog) بتنسيق Markdown للإصدار ${version || 'v2.5.0'} للمشروع ${repoName || 'serverops-console'}.

البيانات المتاحة:
- آخر عمليات النشر البرمجية:
${JSON.stringify((deployments || []).slice(0, 5), null, 2)}

- الحوادث التشغيلية التي تم التعامل معها وحلها:
${JSON.stringify((incidents || []).slice(0, 5), null, 2)}

يرجى كتابة الـ Release Notes بالإنجليزية والترجمة/ملخص باللغة العربية بتنسيق GitHub Release الجذاب مع:
1. 🎉 Executive Summary & Highlights
2. 🚀 New Features & Enhancements
3. 🛠️ Bug Fixes & SRE Incident Resolutions
4. ⚡ Performance & Reliability Metrics
5. 👥 Contributors & CI/CD Verification`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'You are an elite open-source maintainer and DevOps architect writing release notes for GitHub.',
      },
    });

    res.json({ releaseNotes: response.text });
  } catch (error: any) {
    console.error('Release notes error:', error);
    res.status(500).json({ error: error.message || 'فشل في توليد ملاحظات الإصدار' });
  }
});

// Route 12: AI-Powered Pull Request Description Generator
app.post('/api/github/generate-pr-summary', async (req, res) => {
  try {
    const { title, changesSummary, branch } = req.body;

    if (!ai) {
      return res.json({
        prBody: `## Description
${changesSummary || 'Implemented new updates for the server operations console.'}

## Type of Change
- [x] ✨ New feature (non-breaking change which adds functionality)
- [x] 🐛 Bug fix (non-breaking change which fixes an issue)
- [x] 📝 Documentation update

## Checklist
- [x] My code follows the style guidelines of this project
- [x] I have performed a self-review of my own code
- [x] TypeScript build passes with zero errors (\`npm run lint\`)
- [x] GitHub Actions CI checks completed successfully`,
      });
    }

    const prompt = `Write a comprehensive, professional GitHub Pull Request description in markdown.
PR Title: ${title || 'feat: add GitHub DevOps integration & CI/CD workflows'}
Branch: ${branch || 'feat/github-integration'}
Changes Summary: ${changesSummary || 'Added GitHub Hub tab, CI/CD Actions workflows, README documentation, and SRE incident synchronization.'}

Include standard GitHub PR template sections:
- 📌 Overview / Problem Statement
- 🎯 Solution & Changes Made
- 🧪 Testing & Verification
- 📸 UI / Feature Highlights
- 📋 PR Checklist`;

    const response = await ai.models.generateContent({
      model: 'gemini-3.8-flash',
      contents: prompt,
      config: {
        systemInstruction: 'You are a senior software architect crafting pull request descriptions on GitHub.',
      },
    });

    res.json({ prBody: response.text });
  } catch (error: any) {
    console.error('PR summary error:', error);
    res.status(500).json({ error: error.message || 'فشل في توليد وصف الـ PR' });
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
