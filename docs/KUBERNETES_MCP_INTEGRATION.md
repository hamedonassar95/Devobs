# تكامل Kubernetes MCP المحلي والاختياري

## ماذا يضيف

يربط خادم Kubernetes MCP الرسمي Codex بأحداث Kubernetes في namespace تطوير واحد. أحداث Kubernetes قد تعرض أسبابًا مثل تعذّر جدولة Pod أو فشل سحب صورة؛ وهذا يكمل قراءة المقاييس من Grafana MCP. الإعداد محلي للمطور، ولا يدخل في `.codex/config.toml` أو CI أو مكدس Devobs أو أي نشر.

اخترت خادم [`containers/kubernetes-mcp-server`](https://github.com/containers/kubernetes-mcp-server) لأنه Apache-2.0 ويدعم إعدادًا مقيّدًا للقراءة. الإصدار المثبت `v0.1.2`، مصدره `66553fed5c16454e5814b41e331b4357f15806d8`. أصل Windows x64 الرسمي هو [`kubernetes-mcp-server-windows-amd64.exe`](https://github.com/containers/kubernetes-mcp-server/releases/download/v0.1.2/kubernetes-mcp-server-windows-amd64.exe)، وبصمته المنشورة في GitHub Releases هي `2ed4b885f2b94ea8664bed028993370a0abda65fa72863ff4456a4c5b5cc4053`.

راجعت أيضًا Sentry Toolkit الرسمي عند المصدر `afad2c8a41a3c7258f46c7a968acbc5d2221cfeb`. رخصة [FSL-1.1-Apache-2.0](https://github.com/getsentry/toolkit/blob/afad2c8a41a3c7258f46c7a968acbc5d2221cfeb/LICENSE.md) فيه تذكر أن Apache-2.0 تبدأ بعد سنتين، وتعرّف الاستخدام المنافس كاستثناء من المنح الحالي. لذلك لم أختره كاعتماد لخدمة Devobs التجارية قبل مراجعة قانونية مخصصة. لم أنقل منه كودًا.

## قيود الوصول المضافة

- مثال خادم MCP يسمح بأداة `events_list` فقط ويضبط `read_only = true` وحدّ استجابة API إلى 256 KiB.
- مثال Codex يسمح للأداة نفسها فقط ويطلب موافقة عند كل استدعاء. هذا مرشح على جهة العميل وليس حدًا أمنيًا مستقلًا.
- المثال [`kubernetes-events-reader-rbac.yaml`](../.codex/examples/kubernetes-events-reader-rbac.yaml) ينشئ ServiceAccount وRole وRoleBinding في namespace واحد. يسمح الـRole بعملية `list` على `events` فقط؛ Kubernetes RBAC هو الحاجز الفعلي.
- لا تُمنح صلاحيات لقراءة Pods أو ConfigMaps أو Secrets أو سجلات الحاويات، ولا لأي إنشاء أو تعديل أو حذف أو تنفيذ أوامر.
- الحدّ على حجم الاستجابة يقلل البيانات المعادة لكنه لا يثبت خلو نص الحدث من معلومات داخلية. لا تستخدمه مع namespace إنتاج أو بيانات عميل؛ وراجع ما سيصل إلى نموذج Codex قبل الاستدعاء.

إعدادات MCP وإخفاء الأدوات وحدود الحجم ضوابط مساعدة. هوية Kubernetes وصلاحيات RBAC هي التي تقرر ما يمكن قراءته. لا تستخدم kubeconfig بصلاحيات `cluster-admin` أو kubeconfig عملاء.

## إعداد اختياري على Windows

1. نزّل الملف الرسمي المثبت من صفحة [إصدار v0.1.2](https://github.com/containers/kubernetes-mcp-server/releases/tag/v0.1.2)، وضعه خارج المستودع في:

   ```text
   %LOCALAPPDATA%\Devobs\kubernetes-mcp-server\v0.1.2\kubernetes-mcp-server-windows-amd64.exe
   ```

2. تحقّق من البصمة قبل التشغيل:

   ```powershell
   Get-FileHash "$env:LOCALAPPDATA\Devobs\kubernetes-mcp-server\v0.1.2\kubernetes-mcp-server-windows-amd64.exe" -Algorithm SHA256
   ```

   يجب أن تطابق القيمة المذكورة أعلاه. إذا لم تطابق، لا تشغّل الملف.

3. يختار مسؤول العنقود namespace تطويرًا غير إنتاجي، ويراجع ويطبق ملف RBAC الاختياري بعد استبدال `devobs-development` باسم ذلك الـnamespace. يجب أن يصدر لك هوية أو kubeconfig مخصصة مرتبطة بهذا الدور فقط، عبر طريقة المصادقة المعتمدة عندكم. لا تستخدم حساب المسؤول الحالي لمجرد أن الوصول أسرع.

4. احفظ kubeconfig المخصص خارج المستودع مثل:

   ```text
   %LOCALAPPDATA%\Devobs\kubernetes-events-reader.kubeconfig
   ```

   احصر قراءة الملف بحساب Windows المستخدم. لا ترسله إلى Git أو المحادثة، ولا تضعه في ملفات الأمثلة. تدوير بيانات الاعتماد وإبطالها من مسؤول العنقود عند الإيقاف.

5. انسخ `.codex/examples/kubernetes-events-server-readonly.toml` إلى `%USERPROFILE%\.codex\kubernetes-mcp-server-readonly.toml`، وعدّل اسم المستخدم والـnamespace ومسار kubeconfig. انسخ كتلة `mcp_servers.kubernetes_events` من `.codex/examples/kubernetes-events-readonly.toml` إلى `%USERPROFILE%\.codex\config.toml` دون استبدال بقية الإعدادات. غيّر مسار البرنامج إذا لزم.

6. افتح Codex وأكّد ظهور `kubernetes_events`. عند الاستدعاء مرّر namespace المصرح به و`limit` لا يتجاوز 100، وابدأ بطلب قراءة أحداث التطوير الأخيرة. إذا طلبت أداة أخرى أو ظهر رفض RBAC، أوقف المحاولة وراجع إعدادات الهوية والنطاق.

7. للإيقاف، احذف جدول الخادم من إعداد Codex الشخصي، ثم اطلب من مسؤول العنقود إزالة RoleBinding أو تعطيل الهوية. احذف kubeconfig المحلي بعد إبطال الاعتماد.

## حالة التحقق والمصادر

- تحققت من وسم upstream `v0.1.2` وبصمة المصدر، ومن بصمة Windows الرسمية؛ لم أشغّل ملف Windows في بيئة CI.
- **UNVERIFIED:** لم أتصل بعنقود Kubernetes، ولم أطبق RBAC، أو أستخدم kubeconfig أو بيانات اعتماد، أو أبدأ خادم MCP حيًا. الأمثلة لا تفعّل تكاملًا تلقائيًا.
- قبول Codex runtime يبقى **OPEN**؛ AI-9 وP01 يبقيان **BLOCKED**.

المصادر الرسمية المثبتة:

- [Kubernetes MCP Server v0.1.2](https://github.com/containers/kubernetes-mcp-server/tree/v0.1.2)
- [مرجع الإعداد v0.1.2](https://github.com/containers/kubernetes-mcp-server/blob/v0.1.2/docs/configuration.md)
- [دليل أدوات Kubernetes وMCP v0.1.2](https://github.com/containers/kubernetes-mcp-server/blob/v0.1.2/README.md)
- [الرخصة Apache-2.0](https://github.com/containers/kubernetes-mcp-server/blob/v0.1.2/LICENSE)
- [Kubernetes RBAC](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) و[Service Accounts](https://kubernetes.io/docs/concepts/security/service-accounts/)
- [Codex MCP configuration](https://developers.openai.com/codex/mcp)
- [Sentry Toolkit license at the reviewed commit](https://github.com/getsentry/toolkit/blob/afad2c8a41a3c7258f46c7a968acbc5d2221cfeb/LICENSE.md)
