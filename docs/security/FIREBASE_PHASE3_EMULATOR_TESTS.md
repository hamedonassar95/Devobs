# Firebase Phase 3: اختبارات تخويل Firestore بالمحاكي

**الحالة: PENDING HUMAN APPROVAL.** هذه اختبارات محلية ببيانات اصطناعية. لا تفعّل Firebase في التطبيق، ولا تغيّر قواعد الإنتاج أو تنشرها.

## الأساس والأدلة السابقة

- بُني العمل على main عند SHA: 0c70d85c830835ad464d841803e3855f28622e24.
- تم التحقق من دمج PR #767. فحص CI على رأسه (45238000845) وCodeQL على الرأس (45237987280) نجحا. CI بعد الدمج على main (45240244073) وتحليلات CodeQL على SHA الدمج (45240242836) نجحت.
- قواعد التطبيق canonical في apps/ai-intelligence-console/firestore.rules ما زالت deny-all. لا يستخدم Emulator fixture هذه القواعد كإعداد للتطبيق، ولا ينسخ السياسة التجريبية إليها.
- دفتر الإنجازات يسجل PR #767. حالات P01 وAI-9 وCodex runtime بقيت كما هي.

## ماذا يختبر هذا المسار؟

يستخدم المسار Firebase Emulator Suite الرسمي، وFirestore Emulator فقط. ملف القواعد في هذا المجلد سياسة **تجريبية مستقلة** لا تصلح للنشر أو للاستخدام كسياسة إنتاج.

تحتوي البيانات الاصطناعية على المجموعات servers وincidents وdeployments. في كل مجموعة سجلات للمالك owner-a1 ضمن tenant-a، ومالك آخر owner-a2 ضمن tenant-a، ومالك owner-b1 ضمن tenant-b. لا توجد بيانات عميل أو مستخدم حقيقي.

| الحالة | النتيجة المطلوبة |
|---|---|
| قارئ مجهول يقرأ أو يسرد المجموعة | رفض بصلاحية permission-denied |
| قارئ مجهول ينشئ أو يعدّل أو يحذف | رفض بصلاحية permission-denied |
| مستخدم موثّق يحاول الوصول إلى سجل مستأجر آخر | رفض القراءة والتعديل والحذف |
| مستخدم يحاول الوصول إلى سجل مالك آخر ضمن المستأجر نفسه | رفض وفق سياسة المالك التجريبية |
| استعلام بلا قيد المستأجر والمالك معًا | رفض؛ Security Rules ليست مرشحًا لنتائج الاستعلام |
| استعلام مقيد بمالك ومستأجر المستخدم | نجاح وإرجاع سجله الاصطناعي فقط |
| المالك ينشئ ويقرأ ويعدّل ويحذف سجله ضمن fixture | نجاح |
| المالك يزوّر المستأجر أو المالك أو يغيّر حقول الملكية | رفض |
| المالك يضيف حقلًا خارج المخطط التجريبي | رفض |

لا يُعد السماح للمالك داخل هذا fixture قرارًا لنموذج إنتاج Devobs. التطبيق الحالي لا يعرّف بعد عقدًا موثوقًا لعضوية المستأجر والمالك؛ يلزم تصميم ذلك ومراجعته في تغيير منفصل قبل التفكير في قواعد الإنتاج.

## حدود العزل وعدم الاتصال الحي

