# لوحة وAPI الذكاء التشغيلي المحلي — AI-7

**الحالة: أداة محلية أولية للقراءة فقط؛ ليست خدمة مستضافة أو SaaS أو دليل جاهزية إنتاجية.** تجمع مخرجات AI-1 إلى AI-7 في مسار واحد: قراءة أحداث AI-1 المطبّعة، كشف شذوذ المقاييس في AI-2، تحليل السجلات والفرضيات في AI-3، توصيات AI-4، ملخص الاتجاهات في AI-5، ترتيب اختياري بملاحظات AI-6، ثم عرض الكل في لوحة AI-7.

## التشغيل

```sh
node scripts/ai_intelligence/dashboard_server.mjs --store <local-jsonl-file> [--feedback-ledger <private-jsonl-file>] [--google-docs-client-id <public-oauth-client-id>] [--port 8765]
```

افتح الرابط المحلي الذي يطبعه الأمر على `127.0.0.1`. لإيقاف الخادم اضغط `Ctrl+C`. يقرأ الخادم لقطة مرة واحدة عند البدء؛ أعد تشغيله بعد تحديث سجل الأحداث أو سجل التغذية الراجعة. من دون `--google-docs-client-id` لا تحاول اللوحة الاتصال بخدمة خارجية. استخدم بيانات اصطناعية حتى اعتماد سياسة الخصوصية والاحتفاظ.

## الواجهة والحدود الأمنية

- واجهة AI-7 تستخدم مسارًا موحدًا للقراءة فقط: `/api/v1/intelligence` ويعيد حالة المراحل السبع والملخصات والنتائج المحدودة لـAI-2 وAI-3 وAI-4 وAI-5 وAI-6. تبقى المسارات `/api/v1/summary` و`/api/v1/incidents` (تجميعات سجلات لا حوادث مؤكدة) و`/api/v1/recommendations` للتوافق. كل المسارات تقبل `GET` و`HEAD` فقط؛ لا يوجد API لإرسال قرار أو تنفيذ توصية.
- يرتبط الخادم بـIPv4 loopback `127.0.0.1`، ويتحقق من `Host` و`Origin`، ولا يرسل CORS، ويضيف CSP و`no-store`. لا توجد مصادقة منفصلة؛ لا تستخدمه عبر نفق أو على شبكة مشتركة، ولا تعرضه لمستخدمين غير موثوقين على الجهاز.
- الخادم يعيد حقولًا محددة: أعداد مجمعة، أسماء مقاييس من قائمة ثابتة، قيمًا وعتبات إحصائية، وفئات أسباب معروفة، وإشارات `low`/`medium` heuristic وفحوص runbook. لا يعيد نصوص السجلات أو أوقات الأحداث أو event IDs أو بصمات التجميع أو SHA أو مسارات الملفات.
- AI-2 يستخدم قواعد Z-score والمتوسط المتحرك وEWMA، وAI-5 يعرض استقراء يوم واحد بالانحدار الخطي والتمهيد الأسي. هذه خوارزميات محلية حتمية، لا استدلال نموذج لغوي. التكامل هو تنسيق للمراحل الموجودة في تقرير واحد، وليس نموذجًا مدرّبًا واحدًا.
- إشارات `low` و`medium` ليست احتمالات معايرة. إشارة القبول من AI-6 تفضيل محلي مستقل، ولا تثبت صحة السبب. التوصيات `POSSIBLE` وتحتاج اعتمادًا بشريًا؛ التنفيذ التلقائي متوقف.
- جميع المراحل تعمل على لقطة عند بدء الخادم؛ أعد تشغيله بعد تحديث السجل أو الملاحظات. التحليل لا يثبت صحة مصدر الأحداث أو سبب العطل، ولا توجد موصلات حيّة.
- **VERIFIED من المصدر:** أصول اللوحة محفوظة تحت `scripts/ai_intelligence/` وخارج نشر الموقع؛ ينسخ `scripts/stage_site.py` ملف `index.html` وجذر `assets/` فقط.

## إنشاء تقرير جديد في Google Docs (اختياري)

الميزة محلية واختيارية، ولا تعمل إلا إذا شُغّلت اللوحة مع OAuth Client ID عام. أنشئ OAuth client من نوع Web application في Google Cloud، وفعّل Google Docs API، وأضف الأصل `http://127.0.0.1:8765` إلى JavaScript origins المسموحة. لا تنشئ client secret للواجهة ولا ترسله للمحادثة. شغّل اللوحة مع `--google-docs-client-id <client-id>`؛ معرّف العميل ليس كلمة مرور.

عند الضغط على زر الحفظ، تعرض اللوحة تأكيدًا، ثم تطلب موافقتك من Google على نطاق `drive.file`. تنشئ مستندًا جديدًا وتكتب فيه أعداد الأحداث وفئات عامة وتاريخ الإنشاء. لا تقرأ ملفات Drive الموجودة ولا ترسل نصوص السجلات أو أسماء العملاء أو معرّفات المشاريع والخوادم. رمز الوصول يبقى في ذاكرة الصفحة للطلب الحالي ولا يُحفظ في `localStorage` أو ملفات Devops. إذا نجح إنشاء المستند وفشلت الكتابة، قد يبقى مستند فارغ في Drive؛ افحص Drive قبل إعادة المحاولة.

