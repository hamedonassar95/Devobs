# لوحة وAPI الذكاء التشغيلي المحلي — AI-7

**الحالة: أداة محلية أولية للقراءة فقط؛ ليست خدمة مستضافة أو SaaS أو دليل جاهزية إنتاجية.** تجمع مخرجات AI-1 إلى AI-7 في مسار واحد: قراءة أحداث AI-1 المطبّعة، كشف شذوذ المقاييس في AI-2، تحليل السجلات والفرضيات في AI-3، توصيات AI-4، ملخص الاتجاهات في AI-5، ترتيب اختياري بملاحظات AI-6، ثم عرض الكل في لوحة AI-7.

## التشغيل

```sh
node scripts/ai_intelligence/dashboard_server.mjs --store <local-jsonl-file> [--feedback-ledger <private-jsonl-file>] [--google-docs-client-id <public-oauth-client-id>] [--google-sheets-client-id <public-oauth-client-id>] [--google-slides-client-id <public-oauth-client-id>] [--google-chat-client-id <public-oauth-client-id>] [--google-tasks-client-id <public-oauth-client-id>] [--google-gmail-client-id <public-oauth-client-id>] [--port 8765]
```

افتح الرابط المحلي الذي يطبعه الأمر على `127.0.0.1`. لإيقاف الخادم اضغط `Ctrl+C`. يقرأ الخادم لقطة مرة واحدة عند البدء؛ أعد تشغيله بعد تحديث سجل الأحداث أو سجل التغذية الراجعة. كل تكامل Google اختياري ومنفصل؛ لا يُفعّل إلا بإضافة معرّف OAuth الخاص به. استخدم بيانات اصطناعية حتى اعتماد سياسة الخصوصية والاحتفاظ.

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

## إنشاء جدول إجمالي جديد في Google Sheets (اختياري)

هذا خيار محلي منفصل عن Docs وCalendar. فعّل Google Sheets API، وأنشئ OAuth client من نوع Web application، وأضف الأصل `http://127.0.0.1:8765` إلى JavaScript origins. لا تنشئ client secret للواجهة ولا ترسله. شغّل اللوحة مع `--google-sheets-client-id <public-oauth-client-id>`؛ يمكن استخدام OAuth client العام نفسه في أكثر من تكامل، لكن كل ميزة تبقى معطلة ما لم تضف معرّفها صراحةً.

عند الضغط على الزر وتأكيد الإرسال، ينشئ التكامل جدولًا جديدًا بعنوان يومي ويكتب فيه صفوفًا ثابتة لأعداد AI-7، أنواع الأحداث، درجاتها، وفئات استرشادية مجمعة. لا يسرد ملفات Drive، ولا يقرأ جداول سابقة، ولا يرسل نصوص سجلات أو أسماء عملاء أو معرّفات مشاريع أو خوادم. يطلب النطاق `drive.file` فقط، ويكتب القيم بخيار `RAW` حتى لا تُفسّر كنصوص كصيغ. رمز OAuth يبقى في ذاكرة الصفحة للطلب ولا يُحفظ. إذا فشل تحديث القيم بعد إنشاء الجدول، قد يبقى جدول فارغ؛ افحص Drive قبل إعادة المحاولة.

هذا التكامل محلي فقط ولا يضيف تخزينًا إلى موقع Devobs الثابت أو خدمة SaaS. اختباراته تستخدم لقطة اصطناعية وواجهة Google وهمية؛ لم يُربط حساب أو يُنشأ جدول فعلي.

مراجع Google Sheets الرسمية:

