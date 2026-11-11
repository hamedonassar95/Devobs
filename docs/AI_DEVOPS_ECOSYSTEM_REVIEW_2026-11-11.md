# مراجعة منظومة تكاملات DevOps والذكاء الاصطناعي — 2026-11-11

**المستودع:** `hamedonassar95/Devobs`

**رأس `main` الذي تمت مراجعته:** `ac3e3f042b4eb29e3ecda5b672e8d41cac81539f`، دمج PR #523.
**الحالة:** بحث في وثائق رسمية ومراجعة مصدرية؛ لا تفعيل لخدمة أو نموذج.

**VERIFIED — النطاق:** هذا مسح ممثل للمنصات المستخدمة أو ذات الصلة بالمستودع، وليس جردًا شاملًا لكل شركة أو منتج. ملف التسليم البحثي الكامل المذكور في خارطة Devobs لم يصل؛ هذا المسح لا يدّعي أنه بديل عنه أو أنه يغلق P0. لا يثبت وجود تشغيل حي، ولا يغير بوابات المشروع.

**VERIFIED — منهج المصادر:** استخدمت وثائق ومستودعات الناشرين الرسمية فقط. أعاد `codex mcp list` النص `No MCP servers configured yet`؛ لذلك لم تتوفر وصلة `openaiDeveloperDocs`، واعتمدت صفحة OpenAI Developers العامة كمصدر قراءة فقط.

## ما هو موجود الآن