- معرف المشروع ثابت ويبدأ بـ demo-؛ أمر الاختبار يمرر هذا المعرف صراحةً إلى Firebase CLI. توضح وثائق Firebase أن مشاريع demo لا تملك موارد Firebase حية، وأن محاولات الخدمات غير المحاكية تفشل.
- إعداد Firestore يربط المضيف بـ 127.0.0.1 والمنفذ 8080، ويعطّل واجهة المحاكي. قبل تهيئة SDK تتحقق الاختبارات من معرف المشروع، ومضيف ومنفذ Firestore، ومن أن أمر npm يشغّل Firestore وحده على مشروع demo المحدد.
- تتطلب الاختبارات متغير المضيف الذي يحقنه Emulator Suite بقيمة 127.0.0.1:8080. تشغيل ملف الاختبار مباشرة أو مع مضيف آخر يفشل قبل تهيئة Firestore؛ لا يوجد fallback إلى Firebase حي.
- تحقق فحص المقابس أثناء التشغيل من أن عملية Java الخاصة بـFirestore تستمع على 127.0.0.1:8080 (ظهرت في Linux كعنوان IPv4-mapped على loopback). كانت منافذ hub وlogging على loopback أيضًا. لا يبدأ الأمر Auth أو Functions أو Hosting.
- تُنشأ الهويات عبر authenticatedContext في مكتبة الاختبار؛ لا تُنشأ حسابات Firebase Auth ولا تُستخدم كلمات مرور أو رموز خدمة. تُكتب سجلات البذور الاصطناعية في المحاكي فقط عبر withSecurityRulesDisabled.
- لا يتطلب هذا المسار حساب Firebase أو مشروعًا حقيقيًا أو اشتراكًا مدفوعًا. يحتاج تنزيل الحزم وملف المحاكي الرسمي إلى اتصال بالإنترنت؛ تنفيذ الاختبارات وبياناتها محليان.
- تظل القواعد الحية المنشورة، وبياناتها، وإعدادات API key وApp Check وأعلام التطبيق **UNVERIFIED**. نجاح الاختبار المحلي لا يثبت أن سياسة fixture مناسبة للإنتاج أو أن قواعد الإنتاج نُشرت.

## إصدارات الأدوات المثبتة

تم التحقق من إصدارات الحزم بمحرك npm الرسمي بتاريخ 2026-11-23، واختُبرت في Node v24.22.1:

- firebase-tools 15.37.0
- firebase 13.4.0
- @firebase/rules-unit-testing 6.0.0، ويتطلب Node >=24.12.0 وFirebase SDK من الإصدار 13
- @grpc/grpc-js 1.14.7 override ضمن شجرة الاختبارات لمعالجة تنبيه عالي في النسخة المتعدية 1.9.16

اختبار Firebase Emulator حمّل Firestore Emulator v1.22.0. البيئة المحلية استخدمت OpenJDK 21.0.13. كل الاعتماديات محصورة في tests/firebase-emulator/package-lock.json؛ لا تغيّر قفل التطبيق.

**تنبيه توافق واعتماديات:** يطلب @firebase/firestore النطاق ~1.9.0 من @grpc/grpc-js؛ التثبيت المثبت 1.14.7 خارج ذلك النطاق لكنه من الإصدار الرئيسي نفسه. اجتازت حزمة الاختبارات المحلية كاملة بهذا التثبيت. يجب إعادة التحقق من التوافق عند ترقية Firebase SDK أو مكتبة القواعد.

أظهر npm audit بعد هذا التثبيت صفر ثغرات عالية أو حرجة. لكنه أظهر 14 تنبيهًا متوسطًا في شجرة أدوات emulator، ومنها OpenTelemetry وglob/minimatch وuuid في تبعيات Firebase CLI. لذلك:

- npm audit --audit-level=high — PASS، exit 0، مع ظهور التحذيرات المتوسطة.
- npm audit — FAIL، exit 1، بسبب 14 تنبيهًا متوسطًا.
- لم أشغّل npm audit fix --force ولم أبدّل Firebase CLI إلى إصدار أقدم لمعالجة التنبيهات. هذه التبعيات خاصة بمجلد اختبارات التطوير، وليست اعتماديات تشغيل تطبيق Devobs؛ تبقى مخاطرة موثقة للمراجعة.

## التشغيل المحلي

من جذر المستودع:

    cd tests/firebase-emulator
    npm ci
    npm test

يشغّل npm test الأمر التالي بعد تثبيت الحزم:

    firebase emulators:exec --project demo-devobs-firestore-authz --only firestore "node --test firestore.test.mjs"

يشغّل Emulator Suite المحاكي على localhost، ينفذ الاختبارات، ثم يوقفه تلقائيًا. لا تشغّل firebase deploy أو أوامر نشر القواعد.

## نتائج التحقق المحلي

النتائج التالية من هذه المراجعة المحلية؛ لا تشمل موارد Firebase حية:

