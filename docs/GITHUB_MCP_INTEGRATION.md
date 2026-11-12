# تكامل GitHub MCP الاختياري للمطورين

## ما الذي يضيفه؟

يتيح لمطوّر Devobs، من Codex على جهازه، قراءة ملفات المستودعات العامة والـissues وطلبات الدمج ونتائج Actions عبر أدوات GitHub الرسمية. هذا امتداد لبيئة المطوّر فقط؛ لا يضيف خدمة إلى صفحة Devobs أو CI، ولا يفعّل ذكاءً اصطناعيًا أو يغيّر بوابات AI-9 وP01.

الإعداد **غير مفعّل افتراضيًا**. المثال في [`.codex/examples/github-mcp-readonly.toml`](../.codex/examples/github-mcp-readonly.toml) مستقل عن `.codex/config.toml` ولا يبدأ Docker أو يطلب تسجيل دخول ما لم ينسخه المستخدم إلى إعداد Codex الموثوق لديه.

## النسخة ومصدرها

- **VERIFIED:** خادم [GitHub MCP Server](https://github.com/github/github-mcp-server) مفتوح المصدر برخصة MIT. استخدمنا الإصدار `v2.1.0` عند المصدر `4bcdcdf8d7beee98c9448e73e257308280924cc4`.
- **VERIFIED:** الصورة مثبتة على `ghcr.io/github/github-mcp-server:v2.1.0@sha256:f6056fc10bfffcc8c81a6417a2e9ca12808647e8dd6049642a4feaadee0e0f8a`؛ بصمة OCI استُخرجت من سجل GHCR العام بتاريخ 2026-11-12.
- **VERIFIED:** Codex يدعم إعداد خوادم MCP المحلية عبر STDIO باستخدام `command` و`args` و`env` و`env_vars`، ويحمّل إعداد المشروع فقط عند الوثوق بالمستودع. راجع [دليل Codex الرسمي](https://developers.openai.com/codex/mcp).
- **VERIFIED:** خادم GitHub يدعم متغيرات `GITHUB_READ_ONLY` و`GITHUB_TOOLSETS` و`GITHUB_OAUTH_SCOPES`، ويقيّد نشر المنفذ بعنوان loopback عند Docker. راجع [دليل إعداد الخادم](https://github.com/github/github-mcp-server/blob/v2.1.0/docs/server-configuration.md) و[دليل OAuth المحلي](https://github.com/github/github-mcp-server/blob/v2.1.0/docs/oauth-login.md).

## إعداد اختياري على Windows

1. ثبّت Docker Desktop وCodex، وشغّل Docker Desktop.
2. افتح ملف إعداد Codex الشخصي `%USERPROFILE%\.codex\config.toml`. إذا كان فيه إعدادات MCP، أضف جدول `mcp_servers.github` وحقوله من المثال؛ لا تستبدل إعداداتك الحالية ولا تنسخ المثال إلى إعداد المستودع العام.
3. أعد تشغيل Codex وافتح `/mcp`. عند أول طلب ستحتاج للمصادقة مع GitHub. يحمّل Docker الصورة المثبتة عند أول تشغيل.
4. جرّب طلب قراءة مثل: «اعرض ملفات README ونتائج Actions في مستودع عام أملكه». لا تستخدمه لإنشاء issues أو تعديل ملفات؛ الإعداد لا يعرّض أدوات الكتابة.

الإعداد يختار مجموعات `repos,issues,pull_requests,actions` ويطلب نطاق OAuth `public_repo` فقط. إذا أردت وصولًا إلى مستودعات خاصة، لا توسّع النطاق عشوائيًا: أنشئ Fine-grained PAT بصلاحيات قراءة فقط للمستودعات المطلوبة، خزّنه في متغير بيئة محلي اسمه `GITHUB_PERSONAL_ACCESS_TOKEN`، ثم أعد تشغيل Codex. Codex يمرر هذا المتغير إلى العملية عبر `env_vars`؛ لا تضع قيمته في TOML أو المستودع.

## حدود الأمان والتحقق

- `GITHUB_READ_ONLY=true` يجعل الخادم لا يعرض أدوات التعديل. هذا يقيّد واجهة MCP، لكنه لا يحوّل منحة OAuth نفسها إلى رمز GitHub للقراءة فقط. عند الحاجة إلى قيد حسابي أقوى، استخدم Fine-grained PAT مقصورًا على المستودعات والصلاحيات المقروءة فقط.
- Docker ينشر callback على `127.0.0.1:8085` فقط؛ إذا كان المنفذ مستخدمًا، أوقف الإعداد بدل نشره على كل واجهات الشبكة.
- لا يُخزّن المثال أي كلمة مرور أو PAT أو مفتاح، ولا يفعّل خادم MCP داخل CI أو على الموقع المنشور.
- **UNVERIFIED:** لم نشغّل Docker أو OAuth أو استدعاء GitHub حيًا؛ قبول TOML وفحوص المستودع تثبتان سلامة الإعداد المكتوب فقط، لا اكتمال تسجيل الدخول أو التشغيل.

## مراجع upstream

- [دليل GitHub MCP لـCodex](https://github.com/github/github-mcp-server/blob/v2.1.0/docs/installation-guides/install-codex.md)
- [إعدادات الخادم وأنماط القراءة فقط](https://github.com/github/github-mcp-server/blob/v2.1.0/docs/server-configuration.md)
- [توثيق MCP الرسمي في Codex](https://developers.openai.com/codex/mcp)