- **VERIFIED:** يصف `README.md` مراحل AI-1 إلى AI-7 بأنها محلية وحتمية/إحصائية، مع API ولوحة قراءة فقط. وجود موصل أو workflow في المستودع لا يثبت طلب نموذج حي.
- **VERIFIED:** CI يحتوي Trivy وفحوص CodeQL وGitleaks وBandit و`pip-audit`، كما يحتوي بوابة Conftest 0.71.1 الضيقة لسياسة Terraform. لا نضيف ماسحًا أمنيًا مكررًا. تفاصيل Conftest في [PR #515](https://github.com/hamedonassar95/Devobs/pull/515)، و`policy/terraform/main.rego`، و[وثائق Conftest](https://www.conftest.dev/).
- **VERIFIED:** OpenTelemetry Collector وPrometheus وGrafana يعمل إعدادها كمكدس محلي اختياري؛ قياس API الحالي histogram واحد بلا تسميات، ولا توجد منه بيانات Render أو إنتاج. لوحتا p95 ومعدل الطلبات موجودتان في PR #524 المفتوح، وليستا بعد جزءًا من `main`.
- **VERIFIED:** `main` عند SHA أعلاه؛ CI على هذا SHA نجح في [run 43042463109](https://github.com/hamedonassar95/Devobs/actions/runs/43042463109)، بما فيه نشر GitHub Pages الثابت والتحقق منه. هذا ليس نشرًا لخدمة API.
- **VERIFIED من سجل المراجعة الحالي:** PR #524 مفتوح على SHA `8fb1ec5a2a06cfc3da8ad2d4e75fbf986f1148cf` وفحوصه المكتملة نجحت؛ لم يُدمج. إنشاء PR شغّل تكامل Vercel لمعاينة الفرع. لا يوجد في هذا العمل نشر إلى Render.
- **VERIFIED حسب سجل الجاهزية المؤرخ 2026-11-10:** P01 ما زال `NO-GO / BLOCKED`، وAI-9 `FAIL / BLOCKED`. حالة Render الحية بعد ذلك **UNVERIFIED** لأن وصلة Render طلبت إعادة المصادقة؛ لا أستنتج من السجل التاريخي أن الخدمة سليمة الآن.

## المصادر الرسمية وقرار الملاءمة

| المنظومة | ما تقوله المصادر الرسمية | ملاءمتها لـDevobs الآن |
| --- | --- | --- |
| **OpenTelemetry / CNCF** | **VERIFIED من المصدر الرسمي:** مستودع [GenAI Semantic Conventions](https://github.com/open-telemetry/semantic-conventions-genai) يغطي spans وmetrics وMCP ومزودين متعددين؛ ملف [GenAI spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-spans.md) يذكر أن الاتفاقيات في حالة **Development**. وقد تتضمن البيانات المحتوى الكامل للـprompts والردود عند تفعيل حقول المحتوى في التتبع ([شرح OTel](https://opentelemetry.io/blog/2026/genai-observability/)). | **ASSUMED — توصية:** نعيد استخدام Collector الحالي ونبدأ بمقاييس قليلة بلا محتوى prompts أو نتائج أدوات. لا نضيف backend أو logs/traces قبل موافقة خصوصية P13. |
| **Conftest / OPA** | **VERIFIED:** وثائق [Conftest](https://www.conftest.dev/) تصف فحص الإعدادات باستخدام سياسات؛ المستودع يثبت Conftest 0.71.1 ببصمة تحقق ويختبر سياسة Terraform محددة. | **ASSUMED — توصية:** إبقاؤه لفحص Terraform HCL فقط؛ لا تكرر السياسة بمسح عام آخر ولا تعتبره تحققًا من موارد Google الحية. |
| **Ollama / LocalAI** | **VERIFIED:** خيارات تشغيل محلية موثقة في [دليل Ollama](https://docs.ollama.com/) و[دليل LocalAI](https://localai.io/)، مع إصدارات/صور مثبتة في `models/README.md`. | **ASSUMED — توصية:** إبقاؤهما اختياريين؛ لا تحميل أوزان تلقائيًا ولا ربط تلقائيًا بـAI-1–AI-7. قبل اختيار نموذج يلزم فحص رخصة الأوزان ومتطلبات الجهاز وجودة المهمة. |
| **Prometheus / Grafana** | **VERIFIED:** للمشروعين مفتوحي المصدر [وثائق Prometheus](https://prometheus.io/docs/introduction/overview/) و[وثائق Grafana](https://grafana.com/docs/). | **ASSUMED — توصية:** إعادة استخدام المكدس المحلي الحالي؛ لا نضيف نسخة موازية أو نرسل بيانات الإنتاج إليه. |
| **GitHub Actions / Copilot** | **VERIFIED من المصدر الرسمي:** [إرشادات GitHub الأمنية](https://docs.github.com/en/actions/reference/security/secure-use) توصي بتثبيت Actions على SHA كامل، وتعرض lockfiles لتثبيت الاعتماديات العابرة. وثائق [OIDC](https://docs.github.com/en/actions/concepts/security/openid-connect) تشرح مصادقة قصيرة العمر للخدمات الخارجية بدل مفاتيح طويلة العمر. | **ASSUMED — توصية:** استمر في SHA pins والصلاحيات الدنيا الحالية. لا نضيف صلاحية أو workflow جديدًا لمجرد التجربة؛ OIDC لا يمنح وحده إذن تعديل موارد السحابة. |
| **OpenAI API** | **VERIFIED من مثال OpenAI الرسمي:** مثال [Responses API للتحكم بميزانية كل تشغيل](https://developers.openai.com/cookbook/articles/per_run_spending_controller_responses_api) يحجز تقدير تكلفة قبل الطلب؛ حدود المشروع والتنبيهات لا تمثل سقفًا مضمونًا لكل مهمة، وبعض الأدوات لها رسوم منفصلة. يوضح المثال أيضًا أن `store=false` لا يضمن وحده Zero Data Retention. | **ASSUMED — توصية:** إبقاء الاستدلال مؤجلًا؛ مفتاح API وفوترته منفصلان عن Copilot. أي تشغيل يحتاج سياسة حد لكل تشغيل، ومصدر تكلفة موثوقًا، ومراجعة الاحتفاظ بالبيانات. |
| **Google Cloud / Vertex AI** | **VERIFIED من المصدر الرسمي:** توصي وثائق [Workload Identity Federation](https://docs.cloud.google.com/iam/docs/workload-identities) بهاوية خارجية قصيرة العمر، وتشمل GitHub وGitLab، بدل مفاتيح حساب خدمة دائمة. | **ASSUMED — توصية:** إعادة استخدام التصميم فقط؛ توجد مسارات Vertex محروسة في المصدر. لا استدعاء `gcloud` أو Vertex؛ وأي استعمال يبقى مرتبطًا بموافقة P01 وهوية وصلاحية دنيا وسقف تكلفة موثق. |
| **AWS DevOps Agent** | **VERIFIED من وثائق AWS:** إعلان AWS الرسمي يذكر الإتاحة العامة بتاريخ 2026-03-31؛ وبطاقة الخدمة تصف وصولًا مقيدًا للقراءة وموافقة بشرية قبل إجراءات التخفيف ([الإعلان](https://aws.amazon.com/about-aws/whats-new/2026/03/aws-devops-agent-generally-available/)، [بطاقة الاستخدام المسؤول](https://docs.aws.amazon.com/ai/responsible-ai/aws-aidevops-agent/overview.html)). | **ASSUMED — توصية بحثية فقط:** خدمة مُدارة وليست أداة مفتوحة المصدر. لا نضيفها إلى حساب AWS بلا حاجة مثبتة، تسعير كامل، وتدقيق نطاق البيانات والصلاحيات. |
| **Anthropic / Claude Code** | **VERIFIED من المصدر الرسمي:** توثيق [Claude Code Action](https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md) يشرح خيارات OIDC في إعداد GitHub Actions؛ وملف [الأمن](https://github.com/anthropics/claude-code-action/blob/main/docs/security.md) يوصي بـ`GITHUB_TOKEN` محدود الصلاحية والمنتهي بعد التشغيل بدل PAT دائم لبعض المسارات. | **ASSUMED — توصية:** إعادة استخدام المساعد Claude الموثق والمحدود أصلًا عند الحاجة؛ لا نستبدله ولا نفعّل action جديدة، ونراجع workflow والصلاحيات والميزانية قبل أي تغيير. |
| **Microsoft Foundry** | **VERIFIED من المصدر الرسمي:** وثائق [التتبع ومعالجة البيانات](https://learn.microsoft.com/en-us/azure/foundry/observability/concepts/trace-data) تقول إن tracing متوقف افتراضيًا، وإن تفعيله يبدأ جمع وتخزين traces؛ وتوصي بإدارة RBAC وتنقيح البيانات الحساسة. | **ASSUMED — توصية:** عدم إضافة نقل traces إلى Azure Monitor/Foundry قبل تحديد المحتوى والاحتفاظ والصلاحيات والتكلفة. |
| **Render** | **VERIFIED من وثائق Render:** [health checks](https://render.com/docs/health-checks) تقول إن فحص HTTP ينجح مع `2xx` أو `3xx` خلال خمس ثوانٍ، وتفشل استجابات `4xx` أو `5xx`. | **UNVERIFIED — الحالة الحية:** لا إعادة استيراد Blueprint أو نشر. إعادة التحقق الحي تتطلب إعادة مصادقة وصلة Render؛ تاريخ 2026-11-10 يوثق نشرًا فاشلًا لا يثبت الوضع الحالي. |

## التسلسل الموصى به نحو الإنتاج — ASSUMED

1. **ASSUMED:** أغلق PR #524 بالمراجعة البشرية المعتادة إذا كان نطاقه مناسبًا؛ هو لوحات محلية فقط ولا يثبت telemetry مستضافة.
2. **ASSUMED:** أكمل P0 بمصدره الأصلي: أرسل `DEVOBS_AI_CODEX_HANDOFF_2026.md` وتقرير Deep Research الكامل أو أكد أن مسح المصادر الرسمية هذا هو النطاق المطلوب. لا أستبدل ملفًا غائبًا باستنتاجات.
3. **ASSUMED:** تحقق من Render قراءةً فقط بعد إعادة ربط الإضافة. لا تُشغّل deploy أو migration أو تفتح إعدادات الأسرار.
4. **VERIFIED — بوابة حالية:** أبقِ P01 على NO-GO حتى يوجد حد إجمالي تلقائي قابل للتحقق لا يتجاوز شرط المالك البالغ 100 دولار شهريًا، مع هوية وTLS/شبكة وعزل واستعادة مثبتة وموافقة مالك على SHA ونطاق محددين. [بوابة P01](P01_ACTIVATION_READINESS.md) تذكر أن هذا الشرط غير محقق.
5. **ASSUMED:** بعد تجاوز البوابات، نفّذ P13 بقياس minimized وموافقة خصوصية؛ P14 بمقارنة offline بمرجع مستقل؛ P15 بمساعد قراءة فقط ومدخلات منقحة؛ P16 بفحوص deterministic؛ P17 بفرض التكلفة قبل الاستدعاء؛ P18 بإنتاج proposals فقط؛ وP19 بتقييم قابل للتدقيق وتراجع موثق. AI-9 يبقى منفصلًا عن P01.

## حدود هذا المسح

- **UNVERIFIED:** أهلية حسابات Copilot وOpenAI وVertex وAWS وAzure، أسعارها الفعلية لخطة Devobs، وسياسات حفظ البيانات الفعلية؛ لم أقرأ إعدادات أو أسرار الحسابات.
- **UNVERIFIED:** صحة Render الحية الآن؛ موصل Render طلب إعادة مصادقة.
- **ASSUMED:** يمكن الاستفادة من الاتفاقيات المفتوحة وملفات CI الحالية دون إضافة مزود جديد؛ أي اعتماد جديد يحتاج مراجعة ترخيص وإصدار وبصمة وتكلفة منفصلة.
- **VERIFIED:** لم يُرسل استدلال مدفوع، ولم يُنفذ `gcloud` أو `terraform apply` أو نشر أو تعديل أسرار أو إعدادات سحابية ضمن هذه المراجعة.
