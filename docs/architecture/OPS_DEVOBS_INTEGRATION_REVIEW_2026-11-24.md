# مراجعة ربط `ops` مع Devobs

**تاريخ المراجعة:** 2026-11-24 UTC
**الغرض:** التحقق مما هو مربوط حاليًا، وتحديد ما يمكن الاستفادة منه بأمان دون نسخ وظائف مكررة أو توسيع صلاحيات التشغيل.
**النطاق:** قراءة بيانات المستودعات العامة وملفات المصدر فقط. لم أقرأ أسرارًا أو قيم بيئة، ولم أصل إلى قواعد بيانات أو خدمات سحابية.

## النتيجة

**الربط موجود بالفعل على مستوى المصدر وفحص CI للقراءة فقط.** مستودع `ops` مدرج في خريطة Devobs، وتعرض لوحة GitHub فيه زرًا يدويًا لفحص CI للمستودعات المسموح بها. الفحص لا يعمل تلقائيًا، والخدمة المحلية معطّلة افتراضيًا. لا يلزم نسخ تطبيق `ops` مرة أخرى إلى Devobs.

راجعت الفروقات المفيدة: فهرسة Graphify المحلية موثقة في Devobs أصلًا، وتوجد في Devobs آلية منفصلة لتشخيص الحوادث محمية ومغلقة افتراضيًا. أما الوظائف الأخرى في `ops` فتتضمن وصولًا إلى Firebase وواجهات Google/Gemini وكتابة مباشرة إلى GitHub أو إرسال `repository_dispatch`. لم أفعّلها أو أنقلها؛ بعضها غير آمن للنسخ كما هو، وبعضها يحتاج تحققًا مستقلًا من الهوية والصلاحيات والتكلفة.

## المستودعات والأدلة الحالية

