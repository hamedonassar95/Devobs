# Firebase Phase 5: تدقيق قواعد Firestore المستضافة للقراءة فقط

**الحالة: BLOCKED — لم يتوفر وصول Firebase/Google Cloud مصرح به في جلسة التدقيق.** هذا التقرير يثبت ما أمكن من مصدر Devobs واختباراته فقط؛ لا يثبت القواعد الفعالة في المشروع `my-apps-hamedo`. **PENDING HUMAN APPROVAL.**

## نطاق المراجعة والأساس

- المستودع: `hamedonassar95/Devobs`.
- أساس الفرع المعزول: `main` عند `2e47bd4b1c28d1e01d75e80031cdae2b91210399`، بعد دمج PR #772. تحقق `validate` وفحوص Python 3.12/3.15 وNode وCodeQL على هذا الرأس. فشل فحص Dependabot المنفصل (`45278361046`)؛ لا يُعامل هذا الفشل على أنه نجاح ولا كتدقيق لقواعد Firebase.
- تحقق GitHub مباشرةً من PR #766 و#767 و#768 و#770 ومن نتائج CI/CodeQL المسجلة في الدليلين السابقين. دمج Phase 4 هو PR #770: الرأس `8876757f34589bdacbde815d59865f4cfbc6b11d`، ودمجه `432cda3fc0fef928e25ace35fc7fed3f6913908a`؛ فحوص CI وCodeQL على رأسه ناجحة. هذا يؤكد تغيير المصدر واختباراته فقط.
- فُحصت أدلة Phase 1 و2 و3، واختبارات عزل العرض التجريبي في Phase 4، وقواعد التطبيق والـ Emulator fixture عند أساس هذا الفرع.
- دفتر الإنجازات في هذا الأساس يعرض `merged_milestones: 308` و`latest_pr: 770` مع أن GitHub يؤكد دمج #772؛ هذا اختلاف توثيقي قائم لم يُعدّل ضمن النطاق المطلوب.

## خلاصة التدقيق

| السؤال | النتيجة | نوع الدليل |
|---|---|---|
| ما القواعد المرفقة حاليًا بقاعدة Firestore في `my-apps-hamedo`؟ | **BLOCKED / UNKNOWN** — لم تُقرأ واجهة Firebase Rules المستضافة. | لا توجد هوية Google مصرح بها أو أداة Firebase Rules في هذه الجلسة؛ وسياسة المستودع تمنع استخدام `gcloud` أو حساب Google Cloud الخاص بالمالك من هذه البيئة. |
| هل تسمح القواعد المستضافة بقراءة مجهولة؟ | **UNVERIFIED**. | توجد في Phase 1/2 لقطة شاشة مقدمة من المالك ووثيقة قواعد مرجعية قديمة ذات قراءة عامة، لكنهما لا يثبتان النشر الحالي. |
| هل تسمح بكتابة المستخدم المسجل دون ملكية أو tenant؟ | **UNVERIFIED**. | لا توجد معاينة للقواعد المستضافة. القواعد المرجعية القديمة كانت تفتقر إلى فحص الملكية؛ هذا خطر مشروط فقط إذا كانت سياسة مماثلة هي المنشورة. |
| هل تفرض ملكية المستخدم وعزل المستأجر؟ | **UNVERIFIED** في المشروع المستضاف. | نموذج الإنتاج في ملفات Devobs المفحوصة لا يثبت ادعاءات tenant/owner؛ ادعاءات الاختبار المحلي اصطناعية ومنفصلة. |
| هل سياسة المشروع المستضاف default-deny؟ | **UNVERIFIED**. | ملف قواعد التطبيق في المستودع يرفض كل وصول، لكن لا يوجد دليل على أنه نُشر أو أنه مربوط بقاعدة المشروع المستهدف. |
| ما أسماء قواعد Firestore الفعلية؟ | **BLOCKED / UNKNOWN**. | لم تُستدعَ واجهة بيانات قواعد المشروع؛ ولا تُقرأ قيمة إعداد التشغيل `VITE_FIRESTORE_DATABASE_ID`. |

لا يوجد في هذا التدقيق **اختراق أو تعرض مستضاف مؤكد**؛ كذلك لا يوجد دليل كافٍ لنفيه. أي خطر قراءة عامة أو كتابة عابرة للمستأجرين يبقى مشروطًا بمراجعة الإصدار والقواعد الفعالة.

## سبب حجب الفحص الحي

لم يُعثر على موصل Firebase/Firestore أو Google Cloud موثوق في الجلسة. كما تنص `AGENTS.md` على أن هذه البيئة لا تصل إلى حساب Google Cloud الخاص بالمالك، وتحظر تشغيل `gcloud` أو محاولة النشر. لذلك لم أستخرج رمز وصول، ولم أجرّب طلبًا مجهولًا، ولم أرسل طلبًا إلى المشروع الحي. هذا إيقاف مقصود عند حد الصلاحية؛ لا تُعدّل قواعد الاستضافة ولا إعدادات المشروع.

