# Firebase — المرحلة الثانية: جرد صلاحيات الوصول

**الحالة: PENDING HUMAN APPROVAL.** هذه مراجعة للمصدر والوثائق فقط؛ لا تثبت حالة Firebase المنشورة ولا تمنح إذنًا لتفعيل التكامل.

## 1. أساس المراجعة وحدودها

- **VERIFIED (GitHub):** المستودع هو `hamedonassar95/Devobs`. رأس `main` الذي بُنيت عليه هذه المراجعة هو `6cc250a830e776909e5b095d3543e6ffffcb2760`، وهو دمج PR [#766](https://github.com/hamedonassar95/Devobs/pull/766). رأس PR كان `0eb5057a459af9f35d46221885af2e14af3b7eb3`، ودمجه إلى `main` أعطى SHA أعلاه.
- **VERIFIED (GitHub CI على رأس PR #766):** [CI run 45232877435](https://github.com/hamedonassar95/Devobs/actions/runs/45232877435) و[مراجعة AI Code Review run 45232877291](https://github.com/hamedonassar95/Devobs/actions/runs/45232877291) انتهيا بـ`success`. حالة Vercel على رأس PR كانت `success`؛ مراجعة PR-Agent الاختيارية كانت `skipped` وليست فشلًا مطلوبًا.
- **VERIFIED (المصدر عند SHA الأساس):** قواعد `apps/ai-intelligence-console/firestore.rules` تمنع كل قراءة وكتابة. مرحلة Firebase 1 تقول إن التكامل معطّل افتراضيًا، وإن القواعد الحية لم تُتحقق منها.
- **VERIFIED (المستودع المرجعي):** تأكدت هوية `hamedonassar95/DevObs-ai-Intelligence-` كمرجع خاص بفرع افتراضي `main`؛ اقتصر الوصول على قراءة `firestore.rules` ولم أكتب إليه.
- **VERIFIED (دفتر الإنجازات عند SHA الأساس):** `python3 scripts/milestone_ledger.py --summary` يسجل 305 إنجازات و`latest_pr: 747` وثلاث بوابات مفتوحة: P01=`BLOCKED`، AI-9=`BLOCKED`، وقبول Codex runtime=`OPEN`. PR #766 تحققنا منه مباشرة عبر GitHub لكنه لم يظهر في رقم `latest_pr` لذلك الدفتر عند هذا الأساس. لم أعدّل الدفتر لأن نطاق الملفات المطلوب هنا هو هذا الدليل ورابط README فقط.
- **UNVERIFIED:** قواعد Firestore الفعلية المنشورة، قاعدة البيانات التي يستخدمها أي عميل، طبيعة البيانات الموجودة، إعداد تسجيل الدخول الفعلي، تقييدات API key وحالة App Check على Firebase Console.
- **BLOCKED عمدًا:** لم تُقرأ أسرار أو قيم إعدادات البيئة، ولم يُتصل بقاعدة Firebase حية أو تُقرأ سجلات منها. لم تُنشر قواعد ولم تتغير بيانات اعتماد أو فوترة أو IAM أو استضافة.

روابط المصدر التالية مثبتة على SHA الأساس لتسهيل تدقيق الادعاءات:

- [قواعد Devobs canonical عند SHA الأساس](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/firestore.rules#L1-L10)
- [تهيئة Firebase وعلم التفعيل](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseApp.ts#L1-L26)
- [واجهة Firestore الكسولة](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestoreFacade.ts#L1-L59)
- [خدمة Firestore وعملياتها](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L15-L200)
- [أنواع بيانات الخوادم والحوادث والنشر](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/types/serverDashboard.ts#L7-L50)
- [تسجيل Google الاختياري](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/googleAuth.ts#L9-L13)
- [اشتراكات Firestore وإجراءات العرض التجريبي](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/App.tsx#L195-L214)
- [حفظ وحذف سجلات العرض التجريبي](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/App.tsx#L274-L407)
- [قواعد المصدر المرجعي الخاص](https://github.com/hamedonassar95/DevObs-ai-Intelligence-/blob/main/firestore.rules) — فُحصت للقراءة فقط؛ هذا لا يثبت أنها نُشرت في Firebase.

أعاد GitHub ملف القواعد المرجعي بمُعرّف blob `31f4dd932e6071783fad2f18defb186183d5c135` من الفرع `main`. هذا مُعرّف محتوى الملف، وليس ادعاءً بأنه commit SHA للمستودع.

## 2. ما الذي يفعّله المصدر الحالي؟

**VERIFIED من المصدر:** لا يُنشأ تطبيق Firebase إلا إذا كان `VITE_FIREBASE_ENABLED` يساوي النص `true` وكانت حقول تهيئة Firebase الستة في الكود غير فارغة. تسمح `VITE_FIRESTORE_DATABASE_ID` باختيار قاعدة مسماة؛ إن لم تُحدد، يستخدم SDK قاعدة Firestore الافتراضية. لم أقرأ أي قيمة من البيئة.

واجهة Firestore لا تستورد الخدمة إلا بعد تفعيل العلم. أما خدمة Google Workspace الاختيارية فتحتاج أيضًا إلى `VITE_GOOGLE_WORKSPACE_ENABLED=true`. غياب علم التفعيل أو أي قيمة غير `true` يجعل الواجهة تتوقف أو تعيد callbacks فارغة. لم أغيّر هذه الأعلام؛ التكامل يبقى معطّلًا.

**تنبيه مصدر مهم:** عند استيراد خدمة Firestore مع التطبيق والتهيئة متاحين، تستدعي الخدمة تلقائيًا `getDocFromServer()` للمسار `test/connection`. لم يحدث هذا الطلب في هذه المراجعة؛ لكنه سلوك يجب أن يدخل في نطاق اختبارات المحاكي قبل التفكير في تفعيل Firebase.

## 3. كيف يعمل تسجيل الدخول؟

**VERIFIED من المصدر:** يوجد مسار تسجيل اختياري عبر Firebase Authentication ومزوّد Google: `signInWithPopup()`، ثم مستمع `onAuthStateChanged()`. يتطلب مسار Google تفعيل Firebase وGoogle Workspace معًا وتهيئة تطبيق Firebase. يحتفظ الكود برمز Google OAuth في الذاكرة لاستخدامات Google Workspace. هذا المسار غير مفعّل افتراضيًا.

لكن `getAuth()` داخل خدمة Firestore لا يسجل المستخدم دخولًا ولا يفرض شرط تسجيل الدخول على دوال القراءة والكتابة. إنه يقرأ حالة المستخدم لاستخدامها في معلومات الخطأ؛ القرار الأمني لخدمة Firestore يجب أن يأتي من Security Rules على الخادم. لا يوجد في أنواع سجلات الخادم أو الحادثة أو النشر حقل `tenantId` أو `ownerId` ظاهر. لذلك لا يثبت تسجيل الدخول وحده أن المستخدم يملك سجلًا أو ينتمي إلى مستأجره.

**حدّ مهم:** لا يوجد في مصدر الواجهة استعمال لـFirebase App Check مثل `initializeAppCheck`. هذا حكم على الملفات المفحوصة فقط؛ حالة App Check في المشروع الحي **UNVERIFIED**. كما أن جلسة Devobs/Keycloak منفصلة عن Firebase Google Auth، ولم أجد دليلًا في هذا المصدر على أنها تُستخدم لتخويل Firestore.

## 4. جرد عمليات القراءة والكتابة والحذف

هذه عمليات عميل موجودة في المصدر، وليست إثباتًا أنها نُفذت على قاعدة حية. `onSnapshot()` يستمع للمجموعة كاملة بلا قيد مستأجر في هذه الخدمة. و`setDoc(..., { merge: true })` ينشئ أو يحدّث سجلًا بالمعرّف المحدد.

| المجموعة | قراءة | إنشاء / تحديث | حذف من عميل Devobs | دليل المصدر |
|---|---|---|---|---|
| `servers` | `onSnapshot(collection('servers'))` | `setDoc(servers/{id}, server, merge: true)` | نعم، `deleteDoc(servers/{id})` | [الخدمة، الأسطر 94–134](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L94-L134) |
| `incidents` | `onSnapshot(collection('incidents'))` | `setDoc(incidents/{id}, incident, merge: true)` | لم أجد دالة حذف في الخدمة أو الواجهة المفحوصة | [الخدمة، الأسطر 136–167](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L136-L167) |
| `deployments` | `onSnapshot(collection('deployments'))` | `setDoc(deployments/{id}, deployment, merge: true)` | لم أجد دالة حذف في الخدمة أو الواجهة المفحوصة | [الخدمة، الأسطر 169–200](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L169-L200) |

**VERIFIED — خطر تفعيل:** رغم تعليق `App.tsx` الذي يقول إن بيانات العرض التجريبي لا تُزرع في Firestore، فإن إجراءات العرض تستدعي دوال الحفظ للحوادث والنشر والخوادم. كما أن حذف خادم من واجهة العرض يستدعي دالة حذف Firestore. إذا فُعّل التكامل مع مشروع حقيقي، قد تكتب هذه الإجراءات سجلات تجريبية أو تحذف سجل Firestore، رغم أن رسائل الواجهة تصف بعض الإجراءات بأنها محاكاة. لم أفعّل التكامل ولم يحدث أي تغيير حي.

**VERIFIED — سلوك الأخطاء:** أخطاء اشتراك القراءة والحفظ تُسجّل كتحذيرات في `console`، ودوال الحفظ لا تعيد الخطأ إلى الواجهة. لذلك لا يكفي نجاح تفاعل العرض أو ظهور رسالة محاكاة لإثبات نجاح كتابة Firestore.

**قاعدة تصميم مستقبلية:** توضح [Firebase أن Security Rules ليست مرشحًا للنتائج](https://firebase.google.com/docs/firestore/security/rules-conditions#rules_are_not_filters)؛ إذا قُيدت القراءة بمستأجر، يجب أن يطابق الاستعلام هذا القيد، وإلا يرفض Firestore الاستعلام. لذلك يلزم تصميم حقول الاستعلام والقاعدة معًا قبل السماح بقراءة tenant-scoped.

## 5. مصفوفة الوصول بأقل صلاحية

لا توجد حاليًا هوية مستأجر أو مالك موثقة في أنواع السجلات المفحوصة. لذلك الموقف الأقل صلاحية قبل اعتماد نموذج ملكية ومراجعة قواعده هو **الرفض**؛ لا تمنح هذه المصفوفة صلاحيات جديدة.

| الممثل | المورد | العملية | المستأجر | المالك | قاعدة التخويل | الدليل | الخطر إذا كانت القواعد القديمة فعّالة |
|---|---|---|---|---|---|---|---|
| زائر غير مسجل | `servers`, `incidents`, `deployments` | قراءة | غير موجود في النوع | غير موجود في النوع | canonical: رفض؛ قديم: `isSignedIn() || true` يسمح | [قواعد Devobs](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/firestore.rules#L1-L10) و[القواعد المرجعية](https://github.com/hamedonassar95/DevObs-ai-Intelligence-/blob/main/firestore.rules) | قراءة مجهولة لأي سجل مطابق وقد تكشف بيانات تشغيلية |
| مستخدم Firebase مسجل | المجموعات الثلاث | قراءة المجموعة | لا يوجد فحص عضوية مستأجر | لا يوجد فحص مالك | canonical: رفض؛ قديم: القراءة مسموحة لأي مستخدم | [اشتراكات المجموعات](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L94-L188) | وصول عابر للمستأجرين |
| مستخدم Firebase مسجل | كل مجموعة | إنشاء سجل | لا يوجد حقل/قيد مستأجر | لا يوجد حقل/قيد مالك | canonical: رفض؛ قديم: تسجيل دخول + صيغة معرّف فقط | `setDoc(..., merge: true)` في [الخدمة](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L114-L196) وشرط `isValidId` في [المرجع](https://github.com/hamedonassar95/DevObs-ai-Intelligence-/blob/main/firestore.rules) | إنشاء بيانات بلا ربط موثوق بهوية أو مستأجر |
| مستخدم Firebase مسجل | كل مجموعة | تحديث سجل قائم | لا يوجد فحص عضوية مستأجر | لا يوجد فحص مالك | canonical: رفض؛ قديم: تسجيل دخول + صيغة معرّف فقط | الدليل نفسه؛ `merge: true` ينشئ أو يحدّث | استبدال أو تغيير سجل مستخدم آخر |
| مستخدم Firebase مسجل | `servers` | حذف سجل | لا يوجد فحص مستأجر | لا يوجد فحص مالك أو دور حذف | canonical: رفض؛ قديم: شرط `allow write` يشمل الحذف | `deleteDoc` في [خدمة العميل](https://github.com/hamedonassar95/Devobs/blob/6cc250a830e776909e5b095d3543e6ffffcb2760/apps/ai-intelligence-console/src/services/firebaseFirestore.ts#L125-L134) | حذف غير مخوّل لسجل خادم |
| مستخدم Firebase مسجل | `incidents`, `deployments` | حذف مباشر من SDK | لا يوجد فحص مستأجر | لا يوجد فحص مالك | canonical: رفض؛ قديم: قد يسمح بالطلب المباشر إذا طابق شرط الكتابة | لا توجد دالة حذف في واجهة التطبيق المفحوصة؛ القاعدة القديمة عامة | تجاوز الواجهة وحذف سجلات خارج أزرار التطبيق |
| عميل غير مسجل | كل مجموعة | إنشاء أو تحديث أو حذف | غير موجود | غير موجود | canonical: رفض؛ قديم: شرط `request.auth != null` يرفض الكتابة | دوال العميل لا تفحص `currentUser` قبل الإرسال؛ القواعد تقرر على الخادم | الطلبات تفشل عند عدم وجود جلسة؛ لا يجوز تحويل ذلك إلى سماح أوسع |

## 6. القواعد canonical مقارنة بالقواعد المرجعية القديمة

**VERIFIED — Devobs عند SHA الأساس:** تحتوي `apps/ai-intelligence-console/firestore.rules` قاعدة واحدة شاملة `allow read, write: if false`. هذا رفض كامل ومقصود حتى تتم مراجعة سياسة منفصلة.

**VERIFIED — المستودع المرجعي الخاص، ملف `firestore.rules` في `main` كما فُحص للقراءة فقط:** توجد قاعدة منع عامة، لكن توجد بعدها قواعد `servers` و`incidents` و`deployments`. كل منها يسمح بالقراءة باستخدام `isSignedIn() || true`؛ الجزء `|| true` يجعل القراءة متاحة حتى بلا تسجيل دخول. وتسمح الكتابة عند تسجيل الدخول وفحص شكل معرّف المستند فقط؛ لا يوجد شرط يطابق المالك أو المستأجر. قاعدة `allow write` الواسعة تشمل الحذف أيضًا.

وجود قاعدة منع عامة لا يلغي قاعدة السماح المطابقة. توضح وثائق Firebase أن سماحًا مطابقًا واحدًا يكفي للسماح بالطلب؛ لذلك لا تُعامل قاعدة deny-all العامة كأنها «تتغلب» على سماحات أخرى. **UNVERIFIED:** لا نعرف هل هذه القواعد القديمة هي القواعد المنشورة حاليًا، ولا نعرف هل تحتوي قاعدة حية بيانات حقيقية.

إذا كانت قواعد شبيهة بالقديمة منشورة، فالمخاطر المحتملة هي قراءة عامة لبيانات الخوادم والحوادث والنشر، وتعديل أو حذف واسع لأي مستخدم مسجل. أنواع البيانات في النموذج تشمل عناوين IP وأنظمة تشغيل، ورسائل أو آثار مكدس للحوادث، واسم مؤلف النشر والخوادم المستهدفة؛ وجود هذه الحقول لا يثبت وجود بيانات حقيقية في Firestore.

## 7. شرح مبسط للمبتدئ

- **Firebase Authentication:** يسجل هوية المستخدم ويقدمها للطلب. تسجيل الدخول يجيب عن «من أنت؟»، ولا يجيب وحده عن «أي سجل يحق لك رؤيته؟».
- **Cloud Firestore:** قاعدة بيانات مستندات ومجموعات. يمكن لتطبيق الويب أن يطلب منها القراءة والكتابة مباشرة عبر SDK؛ لذلك يجب حماية كل طلب على جهة الخادم.
- **Firestore Security Rules:** حارس الخادم الذي يقرر السماح أو الرفض لكل طلب. قواعد الواجهة أو إخفاء زر لا تحمي قاعدة البيانات. القواعد الحالية في Devobs ترفض الجميع.
- **Firebase API key:** معرّف إعداد يحدد مشروع Firebase وواجهات API للعميل. ليس كلمة مرور ولا بديلًا عن Security Rules. يمكن تقييده حسب الواجهات والمواقع، لكن تقييده لا يحل محل تخويل البيانات.
- **App Check:** يساعد على التحقق أن الطلب صادر عن تطبيق أو جهاز متوقع ويقلل بعض إساءة الاستخدام. لا يثبت ملكية المستخدم ولا يحل محل Authentication أو Security Rules.
- **Emulator Suite:** بيئة محلية لاختبار Auth وFirestore والقواعد باستخدام بيانات وهوية اصطناعية. نجاح الاختبار المحلي لا يثبت أن القواعد الحية منشورة أو صحيحة.

### مراجع Firebase الرسمية

- [Firebase Authentication للويب](https://firebase.google.com/docs/auth/web/start)
- [هيكل Firestore Security Rules](https://firebase.google.com/docs/firestore/security/rules-structure)
- [شروط القواعد والتخويل](https://firebase.google.com/docs/firestore/security/rules-conditions)
- [مفاتيح Firebase API](https://firebase.google.com/docs/projects/api-keys)
- [Firebase App Check](https://firebase.google.com/docs/app-check)
- [اختبار Firestore Rules باستخدام Emulator](https://firebase.google.com/docs/firestore/security/test-rules-emulator)

## 8. التحقق المحلي

نُفذت الفحوص التالية في worktree المعزول `feature/firebase-access-inventory` قبل الالتزام. كلها تفحص المصدر المحلي فقط ولا تتصل بـFirebase:

| الأمر | النتيجة | الدليل الفعلي |
|---|---|---|
| `python3 scripts/milestone_ledger.py --summary` | **PASS**, exit 0 | `merged_milestones: 305`, `latest_pr: 747`, `open_gates: 3`; P01 وAI-9=`BLOCKED`, Codex runtime=`OPEN` |
| `python3 scripts/check_firebase_rules_baseline.py` | **PASS**, exit 0 | `{"reason":"CANONICAL_DENY_ALL_BASELINE","scope":"LOCAL_SOURCE_ONLY","status":"PASS"}` |
| `python3 -m unittest discover -s tests -p "test_firebase_rules_baseline.py" -v` | **PASS**, exit 0 | `Ran 7 tests`; `OK` |
| `git diff --check` | **PASS**, exit 0 | لا مخرجات، ولا مسافات بيضاء غير صالحة |
| فحص روابط Markdown المحلية في README والدليل الجديد | **PASS** | كل أهداف الملفات المحلية المشار إليها موجودة |

**NOT RUN:** لم أجد فاحص Markdown أو روابط توثيق مخصصًا ضمن الأدوات الموجودة. فحص الروابط أعلاه اقتصر على الأهداف المحلية للملفين المعدلين؛ لم تُجلب الروابط الخارجية أو تُختبر إعدادات Console. CI الخاص بـPR Phase 2 يجب التحقق منه على SHA النهائي قبل مراجعة المالك.

## 9. الخطوة التنفيذية التالية الوحيدة

**الخطوة التالية: إنشاء اختبارات تخويل Firestore Emulator محلية ببيانات وادعاءات اصطناعية.** يجب أن تغطي رفض القراءة والكتابة للمجهول، ورفض مستخدم من مستأجر آخر، وقبول العمليات المسموحة فقط لهوية مالكة في fixture تجريبي، وحدود الحذف. يجب أن تميّز الاختبارات صراحةً بين نموذج fixture المقترح وبين نموذج الإنتاج غير الموجود بعد. لا تُنشر القواعد ولا يُتصل بمشروع Firebase حي في تلك الخطوة.

## 10. البوابات والحالة

- **VERIFIED:** P01 باقٍ `BLOCKED / NO-GO`، وAI-9 باقٍ `BLOCKED`، وقبول Codex runtime باقٍ `OPEN` بحسب ملخص الدفتر عند SHA الأساس.
- **UNVERIFIED:** حالة قاعدة Firebase المنشورة أو مصادقة أي عميل حقيقي أو حالة App Check ومفاتيح API.
- **BLOCKED عمدًا:** أي استعلام أو تعديل على Firebase حي، نشر قواعد، تفعيل الأعلام، تبديل بيانات اعتماد، تعديل IAM أو فوترة أو استضافة.
- **موافقة المالك المطلوبة:** مراجعة هذا الجرد ورأس PR ونتائج CI قبل أي دمج أو تكامل لاحق. لا يطلب هذا الدليل اعتماد إنتاج.
