# تكامل Argo CD MCP المحلي والاختياري

يضيف هذا المثال طريقة اختيارية لمطوّر Devobs كي يسأل Codex عن حالة تطبيقات Argo CD التي يسمح له رمزه بقراءتها. يعرض `list_applications` حالة المزامنة والصحة وملخص التطبيق. لا يضيف اتصالًا إلى خدمة Devobs أو CI أو النشر، ولا يشغّل عمليات مزامنة أو تغييرات على Argo CD.

## المصدر المثبّت

- المشروع الرسمي: [`argoproj-labs/mcp-for-argocd`](https://github.com/argoproj-labs/mcp-for-argocd/tree/v0.9.0)، الإصدار `v0.9.0`، commit `28d15ca69b0c31387cc6ec73d201fd13c5d22b6a`.
- رخصة upstream: [Apache-2.0](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/LICENSE).
- الصورة الرسمية المستخدمة: [`ghcr.io/argoproj-labs/mcp-for-argocd`](https://github.com/orgs/argoproj-labs/packages/container/package/mcp-for-argocd?tag=0.9.0)، مثبتة على OCI index digest `sha256:dffc6c719d8635be2d5f2c8ad1c0178540325da4b40da0b373307e12b4c48f86`.
- بيان بناء SLSA في الصورة يربط صورة Linux/amd64 ذات digest `sha256:c8cb6ab894cdbd231afbfa901004ece8b09da8714d8e5ce70a303ba18a2f7a92` وصورة Linux/arm64 ذات digest `sha256:eea75ab1bbbde9022a1e570df648131e21ce7b54a9eb876a4fed5642dd8c4a42` بمصدر GitHub والـcommit المذكور. نجح [سير عمل إصدار الحاوية upstream](https://github.com/argoproj-labs/mcp-for-argocd/actions/runs/31507615066).

## حدود الصلاحيات

- المثال يشغّل صورة Docker الرسمية عبر `stdio` محليًا، ولا يفتح منفذ HTTP. يثبت digest الصورة ويطلب Docker سحبها منه؛ يحتاج Docker Engine يعمل على الجهاز.
- يثبت الخادم على `MCP_READ_ONLY=true`؛ يذكر upstream أن هذا يعطّل أدوات الإنشاء والتعديل والحذف والمزامنة وتشغيل إجراءات الموارد.
- إعداد Codex يسمح بأداة `list_applications` وحدها ويطلب موافقة عند كل استدعاء. هذا تقييد على جهة Codex وليس حاجز صلاحيات مستقلًا.
- صلاحية Argo CD الفعلية تأتي من الرمز: أنشئ رمزًا منفصلًا للقراءة فقط ومقيّدًا بتطبيق أو مشروع تطوير غير إنتاجي واحد. لا تستخدم رمز مسؤول، ولا تمنحه وصولًا لمشاريع العملاء أو الإنتاج. اتبع [مرجع Argo CD RBAC الرسمي](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/) لضبط صلاحيات الحساب والـproject.
- نتيجة الأداة تتضمن بيانات وصفية عن التطبيقات، مثل المصدر والوجهة والوسوم وحالة المزامنة. لا تستخدمها مع بيانات عميل أو معلومات حساسة؛ إخراج MCP قد يدخل في سياق Codex.
- لا تحفظ `ARGOCD_API_TOKEN` أو عنوانًا داخليًا في المستودع. يمرّر المثال متغيري `ARGOCD_BASE_URL` و`ARGOCD_API_TOKEN` من بيئة Codex المحلية فقط. خزّن الرمز خارج Git وابدأ Codex من بيئة محلية موثوقة.
- رغم `MCP_READ_ONLY=true`، لا تثق في إخفاء الأدوات أو واجهة الموافقة وحدهما؛ قيد رمز Argo CD نفسه بأقل صلاحية لازمة.

## إعداد اختياري على Windows

1. ثبّت Docker Engine وCodex من مصادرهما الرسمية، وتأكد أن Docker CLI يصل إلى المحرك.
2. اطلب من مسؤول Argo CD رمزًا مستقلًا للقراءة فقط ومحصورًا في مشروع تطوير غير إنتاجي. لا تلصق الرمز في المحادثة ولا تحفظه في ملف بالمستودع.
3. عيّن `ARGOCD_BASE_URL` و`ARGOCD_API_TOKEN` في بيئة محلية موثوقة قبل تشغيل Codex. لا تضع قيمة الرمز في `config.toml`؛ `env_vars` في المثال تسمح بتمرير متغيرات بيئة موجودة إلى عملية الخادم.
4. انسخ جدول `[mcp_servers.argocd]` من [مثال Codex](../.codex/examples/argocd-mcp-readonly.toml) إلى `%USERPROFILE%\.codex\config.toml`، من دون استبدال الإعدادات الموجودة. يجب أن يكون عنوان `ARGOCD_BASE_URL` متاحًا من شبكة الحاوية؛ إذا كان Argo CD يعمل على Windows نفسه، راجع طريقة الوصول إلى المضيف من [Docker Desktop](https://docs.docker.com/desktop/features/networking/#i-want-to-connect-from-a-container-to-a-service-on-the-host).
5. أعد تشغيل Codex، وتأكد أن الخادم يعرض `list_applications` فقط. ابدأ بطلب قائمة تطبيقات مشروع التطوير، وراجع المخرجات قبل مشاركتها. إذا طلب Codex أداة أخرى أو ظهر تطبيق خارج النطاق، أوقف الاستخدام وراجع رمز Argo CD.
6. للإيقاف، احذف جدول `mcp_servers.argocd` من إعداد Codex الشخصي، وألغِ الرمز المنفصل من Argo CD.

## حالة التحقق والمصادر

- **VERIFIED:** commit الإصدار وتوقيعه، ورخصة Apache-2.0، وOCI index digest وبَيانا بناء SLSA وصورة الحاوية، ونجاح سير عمل الإصدار upstream.
- **UNVERIFIED:** لم نشغّل خادم MCP، ولم نتصل بـArgo CD أو نستخدم رمزًا أو بيانات تطبيقات. المثال غير مفعّل في `.codex/config.toml`، ولا يثبت أن إعداد Codex أو اتصال المستخدم يعمل.
- قبول Codex runtime يبقى **OPEN**؛ AI-9 وP01 يبقيان **BLOCKED**.

المراجع الرسمية:

- [Argo CD MCP v0.9.0](https://github.com/argoproj-labs/mcp-for-argocd/tree/v0.9.0)، [README والأدوات](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/README.md)، [رخصة Apache-2.0](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/LICENSE).
- [حاوية GHCR للإصدار 0.9.0](https://github.com/orgs/argoproj-labs/packages/container/package/mcp-for-argocd?tag=0.9.0) و[سير عمل بناء الحاوية](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/.github/workflows/docker.yml).
- [مرجع Argo CD RBAC](https://argo-cd.readthedocs.io/en/stable/operator-manual/rbac/).
- [إعداد خوادم MCP في Codex](https://developers.openai.com/codex/mcp).