| المستودع | الفرع/المراجعة | الدليل |
|---|---|---|
| Devobs | `main` — `bedb3ec03697e5e35efb9a6bbcbdbc31f54b5014` | [المراجعة الحالية على GitHub](https://github.com/hamedonassar95/Devobs/tree/bedb3ec03697e5e35efb9a6bbcbdbc31f54b5014)؛ فحص CI على هذا الرأس نجح في [45384044192](https://github.com/hamedonassar95/Devobs/actions/runs/45384044192). |
| `ops` | `main` — `d0f80f9e8256d01fc18cc1d117773df3fa76c2ae` | [المراجعة الحالية على GitHub](https://github.com/hamedonassar95/ops/tree/d0f80f9e8256d01fc18cc1d117773df3fa76c2ae)؛ GitHub يعرّفه كمستودع مستقل، وليس fork. |

**VERIFIED:** فحص بناء `ops` رقم `45378521215` انتهى بنجاح على الرأس `d0f80f9e8256d01fc18cc1d117773df3fa76c2ae`. أصلح PR [#3](https://github.com/hamedonassar95/ops/pull/3) عقد تثبيت Bun والملف المقفل، واستخدم CI الحالي Bun `1.4.5` وNode `24.22.1` مع تثبيتات Actions كاملة الـSHA وصلاحية `contents: read`. هذه إصلاحات لبناء المستودع نفسه؛ لا حاجة لإضافة Bun إلى تطبيق Devobs الذي يستخدم سلسلة أدواته وملف القفل الخاصين به.

## كيف يرتبط `ops` بـ Devobs الآن

1. **خريطة المصدر:** يسجل [`repository_database_map.json`](repository_database_map.json) مستودع `ops` مع المستودعات ذات الصلة. هذه لقطة موثقة وليست اتصالًا بقاعدة بيانات.
2. **فحص CI يدوي:** تعرض [`RepositoryDatabaseMapPanel`](../../apps/ai-intelligence-console/src/components/github/RepositoryDatabaseMapPanel.tsx) زر **Check GitHub CI** لكل مستودع مسموح. لا يوجد polling تلقائي.
3. **واجهة قراءة فقط:** يستخدم [`publicGithubStatus.ts`](../../apps/ai-intelligence-console/publicGithubStatus.ts) طلبات GitHub عامة ثابتة ومحددة. لا يستخدم PAT أو OAuth ولا يقبل عنوان URL أو اسم مستودع عشوائي.
4. **التفعيل محلي اختياري:** في [`server.ts`](../../apps/ai-intelligence-console/server.ts) يبقى الفحص مغلقًا ما لم يضبط المشغّل المحلي `DEVOBS_PUBLIC_GITHUB_STATUS_ENABLED=true`، ويشترط الاستماع على `127.0.0.1`. لم أغيّر الإعداد ولم أختبر استضافة عامة. تفاصيل الحدود في [دليل التطبيق](../../apps/ai-intelligence-console/README.md).

هذا يثبت **تكاملًا من ناحية المصدر**. لا يثبت أن واجهة Devobs منشورة أو أن الفحص مفعّل في أي بيئة مستضافة. حالة `ops` أعلاه هي نتيجة GitHub Actions على commit محدد، وليست إثبات صحة التطبيق أو نشره.

## ما هو مفيد وموجود أصلًا في Devobs

| القدرة | الحالة | قرار النقل |
|---|---|---|
| فحص حالة CI العامة لـ `ops` | **VERIFIED في المصدر؛ التشغيل المحلي اختياري** | استخدم اللوحة الموجودة. لا تضف Dispatcher أو polling مكررًا. |
| فهرسة Graphify محليًا وبدون رفع الشيفرة | **VERIFIED في مصدر Devobs** | `ops/docs/graphify-local.md` يحيل أصلًا إلى مشغّل Devobs؛ راجع [التصميم المركزي](graphify-integration.md). لا تنسخ CLI أو تبعيات مكررة. |
| تشخيص الحوادث عبر Devobs | **الكود موثق في Devobs؛ التشغيل الحي UNVERIFIED** | يوجد proxy منفصل محمي ومغلق افتراضيًا. دليل `ops` نفسه يصف التكامل بأنه غير منشور وغير مختبر حيًا؛ لا تنقل إعدادات أو أسرارًا. |
| واجهات لوحة React وGoogle Workspace وGemini | **موجودة ضمن تطبيق Devobs المستورد؛ التفعيل الفعلي UNVERIFIED** | أعد استخدام التطبيق الموجود فقط بعد مراجعة كل تكامل وهوية وصلاحياته. لا تنسخ إعدادات مزود أو OAuth scopes من `ops`. |
| Firebase القديم | **مصدر قديم فقط؛ الاتصال الحي UNVERIFIED** | لا تنقل قواعد `ops` أو تفعّل Firebase. Devobs يبقي Firebase معطّلًا افتراضيًا وقواعد Firestore canonical من نوع deny-all. |

## وظائف `ops` التي لم أنقلها

### كتابة GitHub وإرسال الأحداث

- تحتوي واجهة `ops` في `GitHubTab.tsx` على إدخال PAT واختبار الرمز واختيار الفرع وخيار force-push؛ وتحتوي `server.ts` على مسارات مرتبطة بالدفع إلى GitHub. لم أنقل هذه الواجهة أو المسارات. هذه صلاحية كتابة مباشرة ولا حاجة لها لفحص CI.
- يحتوي [`dispatch-to-devobs.yml`](https://github.com/hamedonassar95/ops/blob/d0f80f9e8256d01fc18cc1d117773df3fa76c2ae/.github/workflows/dispatch-to-devobs.yml) على خطوة إرسال تتطلب سرًا بصلاحية كتابة للمستودع الهدف. وجود إعداد السر أو صلاحيته **UNVERIFIED**؛ لم أفحصه.
- تشغيل الإرسال الأخير [45378593746](https://github.com/hamedonassar95/ops/actions/runs/45378593746) على SHA `d0f80f9e8256d01fc18cc1d117773df3fa76c2ae` فشل في خطوة **Prepare metadata-only repository dispatch payload**، وتُخطيت خطوة الإرسال. لم أقرأ السجلات الخام ولم أرسل أي حدث.
- **خلل مصدر مؤكد ومتوافق مع فشل التحضير:** شرط الـworkflow يقيّد المصدر إلى مستودع التشغيل الحالي (`ops`)، بينما يعرّف [`repository_dispatch.mjs`](https://github.com/hamedonassar95/ops/blob/d0f80f9e8256d01fc18cc1d117773df3fa76c2ae/scripts/repository_dispatch.mjs) `SOURCE_REPOSITORY` على أنه `hamedonassar95/Devobs`، ويرفض أي `head_repository` لا يطابقه. لذلك لا يطابق payload حدث `ops` هذا الشرط. هذا تعارض مصدر موثق؛ سبب فشل التشغيل المسجل تحديدًا يظل **UNVERIFIED** لأن سجل الخطوة لم يُراجع.
- وفق توثيق GitHub، يحمل حدث `workflow_run` معلومات تشغيل workflow المصدر؛ راجع [مرجع الحدث الرسمي](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run). لا أوصي بتصحيح هذا المسار أو تشغيله ضمن طلب الدمج الحالي: يلزم أولًا مراجعة منفصلة لصلاحية Contents write، وحماية مصدر الـworkflow، وسلوك المستقبِل على Devobs.

### قواعد البيانات والذكاء الاصطناعي

- في [`firestore.rules`](https://github.com/hamedonassar95/ops/blob/d0f80f9e8256d01fc18cc1d117773df3fa76c2ae/firestore.rules)، تسمح القواعد القديمة بقراءات عامة بسبب `|| true`، وتسمح بكتابات للمستخدم المسجّل دون تحقق ملكية أو tenant. **لا تنقل هذه القواعد ولا تنشرها.** لا يثبت هذا التدقيق أنها منشورة على Firebase.
- ملفات `ops` تتضمن Firebase وGemini وGoogle Workspace. لم أفحص أسرارها أو إعداداتها، ولم أختبر اتصالًا بها أو أستهلك خدمة مدفوعة. وجود الشيفرة أو الادعاءات التسويقية لا يثبت أن التكامل يعمل أو أن استخدامه مصرح.
- إعدادات `devobs-saas` وRender وSupabase تبقى نطاقات منفصلة؛ لم أصل إلى قواعد بياناتها ولم أدمج بياناتها.

## التصنيف والقرار

- **VERIFIED:** مستودعا Devobs و`ops` على SHA المذكورين؛ `ops` ليس fork وفق بيانات GitHub؛ لوحة Devobs تحتوي فحص CI عامًّا يدويًا ومغلقًا افتراضيًا؛ CI لـ `ops` نجح على SHA الحالي؛ تشغيل dispatch فشل قبل خطوة الإرسال.
- **UNVERIFIED:** تفعيل اللوحة في استضافة فعلية، وجود سر dispatch أو صلاحيته، استقبال الحدث في Devobs، اتصال Firebase أو Google Workspace أو Gemini، ونشر أي موارد من `ops`.
- **BLOCKED للنقل:** PAT والدفع المباشر/force-push، dispatcher الذي يحتاج صلاحية كتابة، وقواعد Firestore القديمة. لا تنقلها إلى Devobs.
- **القرار:** أبقِ Devobs المستودع canonical، واستفد من `ops` عبر فحص CI العام الموجود فقط. لا أنقل شيفرة إضافية الآن لأن القدرات الآمنة المقصودة موجودة أصلًا، والفروقات المتبقية إما مكررة أو ذات أثر جانبي/صلاحيات غير مناسبة.

لم يتغير أي كود تشغيل أو قواعد صلاحيات أو إعدادات نشر. لم يحدث تفعيل، نشر، دمج قواعد بيانات، أو استدعاء لتكامل خارجي.
