# تفعيل AI Scan لطلبات السحب

**تاريخ المراجعة:** 16 أكتوبر 2026

**الإعلان:** [أصبح AI Scan لطلبات السحب متاحًا للجميع](https://github.blog/changelog/2026-10-15-ai-scan-for-pull-requests-generally-available/)

**مرجع GitHub:** [AI-powered security detections](https://docs.github.com/en/enterprise-cloud@latest/code-security/concepts/code-scanning/ai-powered-security-detections)

## حالة Devobs

أظهر فحص طلب السحب التجريبي أن GitHub يشغّل CodeQL الافتراضي للمستودع على Python وJavaScript/TypeScript وActions. لذلك لم أضف سير عمل CodeQL مكررًا. خيار AI Scan نفسه لا يُفعّل بملف YAML أو Action؛ هو إعداد مستقل للمستودع في GitHub.

## تفعيل AI Scan على GitHub

بعد التأكد من إعداد ميزانية أرصدة AI للحساب الذي يتحمل الفاتورة:

1. افتح مستودع [Devobs](https://github.com/hamedonassar95/Devobs).
2. اذهب إلى **Settings → Code security and analysis**.
3. ضمن إعدادات **Code scanning**، فعّل **AI Scan on pull requests** للمستودع فقط.
4. تحقق من أن Code scanning مفعّل وأن أول طلب سحب مؤهل يعرض نتائج AI Scan.

صلاحية AI Scan متاحة للمستودعات العامة المملوكة لحساب شخصي. يُفوتر الاستخدام ضمن **Code Security AI Credits** للحساب المرتبط، وتُستهلك الأرصدة المشمولة أولًا ثم قد يبدأ الاستخدام المدفوع بحسب الميزانيات. لا يوجد تقدير ثابت مسبق للتكلفة؛ ابدأ بميزانية صلبة وحدّ الاستخدام قبل التفعيل. لم أفعّل خيارًا قد يولّد رسومًا من جهة إعدادات GitHub.

## حدود الميزة

- تفحص طلبات السحب المؤهلة عند إنشائها ومع كل commit جديد، وتغطي لغات وأطرًا لا يغطيها CodeQL.
- لا تفحص طلبات السحب الآتية من fork أو التي ينشئها Dependabot.
- تظهر النتائج في صفحة طلب السحب، وتبقى استشارية: لا تفشل فحص Code scanning ولا تمنع الدمج عبر قواعد الحماية.
- لا تحتاج إلى Copilot أو CodeQL default setup، لكن يلزم تفعيل Code scanning وخيار AI Scan على المستودع.

## القياس بعد التفعيل

سجّل لكل فترة مراجعة: عدد طلبات السحب المؤهلة، عدد نتائج AI، النتائج المؤكدة بعد المراجعة، النتائج المرفوضة، وقيمة **Code Security AI Credits** في صفحة الفوترة. راجع كل نتيجة يدويًا؛ لا تجعل AI Scan شرط دمج أو دليلًا وحيدًا على سلامة التغيير.