هذا التكامل يخص لوحة AI-7 المحلية فقط؛ لا يضيف حفظًا إلى موقع Devobs الثابت أو خدمة SaaS مستضافة. اختبارات المستودع تستخدم تقريرًا اصطناعيًا وطلبات Google وهمية، ولا تسجّل الدخول أو تتصل بحساب Google.

## جدولة مراجعة متابعة في Google Calendar (اختياري)

الميزة معطلة افتراضيًا. لتجربتها محليًا، أضف معرّف OAuth العام للويب:

```sh
node scripts/ai_intelligence/dashboard_server.mjs --store <local-jsonl-file> --google-calendar-client-id <public-oauth-client-id>
```

سجّل `http://127.0.0.1:8765` كأصل JavaScript مسموح، وفعّل Google Calendar API وجهّز شاشة موافقة OAuth. معرّف العميل العام ليس سرًا؛ لا تنشئ client secret للواجهة ولا ترسله. لا تطلب اللوحة صلاحية `calendar.app.created` إلا بعد اختيار موعد مستقبلي وتأكيده. تتيح هذه الصلاحية إنشاء تقاويم ثانوية خاصة بالتطبيق وإدارة أحداث تلك التقاويم. ينشئ التكامل تقويمًا واحدًا باسم `Devobs AI-7 Follow-ups`، ثم موعدًا ثابت العنوان مدته 30 دقيقة. لا يضيف مدعوين أو رابط Meet أو سجلات أو تفاصيل حادثة أو أسماء عملاء؛ الوقت الذي تختاره هو البيانات الوحيدة التي يرسلها إلى Google.

رمز الوصول يبقى في ذاكرة الصفحة للطلب ولا يُحفظ في ملفات أو تخزين المتصفح. يُحفظ معرّف التقويم الذي أنشأه التطبيق فقط في `localStorage` على هذا المتصفح لتجنب إنشاء تقويم جديد كل مرة؛ المعرّف ليس رمز دخول. إذا بدّلت حساب Google ولم يعد التقويم متاحًا، يمسح التكامل المعرّف المحلي ويطلب منك إعادة المحاولة لإنشاء تقويم للحساب الحالي. يُشتق معرّف الموعد محليًا من توقيته لتسهيل إعادة المحاولة؛ وإذا أعاد Google تعارضًا، يتحقق التكامل من الحدث الموجود قبل اعتباره الموعد نفسه. لا يضمن Google اكتشاف كل تصادم محتمل للمعرّفات. إذا نجح إنشاء التقويم وفشل إنشاء الموعد، قد يبقى التقويم فارغًا؛ راجعه قبل إعادة المحاولة. لم نربط حساب Google ولم ننشئ تقويمًا حقيقيًا. نجاح الاختبارات المحلية لا يثبت اتصال OAuth أو التشغيل الفعلي.

مراجع Google Calendar الرسمية:

- [نطاقات Google Calendar API](https://developers.google.com/workspace/calendar/api/auth)
- [قراءة تقويم محدد](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/get)
- [إنشاء تقويم ثانوي](https://developers.google.com/workspace/calendar/api/v3/reference/calendars/insert)
- [قراءة حدث محدد للتحقق من إعادة المحاولة](https://developers.google.com/workspace/calendar/api/v3/reference/events/get)
- [إنشاء حدث في التقويم](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert)
- [نموذج الرموز في Google Identity Services](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

مراجع Google Docs الرسمية:

- [Google Docs API authorization scopes](https://developers.google.com/workspace/docs/api/auth)
- [Create a document](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/create)
- [Batch update a document](https://developers.google.com/workspace/docs/api/reference/rest/v1/documents/batchUpdate)

## التقييم الاصطناعي والفحوص

**VERIFIED في اختبار هذه النسخة:** يحتوي اختبار التغطية ست حالات اصطناعية لقواعد AI-3 (timeout، اتصال، DNS، صلاحية، اعتماد، ذاكرة)، ومطابقة 6/6 للفئة المحددة. هذه **مطابقة لمجموعة قواعد صغيرة أنشأها المطور**، وليست دقة تنبؤية أو تقييمًا على حوادث حقيقية.

```sh
node --check scripts/ai_intelligence/dashboard_server.mjs
node --check scripts/ai_intelligence/dashboard_assets/dashboard.js
node --check scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_calendar_followup.mjs
node --check tests/ai_dashboard_api.test.mjs
node --check tests/google_calendar_followup.test.mjs
node --test tests/ai_dashboard_api.test.mjs tests/google_docs_export.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_trend_forecast.test.mjs
node --test tests/google_calendar_followup.test.mjs
```

الخادم يستخدم مكتبة [Node.js HTTP](https://nodejs.org/api/http.html) وواجهة [URL](https://nodejs.org/api/url.html) المدمجتين؛ الاختبارات تستخدم [Node.js Test Runner](https://nodejs.org/api/test.html) وHTTP محليًا على loopback فقط. لا تثبت هذه الفحوص أمان خدمة عامة أو جاهزية نشر.