- [نطاقات OAuth في Google Sheets API](https://developers.google.com/workspace/sheets/api/scopes)
- [إنشاء جدول](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets/create)
- [تحديث قيم جدول](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/update)
- [نموذج الرموز في Google Identity Services](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

## إنشاء عرض تنفيذي إجمالي جديد في Google Slides (اختياري)

هذا تكامل محلي اختياري مستقل. فعّل Google Slides API، واستخدم OAuth client من نوع Web application، وأضف الأصل `http://127.0.0.1:8765` إلى JavaScript origins. لا تنشئ client secret للواجهة ولا ترسله. شغّل اللوحة مع `--google-slides-client-id <public-oauth-client-id>`؛ ويمكن استخدام معرّف OAuth العام نفسه لبقية التكاملات، مع تفعيل كل خيار على حدة.

بعد الضغط على الزر وتأكيدك، يطلب المتصفح موافقتك على `drive.file` ثم ينشئ عرضًا جديدًا من شريحتين: مؤشرات AI-7 الإجمالية، ثم أعداد أنواع الأحداث ودرجات الشدة. يستخدم العرض تسميات وأعدادًا ثابتة وتاريخ الإنشاء فقط؛ لا يسرد أو يقرأ عروض Drive الموجودة، ولا يرسل نصوص السجلات أو الحوادث أو أسماء العملاء أو معرّفات المشاريع والخوادم. رمز الدخول يبقى في ذاكرة الصفحة ولا يُحفظ. إذا نجح إنشاء العرض وفشل تحديث الشرائح، قد يبقى العرض فارغًا أو جزئيًا؛ راجع Drive قبل إعادة المحاولة.

هذا التصدير لا يضيف تخزينًا لموقع Devobs الثابت أو خدمة SaaS، ولا يثبت OAuth أو صلاحية حساب حقيقي. الاختبارات تستخدم لقطة وطلبات Google اصطناعية فقط.

مراجع Google Slides الرسمية:

- [نطاقات OAuth في Google Slides API](https://developers.google.com/workspace/slides/api/scopes)
- [إنشاء عرض تقديمي](https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/create)
- [تطبيق تحديثات العرض دفعة واحدة](https://developers.google.com/workspace/slides/api/reference/rest/v1/presentations/batchUpdate)
- [نموذج الرموز في Google Identity Services](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

## إرسال موجز مجمّع إلى Google Chat (اختياري)

هذا خيار محلي معطّل افتراضيًا. فعّل Google Chat API، وأنشئ OAuth client من نوع Web application، وأضف `http://127.0.0.1:8765` إلى JavaScript origins. شغّل اللوحة مع `--google-chat-client-id <public-oauth-client-id>`. لا تنشئ client secret للواجهة ولا ترسله. تطلب الميزة نطاق المستخدم `https://www.googleapis.com/auth/chat.messages.create` فقط بعد معاينة النص وتأكيد الإرسال.

أدخل اسم مورد مساحة موجودة بصيغة `spaces/{space}` بنفسك. لا تسرد اللوحة المساحات ولا تقرأ الرسائل. بعد التأكيد وإتاحة رمز OAuth بالنطاق المطلوب، ترسل رسالة نصية واحدة إلى تلك المساحة؛ يراها أعضاؤها وتظهر باسم حساب Google الذي وافق. الرسالة مبنية من تسميات وأعداد AI-7 المجمّعة ووقت الإنشاء فقط، ولا تحتوي نصوص سجلات أو حوادث أو أسماء عملاء أو معرفات مصادر. لا تُرسل الرسالة قبل تأكيد المتصفح، ولا تعيد الصفحة المحاولة تلقائيًا. إذا كانت النتيجة غير مؤكدة، افحص مساحة Chat قبل أي إرسال جديد لاحتمال وصول الرسالة.

هذا تكامل محلي اختياري وليس موصلًا حيًا أو خدمة مستضافة. الاختبارات تستخدم مساحة ورسالة ورمزًا اصطناعيًا وطلبات HTTP وهمية؛ لم نسجل الدخول أو نرسل إلى مساحة حقيقية. تفعيل OAuth يتطلب إعداد Google Workspace/Chat مناسبًا، ولا تثبت الاختبارات صلاحيات حسابك أو إعداد المؤسسة.

مراجع Google Chat الرسمية:

- [إنشاء الرسائل](https://developers.google.com/workspace/chat/create-messages)
- [مرجع إنشاء رسالة في مساحة](https://developers.google.com/workspace/chat/api/reference/rest/v1/spaces.messages/create)
- [مصادقة المستخدم وتفويضه في Google Chat](https://developers.google.com/workspace/chat/authenticate-authorize-chat-user)
- [نموذج الرموز في Google Identity Services](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

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

## إنشاء مهمة متابعة واحدة في Google Tasks (اختياري)

الميزة محلية ومعطّلة افتراضيًا. فعّل Google Tasks API، وسجّل `http://127.0.0.1:8765` كـJavaScript origin في OAuth client من نوع Web application، ثم شغّل اللوحة مع `--google-tasks-client-id <public-oauth-client-id>`. لا تنشئ client secret للواجهة ولا ترسله. قبل أي اتصال، تعرض اللوحة عنوان المهمة وملاحظاتها وتاريخ استحقاقها وتطلب تأكيدك.

بعد التأكيد، تنشئ اللوحة مهمة واحدة بعنوان ثابت في قائمة Google Tasks الافتراضية، مع أعداد AI-7 المسموحة وتاريخ تختاره. لا تسرد القوائم ولا تقرأ أو تعدّل أو تحذف أي مهمة. نطاق Google `https://www.googleapis.com/auth/tasks` يسمح بإدارة المهام عمومًا؛ الكود هنا يستخدمه لطلب `tasks.insert` واحد فقط. رمز الوصول يبقى في ذاكرة الصفحة. إذا لم تتأكد من نتيجة الطلب، افحص Google Tasks قبل إعادة المحاولة لاحتمال إنشاء المهمة.

هذا تكامل محلي غير موصول بحساب Google ولا يثبت جاهزية SaaS. الاختبارات تستخدم بيانات اصطناعية واستجابة وهمية؛ لم ننشئ مهمة فعلية.

مراجع Google Tasks الرسمية:

- [Google Tasks API: إدراج مهمة](https://developers.google.com/tasks/reference/rest/v1/tasks/insert)
- [نطاقات OAuth في Google Tasks](https://developers.google.com/identity/protocols/oauth2/scopes#tasks)
- [Google Identity Services: نموذج الرموز](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

## إرسال موجز واحد عبر Gmail (اختياري)

هذا الخيار المحلي معطّل افتراضيًا. فعّل Gmail API، وسجّل `http://127.0.0.1:8765` كـJavaScript origin في OAuth client من نوع Web application، ثم شغّل اللوحة مع `--google-gmail-client-id <public-oauth-client-id>`. لا تنشئ client secret للواجهة ولا ترسله. لا يُطلب نطاق `https://www.googleapis.com/auth/gmail.send` إلا بعد معاينة الرسالة وتأكيد الإرسال.

أدخل عنوانًا واحدًا وراجع المعاينة قبل الإرسال. ينشئ Devobs رسالة نصية ثابتة من أعداد AI-7 والفئات العامة فقط. لا يقرأ الرسائل أو المرفقات، ولا يرسل سجلات أو أسماء عملاء أو معرّفات مشاريع وخوادم. Gmail يرسلها من حساب Google الذي توافق عليه؛ يُسمح بمحاولة إرسال واحدة في الصفحة الحالية. إذا انقطع الاتصال أو لم تصل استجابة واضحة، افحص مجلد الرسائل المرسلة قبل إعادة تحميل اللوحة والمحاولة مرة ثانية.

الميزة اختيارية ومحلية، ولم تُضبط لها بيانات OAuth ولم تُرسل رسالة فعلية. الاختبارات تستخدم استجابة Gmail وهمية.

مراجع Google الرسمية:

- [Gmail API: إرسال البريد](https://developers.google.com/workspace/gmail/api/guides/sending)
- [Gmail `users.messages.send`](https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send)
- [نطاقات Gmail API OAuth](https://developers.google.com/workspace/gmail/api/auth/scopes)
- [Google Identity Services: نموذج الرموز](https://developers.google.com/identity/oauth2/web/guides/use-token-model)

## التقييم الاصطناعي والفحوص

**VERIFIED في اختبار هذه النسخة:** يحتوي اختبار التغطية ست حالات اصطناعية لقواعد AI-3 (timeout، اتصال، DNS، صلاحية، اعتماد، ذاكرة)، ومطابقة 6/6 للفئة المحددة. هذه **مطابقة لمجموعة قواعد صغيرة أنشأها المطور**، وليست دقة تنبؤية أو تقييمًا على حوادث حقيقية.

```sh
node --check scripts/ai_intelligence/dashboard_server.mjs
node --check scripts/ai_intelligence/dashboard_assets/dashboard.js
node --check scripts/ai_intelligence/dashboard_assets/google_docs_export.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_calendar_followup.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_sheets_export.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_slides_export.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_chat_export.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_tasks_followup.mjs
node --check scripts/ai_intelligence/dashboard_assets/google_gmail_summary.mjs
node --check tests/ai_dashboard_api.test.mjs
node --check tests/google_calendar_followup.test.mjs
node --check tests/google_sheets_export.test.mjs
node --check tests/google_slides_export.test.mjs
node --check tests/google_chat_export.test.mjs
node --check tests/google_tasks_followup.test.mjs
node --check tests/google_gmail_summary.test.mjs
node --test tests/ai_dashboard_api.test.mjs tests/google_docs_export.test.mjs tests/google_chat_export.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_trend_forecast.test.mjs
node --test tests/google_calendar_followup.test.mjs
node --test tests/google_sheets_export.test.mjs
node --test tests/google_slides_export.test.mjs
node --test tests/google_tasks_followup.test.mjs
node --test tests/google_gmail_summary.test.mjs
```

الخادم يستخدم مكتبة [Node.js HTTP](https://nodejs.org/api/http.html) وواجهة [URL](https://nodejs.org/api/url.html) المدمجتين؛ الاختبارات تستخدم [Node.js Test Runner](https://nodejs.org/api/test.html) وHTTP محليًا على loopback فقط. لا تثبت هذه الفحوص أمان خدمة عامة أو جاهزية نشر.