| الأمر | النتيجة الفعلية |
|---|---|
| npm ci في tests/firebase-emulator | PASS، exit 0؛ أضيفت 712 حزمة. ظهرت تحذيرات إهمال لتبعيات متعدية. |
| npm test في tests/firebase-emulator | PASS، exit 0؛ 6 اختبارات، 6 نجاح، 0 فشل أو تخطٍ. |
| env -u FIRESTORE_EMULATOR_HOST node --test firestore.test.mjs | فشل متوقع، exit 1؛ رفضت hook التهيئة التشغيل قبل تهيئة Firestore SDK، وظهرت الحالات الست كفاشلة بسبب hook. هذا اختبار fail-closed؛ لا fallback إلى خدمة حية. |
| فحص منفذ Firestore عبر ss أثناء Firebase Emulator Suite | PASS، exit 0؛ عملية Java تستمع على loopback للمنفذ 8080. |
| python3 scripts/check_firebase_rules_baseline.py | PASS، exit 0؛ CANONICAL_DENY_ALL_BASELINE / LOCAL_SOURCE_ONLY. |
| python3 -m unittest discover -s tests -p 'test_firebase_rules_baseline.py' -v | PASS، exit 0؛ 7 اختبارات، OK. |
| python3 scripts/milestone_ledger.py --summary | PASS، exit 0؛ 306 إنجازات، أحدث PR مسجل 767، 3 بوابات مفتوحة. |
| python3 -m unittest tests.test_milestone_ledger -v | PASS، exit 0؛ 88 اختبارًا، OK بعد تحديث توقعات الدفتر لتسجيل PR #767. |
| python3 scripts/check_action_pins.py | PASS، exit 0؛ 48 ملف workflow/template. |
| git diff --check | PASS، exit 0؛ لا توجد أخطاء whitespace. |
| فحص روابط Markdown المحلية في README.md ودليل Phase 3 | PASS، exit 0؛ كل الروابط المحلية المشار إليها موجودة. |

**CodeQL وCI على هذا PR:** تُسجّل روابط ونتائج الرأس النهائي في وصف PR بعد اكتمال GitHub Actions. اختبار Emulator محلي ولا يغيّر CI أو ينشر قواعد.

## المخاطر والرجوع

سياسة fixture تفرض ملكية على مستوى المالك وتقييد مخطط بسيط من ثلاثة حقول. قد لا تناسب سجلات الحوادث أو النشر المشتركة بين أعضاء الشركة، ولا تثبت عضوية tenant حقيقية. لذلك لا تُنسخ إلى التطبيق أو Firebase Console دون تصميم schema/claims، واختبارات استعلامات، ومراجعة مستقلة وموافقة صريحة.

لا توجد موارد حية تحتاج إلى استرجاع. لإيقاف Emulator يدويًا إن أُوقف التنفيذ قسرًا، أوقف فقط عملية الاختبار المحلية التي بدأت لهذا الأمر. ملفات السجل المحلية مستثناة من Git. للتراجع عن التغيير بعد مراجعته، استخدم revert لالتزام PR المحدد؛ لا تنشر قواعد ولا تغيّر إعدادات الإنتاج.

**PENDING HUMAN APPROVAL.** المطلوب من المراجع هو تدقيق fixture وحدود الاعتماديات المتوسطة. لا تدمج أو تنشر كجزء من هذا العمل.

## المراجع الرسمية

- Firebase Emulator Suite: https://firebase.google.com/docs/emulator-suite/install_and_configure
- Firestore Emulator وربطه بالتطبيقات: https://firebase.google.com/docs/emulator-suite/connect_firestore
- اختبار Firestore Security Rules باستخدام المحاكي: https://firebase.google.com/docs/firestore/security/test-rules-emulator
- Firebase CLI على npm: https://www.npmjs.com/package/firebase-tools/v/15.37.0
- Firebase JS SDK على npm: https://www.npmjs.com/package/firebase/v/13.4.0
- Firebase Rules Unit Testing على npm: https://www.npmjs.com/package/@firebase/rules-unit-testing/v/6.0.0
