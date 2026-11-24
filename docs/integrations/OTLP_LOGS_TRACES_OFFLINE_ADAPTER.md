# محول سجلات وعمليات OTLP محلي لـDevobs

**الحالة: محول ملفات محلي اختياري؛ ليس مستقبل OTLP أو تكاملًا حيًا أو دليل جاهزية إنتاج.** يحوّل جزءًا محدودًا من OTLP/JSON Logs وTraces إلى عقد SafeSignal الموجود في Devobs. لا يفتح منفذ شبكة، ولا يبدأ Collector، ولا يتصل بمزود، ولا يكتب إلى مخزن AI-1 أو Firebase أو قاعدة بيانات.

## لماذا هذا النطاق

تصف مواصفة OpenTelemetry OTLP 1.11.1 إشارات traces وlogs بأنها مستقرة. وتحتوي بياناتهما حقولًا قد تكون حرة أو حساسة، لذلك لا يعتبر هذا المحول كاملًا أو آمنًا تلقائيًا لكل بيانات OTLP. [مواصفة OTLP](https://opentelemetry.io/docs/specs/otlp/)، [نموذج traces](https://opentelemetry.io/docs/specs/otel/trace/data-model/) و[نموذج logs](https://opentelemetry.io/docs/specs/otel/logs/data-model/) تشرح بنية البيانات؛ ويحدد [W3C Trace Context](https://www.w3.org/TR/trace-context/) رفض معرفات التتبع ذات القيم الصفرية. وتحذر [إرشادات OpenTelemetry للبيانات الحساسة](https://opentelemetry.io/docs/security/handling-sensitive-data/) من أن الأداة لا تعرف حساسية بيانات المؤسسة نيابة عنها.

المحول يعالج **ملف JSON محليًا أو stdin فقط**، ويرفض كامل الدفعة إذا وجد حقلًا أو قيمة خارج العقد الضيق. يقبل كل ملف سجلات أو traces فقط؛ لا يشغّل التصفية على Collector حي ولا يدّعي تنقيح بيانات اعتباطية.

## العقد المقبول

- جذر OTLP/JSON يحتوي `resourceLogs` فقط، من 1 إلى 32 سجلًا بعد التسطيح، بحد أقصى 1 MiB.
- لكل مجموعة مورد `resource.attributes` واحد فقط: `service.name`، بقيمة OTLP `stringValue` مطابقة لمعرف آمن.
- يقبل المحول `scope` فارغًا فقط، ومجموعة `logRecords` غير فارغة.
- لكل سجل `attributes` بالضبط: `devobs.operation` و`devobs.status` بقيمتي `stringValue`. هذان الحقلان **مفردات Devobs خاصة** وليسا اصطلاحين دلاليين رسميين من OpenTelemetry.
- يقبل `timeUnixNano` أو `observedTimeUnixNano`؛ يفضّل وقت الحدث عند كونه غير صفري، وإلا يستخدم وقت الرصد، وفق توصية نموذج السجلات عند تحويل سجل ذي حقل وقت واحد. يقبل تمثيل رقم 64 بت كسلسلة عشرية أو عدد JSON صحيح؛ ويرفض الأعداد العشرية والقيم خارج النطاق.
- يرفض `body` و`severity*` و`eventName` وخصائص السجلات الإضافية و`schemaUrl` وأي حقول غير معلنة. لا يقرأها لإنتاج المخرجات.
- يمرر القيم المطبّعة إلى `from_trusted_safe_signals`؛ لذلك تُطبق مفردات العملية/الحالة، هوية الخدمة، SHA المصدر، حدود الوقت والتكرار الموجودة أصلًا.

### Traces

- يقبل جذر `resourceSpans` فقط، مع مورد `service.name` ومجموعة `scopeSpans` ذات `scope` فارغ.
- يقبل span بالحقول المطلوبة `traceId` و`spanId` و`name` و`startTimeUnixNano` و`endTimeUnixNano`، وبحد أقصى `parentSpanId` و`kind` و`status` الاختيارية. يتحقق من أن معرفات trace/span سداسية عشرية وغير صفرية، ثم يهملها؛ لا تظهر في المخرجات.
- لا يقبل `attributes` أو `events` أو `links` أو حقولًا نصية حرة. يقبل حالة رقمية فقط: `Unset` تصبح `unknown`، و`Ok` تصبح `ok`، و`Error` تصبح `error`. لا يقبل رسالة الحالة.
- يحسب المدة من وقتي البداية والنهاية، ثم يطبق حد SafeSignal البالغ 10 دقائق. يعرض وقت نهاية span كوقت الرصد.

`tenant` و`project` و`source-sha` يدخلها المشغل يدويًا. لا يصادق المحول عليها ولا يثبت مصدر الملف أو مالكه؛ البصمة ليست توقيعًا. استخدم بيانات اصطناعية محلية إلى أن توجد هوية/ملكية موثوقة وعقد تدفق معتمد. المخرجات JSONL محدودة من SafeSignal، ولا تحتوي جسم السجل أو خصائصه الخام. لا يحفظ البرنامج الناتج ولا يرسله إلى AI-1 تلقائيًا.

### ربط نطاق الطلب بمكونات الهوية الموجودة

يوفر `ScopedOtlpConverter` وصلة **داخل العملية فقط** لمن يستضيفها محليًا: يأخذ مدققًا يطبق واجهة `verify(token)` ويعيد `AuthenticatedPrincipal`، ثم يستخدم `OfflineTenantGate` الحالي لفحص صلاحية `devobs.read` وعضوية المستأجر والمشروع. يُشتق `source_sha` من `ProjectSnapshot` المصرح به بدل تمريره من الطلب. كما يتطلب سجل topology موقّعًا لكل نطاق tenant/project، ويمرره إلى `verify_topology_attestation` الموجود في Devobs مع SHA المشروع والوقت الحالي؛ لا تُقبل أسماء الخدمات التي لا تظهر في اللقطة الموقعة. هذا يعيد استخدام تحقق Ed25519 الحالي ولا ينشئ نوع توقيع أو مفاتيح جديدة. مواصفة [RFC 9068](https://www.rfc-editor.org/rfc/rfc9068.html) تتطلب من مدقق access token التحقق من التوقيع وissuer وaudience والانتهاء؛ استخدم مدقق `AccessTokenVerifier` الموجود بإعداد JWKS عام مثبت من مصدر مشغل موثوق، ولا تجلب JWKS من عنوان يقدمه الطلب.

هذا اختبار/وصلة مصدرية فقط: لا ينشئ OIDC أو endpoint، وعضويات ولقطات `OfflineTenantGate` ومظاريف topology تبقى إعدادًا محليًا داخل الذاكرة. مدقق حقيقي غير مضبوط أو مفتاح topology غير موثوق يبطلان افتراض الثقة. يعرّف معيار OpenTelemetry الرسمي `service.name` بوصفه الاسم المنطقي للخدمة، لا هوية مصادَقًا عليها؛ لذلك ربطه بلقطة topology يمنع إسناد الإشارة إلى اسم غير مدرج، لكنه **لا يثبت أن مرسل OTLP هو تلك الخدمة** ولا يمنع مستخدمًا مصرحًا له من رفع بيانات مصطنعة باسم خدمة مدرجة. لا يوجد تحقق من توقيع ملف OTLP أو workload provenance. اختبارات الوصلة تستخدم verifier اصطناعيًا ونتيجة تحقق ممثلة فقط، بلا مفاتيح خاصة أو رموز صالحة؛ فحص التوقيع يبقى مسؤولية `verify_topology_attestation` واختباراته الحالية، ولا تتصل هذه الوصلة بمزود هوية حي.

## التشغيل المحلي

مسار CLI المحلي يتطلب Python الموجود في المشروع فقط؛ لا حزم جديدة أو خدمات أو مفاتيح. وصلة `ScopedOtlpConverter` لا تعمل دون مظاريف topology موقعة ومفاتيح عامة موثوقة مُعدة مسبقًا؛ لا تنشئ مفاتيح أو أسرارًا.

```sh
python3 scripts/integrations/otlp_logs_traces_adapter.py \
  --input ./synthetic-otlp.json \
  --tenant demo --project local \
  --source-sha <40-or-64-character-hex-sha>
```

استخدم `--input -` لقراءة JSON من stdin. يطبع النجاح فقط سجلات SafeSignal المنقحة إلى stdout. يفشل الملف غير المتاح أو غير المنتظم، ويطبع الخطأ رمزًا ثابتًا إلى stderr دون إظهار المسار أو القيم. لا تمرر سجلات عملاء أو إنتاج أو أسرار إلى هذا المسار المحلي.

الاختبارات الاصطناعية:

```sh
python3 -m unittest tests.test_otlp_logs_traces_adapter -v
python3 -m unittest tests.test_otlp_authenticated_scope -v
python3 -m compileall -q scripts/integrations/otlp_logs_traces_adapter.py tests/test_otlp_logs_traces_adapter.py tests/test_otlp_authenticated_scope.py
```

## ما لا يفعله وما الخطوة التالية

لا يوجد OTLP endpoint أو Collector جديد، ولا إعداد أو صلاحية أو نشر، ولا نموذج ذكاء اصطناعي، ولا إدخال آلي إلى AI-1. لا يغير هذا العمل سياسة Collector الحالية التي تقتصر على المقاييس المحلية. قبل ربط SafeSignal بذاكرة AI-1 أو AI-7 يجب تصميم تمثيل يحتفظ بحدود tenant/project/SHA؛ مخطط أحداث AI-1 الحالي لا يحمل هذه الحقول، لذلك لا يجوز إسقاط نطاق المستأجر بصمت.

هذا التحويل لا يغيّر حالة P02/T18 أو AI-9 أو P01: تبقى P02/T18 **BLOCKED** للاستخدام الحي، وAI-9 **BLOCKED**، وP01 **NO-GO / BLOCKED**. أي مستقبل شبكي أو Collector أو تخزين متعدد المستأجرين يحتاج مراجعة مستقلة للمصادقة والخصوصية والاحتفاظ والحذف والحدود والميزانية والموافقة البشرية.

## مصادر رسمية

- [OpenTelemetry Protocol Specification 1.11.1](https://opentelemetry.io/docs/specs/otlp/) — استقرار دعم traces وlogs، JSON protobuf، وتمثيل timestamps ومعرفات التتبع.
- [OpenTelemetry Traces Data Model](https://opentelemetry.io/docs/specs/otel/trace/data-model/) — حقول span والمدة والحالة.
- [OpenTelemetry Logs Data Model](https://opentelemetry.io/docs/specs/otel/logs/data-model/) — دلالة الوقت الأصلي ووقت الرصد، وكون `Body` يقبل قيمًا حرة، وتوصية اختيار `Timestamp` ثم `ObservedTimestamp` عند الحاجة إلى وقت واحد.
- [OpenTelemetry Service Resource Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/resource/service/) — تعريف `service.name` بوصفه الاسم المنطقي للخدمة.
- [OpenTelemetry Handling Sensitive Data](https://opentelemetry.io/docs/security/handling-sensitive-data/) — تقليل البيانات ومسؤولية مراجعة الحقول الحساسة.
- [OpenTelemetry Collector Configuration Best Practices](https://opentelemetry.io/docs/security/config-best-practices/) — حدود هذا التغيير: لا Collector ولا endpoint ولا صلاحية شبكة.
- [W3C Trace Context](https://www.w3.org/TR/trace-context/) — رفض معرفات التتبع ومعرفات الآباء ذات القيمة الصفرية.