## ما تثبته ملفات المصدر الحالية

**VERIFIED عند أساس هذا الفرع، وليس دليلًا على Firebase Console:**

1. ملف قواعد Devobs المرفق بالتطبيق يحتوي قاعدة عامة واحدة: `allow read, write: if false`. هذا رفض كامل في **مصدر التطبيق**، ولا يثبت الإصدار المستضاف. [مصدر القواعد عند SHA الأساس](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/firestore.rules#L1-L10).
2. لا يهيّئ التطبيق Firebase إلا عندما تكون قيمة `VITE_FIREBASE_ENABLED` هي `true` وتكون إعدادات Firebase الستة غير فارغة. يمكن أن يحدد `VITE_FIRESTORE_DATABASE_ID` قاعدة مسماة؛ إذا لم تُمرر قيمة صريحة، يستدعي كود Firestore واجهة SDK بلا معرّف قاعدة. **لم تُقرأ أي قيمة بيئة**، لذا لا نعرف هل التكامل مفعّل في أي نشر أو أي قاعدة يستهدفها. [تهيئة Firebase](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/src/services/firebaseApp.ts#L5-L25) و[اختيار قاعدة Firestore](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L15-L21).
3. واجهة Firestore الكسولة تفعّل الاشتراكات والحفظ والحذف فقط عندما يكون العلم صريحًا. لكن حالة قيم التشغيل غير معروفة؛ وجود واجهة عميل لا يثبت نجاح طلب أو سماح قواعد. [واجهة Firestore](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/src/services/firebaseFirestoreFacade.ts#L5-L59).
4. Phase 4 يفصل أفعال لوحة العرض التجريبية عن Firestore: اختبارات الانحدار تغطي إنشاء الخادم وتحديثه وحذفه وإنشاء حادثة ونشر، مع العلمين `false` و`true`، وتتحقق من عدم استدعاء عمليات الحفظ/الحذف أو استيراد الواجهة. هذا يمنع تلك الأفعال التجريبية من الكتابة عبر ذلك المسار، لكنه لا يحول قواعد أي قاعدة حية إلى سياسة آمنة ولا يختبر مستخدمًا أو مستأجرًا حقيقيًا. [مصنع أفعال العرض](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/src/App.tsx#L106-L121) و[اختبارات العزل](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/apps/ai-intelligence-console/tests/demoFirestoreIsolation.test.mjs#L156-L245).
5. Phase 3 يشغل Emulator محليًا على `127.0.0.1:8080` بمعرّف مشروع تجريبي `demo-devobs-firestore-authz` وبسجلات اصطناعية. قواعد هذا الـfixture **تجريبية** وتسمح لمالك اصطناعي محدد؛ ليست قواعد إنتاج معتمدة ولا تمثل خدمة Firebase المستضافة. [قواعد Emulator التجريبية](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/tests/firebase-emulator/firestore.rules) و[اختبار Emulator](https://github.com/hamedonassar95/Devobs/blob/2e47bd4b1c28d1e01d75e80031cdae2b91210399/tests/firebase-emulator/firestore.test.mjs).

**UNVERIFIED / خطر تاريخي مشروط:** وثيقتا Phase 1 و2 تسجلان لقطة مالك وقواعد مرجعية قديمة سمحت بقراءات عامة عبر `... || true` وكتابات لأي مستخدم مسجل دون إثبات المالك أو المستأجر. لا نعرف إن كانت هذه القواعد قد نُشرت يومًا أو ما زالت منشورة. لذلك نستخدمها كإشارة تستلزم التحقق، لا كحكم على الوضع الحالي ولا كدليل على وجود بيانات مكشوفة.

## جرد قواعد البيانات

| النطاق | ما نعرفه | ما لا نعرفه |
|---|---|---|
| التطبيق في Devobs | يقرأ `VITE_FIRESTORE_DATABASE_ID` من إعداد التشغيل؛ واجهة العميل تقبل قاعدة صريحة أو الاستدعاء الافتراضي. | القيمة الفعلية، وهل التطبيق متصل في أي بيئة، والـdatabase ID المرتبط بقواعد المشروع الحي. |
| Emulator المحلي | إعداد الاختبار يستخدم مشروعًا تجريبيًا وقاعدة SDK الافتراضية على Firestore Emulator المحلي. | هذا لا يكشف أسماء قواعد المشروع الحقيقي. |
| Firebase `my-apps-hamedo` | اسم المشروع **مقدم من طلب المالك**. | لم يتم التحقق من هوية المشروع أو أسماء قواعد البيانات أو قواعد الإصدار المرتبطة بها. |

لا يُستنتج أن قاعدة المشروع هي `(default)` من ملفات المصدر؛ كما لا يمكن عدّ قواعد المشروع الحي من wildcard `/databases/{database}/documents` وحده. يلزم ربط إصدار Rulesets بنقطة إرفاقه، ثم مطابقة قواعد البيانات بالمعرّفات من بيانات الموارد فقط.

## طريقة القراءة المسموح بها عند توفر هوية مصرح بها

توثّق Firebase رسميًا واجهات Rules REST API v1 التالية. لم تُستدعَ هنا؛ هذه خطة للتحقق اللاحق بعد توافر هوية موجودة بصلاحية قراءة مناسبة، دون إنشاء صلاحيات أو قراءة مستندات التطبيق:

1. `GET https://firebaserules.googleapis.com/v1/projects/my-apps-hamedo/releases` — جلب أسماء الإصدارات وربط كل `Release` بحقل `rulesetName` ووقت الإنشاء/التحديث. يلزم اتباع صفحات النتائج حتى لا تُفقد إصدارات. [توثيق `projects.releases.list`](https://firebase.google.com/docs/reference/rules/rest/v1/projects.releases/list).
2. `GET https://firebaserules.googleapis.com/v1/projects/my-apps-hamedo/rulesets` — جلب بيانات Rulesets الوصفية فقط عند الحاجة، مثل الخدمات ونقطة الإرفاق؛ ثم `GET https://firebaserules.googleapis.com/v1/projects/my-apps-hamedo/rulesets/{ruleset_id}` للإصدار المشار إليه وحده، للحصول على ملفات مصدر القواعد. [توثيق `projects.rulesets` وحقول `attachment_point`/`source`](https://firebase.google.com/docs/reference/rules/rest/v1/projects.rulesets) و[توثيق `projects.rulesets.get`](https://firebase.google.com/docs/reference/rules/rest/v1/projects.rulesets/get).
3. عند الحاجة لتأكيد جميع أسماء قواعد البيانات، تستخدم واجهة Firestore **لبيانات القواعد فقط**: `GET https://firestore.googleapis.com/v1/projects/my-apps-hamedo/databases`. لا تُطلب `documents` أو `collections` أو أي بيانات تطبيق. [توثيق `projects.databases.list`](https://docs.cloud.google.com/firestore/docs/reference/rest/v1/projects.databases/list).
4. تسجل النتيجة لكل قاعدة: database ID، اسم Release المرتبط بها، `rulesetName`، `updateTime`، الخدمات ونقطة الإرفاق، وأسماء ملفات المصدر/بصمتها. بعد ذلك تفحص المصدر الكامل المنسوب إلى ذلك الإصدار للتحقق من `allow read` و`get/list` و`create/update/delete`، فحوص `request.auth`, `tenantId`, owner/UID، والتطابقات غير المسموح بها افتراضيًا. لا يكفي فحص مقتطف أو قاعدة واحدة إذا كانت هناك قواعد سماح أخرى متداخلة.

تذكر وثائق Firebase أن واجهتي `releases.list` و`rulesets.get` تقبلان نطاق `https://www.googleapis.com/auth/firebase.readonly`. يجب أن تكون صلاحية IAM الموجودة أضيق ما يمكن؛ لا تُنشأ صلاحيات جديدة ضمن هذا العمل. إذا لم تكن الهوية الحالية مخولة، تبقى النتيجة BLOCKED بدل توسيع الصلاحيات.

## مصفوفة النتائج حسب المحور

| المحور | نتيجة المصدر أو الاختبار المحلي | حالة القواعد المستضافة | الأثر |
|---|---|---|---|
| قراءة مجهولة | ملف التطبيق المحلي deny-all؛ Phase 2 يصف سلوكًا أوسع في مرجع قديم. | **UNVERIFIED** | لا نستطيع إثبات السماح أو الرفض في قاعدة `my-apps-hamedo`. |
| كتابة مستخدم موثق | ملف التطبيق المحلي deny-all؛ الـfixture التجريبي لا يسمح إلا بهوية مالك اصطناعية على سجل اصطناعي. | **UNVERIFIED** | لا نستطيع إثبات رفض إنشاء/تعديل/حذف عابر للمستأجر في الإنتاج. |
| tenant/owner | لا يثبت مصدر نماذج التطبيق وجود `tenantId`/`ownerId` موثوقَين؛ الـfixture المحلي يستخدم claims اصطناعية فقط. | **UNVERIFIED** | لا يُعتمد تسجيل الدخول وحده كإثبات ملكية أو عضوية. |
| default-deny | قاعدة التطبيق المحلية ترفض الجميع؛ قواعد Emulator منفصلة. | **UNVERIFIED** | لا يمكن نسب سياسة المصدر أو الاختبار المحلي إلى الإصدار المستضاف. |
| قاعدة البيانات/نقطة إرفاق الإصدار | معرّف قاعدة التشغيل اختياري في المصدر. | **BLOCKED** | أسماء القواعد والإصدارات ونقاط الإرفاق الحية غير معروفة. |

## نتائج التحقق

سجّل هنا النتائج التي أُعيد تشغيلها على رأس هذا الفرع. فحوص قواعد المصدر والمحاكي لا تستعلم عن Firebase الحي:

| الأمر | النتيجة | الدليل |
|---|---|---|
| `python3 scripts/milestone_ledger.py --summary` | **PASS**, exit 0 | `merged_milestones: 308`, `latest_pr: 770`, `open_gates: 3`; P01 وAI-9=`BLOCKED`، وقبول Codex=`OPEN`. |
| `python3 scripts/check_firebase_rules_baseline.py` | **PASS**, exit 0 | `CANONICAL_DENY_ALL_BASELINE`, `LOCAL_SOURCE_ONLY`. |
| `python3 -m unittest discover -s tests -p 'test_firebase_rules_baseline.py' -v` | **PASS**, exit 0 | `Ran 7 tests`; `OK`. |
| `npm ci` في `tests/firebase-emulator/` | **PASS**, exit 0 | Node `v24.22.1`, Java `21.0.13`; ثُبتت 712 حزمة من القفل خلال دقيقتين. ظهرت تحذيرات تقادم لتبعيات انتقالية (`uuid@9`, `glob@10.5.0` وغيرها). لم تُحدّث الحزم أو ملف القفل. |
| `npm test` في `tests/firebase-emulator/` | **PASS**, exit 0 | Firestore Emulator المحلي؛ الاختبارات `6 passed`, `0 failed`, `0 skipped`. البيانات والهويات اصطناعية. |
| فحص روابط Markdown المحلية المضافة | **PASS**, exit 0 | فُحص رابط README الجديد والملف الهدف؛ `1` رابط محلي، والهدف موجود. **NOT RUN:** لا يوجد مدقق Markdown عام مهيأ في المستودع. |
| `python3 scripts/check_action_pins.py` | **PASS**, exit 0 | `Action pin check passed for 48 workflow and template files.` |
| `git diff --check` | **PASS**, exit 0 | بعد تجهيز الملفين؛ لا أخطاء مسافات أو whitespace. |
| CI وCodeQL على أساس main `2e47bd4…` | **PASS** للفحوص المطلوبة؛ **FAIL** لفحص Dependabot | `validate` وPython/Node وCodeQL JS/Python/Actions نجحت. [Main CI](https://github.com/hamedonassar95/Devobs/actions/runs/45278226350)، [CodeQL](https://github.com/hamedonassar95/Devobs/actions/runs/45278225413)، [Dependabot الفاشل](https://github.com/hamedonassar95/Devobs/actions/runs/45278361046). |
| CI وCodeQL على رأس PR #773 `79057408fb9c4eb4d0a266dc09f623e1b7cbfff9` | **PASS** للفحوص المطلوبة | [CI في PR](https://github.com/hamedonassar95/Devobs/actions/runs/45281950020): `validate` نجح؛ [CodeQL](https://github.com/hamedonassar95/Devobs/actions/runs/45281942114) نجح في Python وJavaScript/TypeScript وActions. [تشغيل الدفع على SHA نفسه](https://github.com/hamedonassar95/Devobs/actions/runs/45281856054) نجح، بما في ذلك Python 3.12/3.15 وNode؛ `production-release` تخطاه التشغيل. PR #773 بقي Draft؛ حالة الدمج كانت `CLEAN` عند الفحص. |
| Firebase Rules REST API v1 / أسماء قواعد المشروع | **BLOCKED** | لم ينفذ أي طلب مستضاف؛ لا توجد هوية مصرح بها في الجلسة. |

## الخطوة التالية الوحيدة

**الخطوة التالية:** يتيح المالك وصول قراءة قائمًا إلى Firebase Rules API v1 وبيانات قواعد Firestore فقط، أو يشغّل المالك/مشغل مخول طلبات `GET` أعلاه في جلسة موثوقة ويراجع/يشارك مخرجاتها المنقحة (أسماء الموارد ومصدر القواعد فقط، بلا رموز أو بيانات تطبيق). بعدها يُحدّث هذا التقرير على فرع مستقل ليربط كل قاعدة إصدار بقاعدة البيانات الصحيحة ويصنف السماح/الرفض. لا ترفع القواعد ولا تجرّب طلب قراءة لمستندات.

**لا تغيير لقواعد أو نشر أو فوترة أو IAM.** تبقى بوابات P01=`BLOCKED / NO-GO` وAI-9=`BLOCKED` وCodex runtime=`OPEN` دون تعديل. نتيجة هذا العمل **PENDING HUMAN APPROVAL**.
