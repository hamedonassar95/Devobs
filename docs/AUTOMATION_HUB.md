# مركز الأتمتة وسير التشغيل الموحد

هذه الصفحة هي نقطة البدء لمتابعة أتمتة Devobs والمشاريع المرتبطة بها. هي فهرس وروابط تشغيل؛ لا تنسخ الشيفرات أو الأسرار من مستودع إلى آخر.

## القرار التنظيمي

- يبقى `Devobs` المستودع المركزي لفهرسة عمليات DevOps الخاصة به، والتحقق من شيفرته، ونشر موقع GitHub Pages التابع له.
- يبقى كل تطبيق أو مكتبة في مستودع مستقل، مع مصدر حقيقة وسجل تغييرات وسير عمل يخصه.
- لكل عملية مسار تلقائي أساسي واحد. استخدم التشغيل اليدوي عند الحاجة الموثقة فقط، ولا تعِد تشغيل المسار نفسه لمجرد أن خطوة لاحقة ما زالت تعمل.
- لا يعني ظهور مشروع في هذا الفهرس أنه متصل آليًا أو جاهز للإنتاج؛ حالة الاتصال تُثبت بنتيجة فحص فعلية.

## خريطة المستودعات

| المجال | المستودع | الاستخدام وحدود المسؤولية |
| --- | --- | --- |
| مركز الأتمتة | [Devobs](https://github.com/hamedonassar95/Devobs) | CI، فحص النشر، والاستجابة للحوادث. Pages ينشر حاليًا `index.html` من جذر المستودع فقط؛ لا ينشر `devobs/index.html`. |
| مكتبة سكربتات مرجعية | [DevOps-Bash-tools](https://github.com/hamedonassar95/DevOps-Bash-tools) | نسخة Fork عامة لمكتبة سكربتات. تُراجع السكربتات المطلوبة قبل استخدامها؛ لا تُنسخ المكتبة كاملة إلى Devobs. |
| بوابة وكلاء الذكاء الاصطناعي | [unity-gateway](https://github.com/hamedonassar95/unity-gateway) | مشروع Fork منفصل للتجربة والتقييم؛ ليس جزءًا من نشر Devobs الحالي. |
| تطبيق صيانة الهواتف | [phone-repair-assistant-v2](https://github.com/hamedonassar95/phone-repair-assistant-v2) | تطبيق مستقل وخاص. تبقى بيانات العملاء وأسراره وإصداراته في مستودعه. |
| موقع الخدمات | [al-dala-mobile](https://github.com/hamedonassar95/al-dala-mobile) | مستودع مستقل بوصف موقع الخدمات. جرد الملفات الحالي أظهر `README.md` فقط؛ لا يوجد نشر مستقل مثبت. صفحة Pages التجريبية الحالية تُبنى من الملف `index.html` في جذر مستودع `Devobs`، لذلك لا يوجد حتى الآن مسار نشر مستقل مثبت لهذا الموقع. |
| أمثلة وتعلّم | [skills-introduction-to-github](https://github.com/hamedonassar95/skills-introduction-to-github)، [Spoon-Knife](https://github.com/hamedonassar95/Spoon-Knife)، [Next.js](https://github.com/hamedonassar95/Next.js) | أمثلة أو قوالب تعليمية؛ لا تُعامل كأنها أتمتة إنتاجية متصلة. |

مشاريع Fork الأخرى، مثل `browser-compat-data` و`edwards25519` و`opensource.guide` و`pyperformance` و`remix-project` و`sentry-docs` و`server`، تبقى منفصلة عن مسارات التشغيل الخاصة بـDevobs.

## المسار الأساسي للنشر والاستجابة

| الغرض | المسار المعتمد | متى يُستخدم |
| --- | --- | --- |
| التحقق من تغيير Devobs | [CI](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml) | تلقائيًا مع الدفع إلى `main` وطلبات الدمج. هذا هو فحص الشيفرة الأساسي. |
| النشر المعتاد لـPages | [Deploy Pages](https://github.com/hamedonassar95/Devobs/actions/workflows/deploy-pages.yml) | تلقائيًا بعد نجاح CI لآخر تغيير على `main`. لا تطلق نشرًا ثانيًا يدويًا لنفس التغيير. |
| التحقق من الموقع المنشور | [Deployment Health Check](https://github.com/hamedonassar95/Devobs/actions/workflows/deployment-health-check.yml) | يبدأ بعد النشر تلقائيًا؛ شغّله يدويًا فقط لفحص مطلوب أو تحقيق عطل. |
| فرز فشل CI أو النشر | [Incident Response](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-response.yml) | يتابع فشل المسارات المحددة ويجمع الأدلة؛ لا يغيّر الشيفرة ولا ينشرها. |
| تحقيق AI في حادثة | [Incident Investigator — Copilot](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator.lock.yml) | المسار الأساسي للتحقيق. استخدم [Claude](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator-claude.lock.yml) أو [Vertex](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator-vertex.lock.yml) يدويًا فقط بعد فشل المسار الأساسي والتأكد من عدم وجود تقرير للحادثة. |
| فحص بيانات مزوّدي AI | [AI Provider Preflight](https://github.com/hamedonassar95/Devobs/actions/workflows/ai-provider-preflight.yml) | تشغيل يدوي للتحقق من الإعداد والمصادقة؛ لا يرسل طلبًا إلى نموذج AI. |
| نشر نسخة محددة | [One-click deploy](https://github.com/hamedonassar95/Devobs/actions/workflows/one-click-deploy.yml) | حالة استثنائية تتطلب اختيار النسخة وتأكيدًا صريحًا؛ ليس بديلًا للنشر التلقائي المعتاد. |
| استعادة إصدار Pages | [Rollback Pages](https://github.com/hamedonassar95/Devobs/actions/workflows/rollback-pages.yml) | استعادة يدوية عند الحاجة، وفق [دليل التراجع](RELEASE_ROLLBACK.md). |

كل من `Deploy Pages` و`One-click deploy` و`Rollback Pages` يستخدم مجموعة التزامن `github-pages`، لذلك لا تعمل عمليات النشر والتراجع بالتوازي. اترك العملية الحالية تنتهي قبل طلب عملية أخرى.

## عمليات يدوية منفصلة

هذه العمليات ليست جزءًا من النشر المعتاد؛ شغّل الواحدة المطلوبة فقط بعد مراجعة مدخلاتها:

- [Efficiency Improver](https://github.com/hamedonassar95/Devobs/actions/workflows/efficiency-improver.lock.yml): تجربة AI يدوية محدودة، تنتج بحد أقصى PR مسودة واحدًا.
- [Amazon ECS](https://github.com/hamedonassar95/Devobs/actions/workflows/aws.yml): نشر منفصل إلى AWS، لا يبدأ دون تأكيد صريح.
- [Facebook Page post](https://github.com/hamedonassar95/Devobs/actions/workflows/facebook-post.yml): نشر رسالة عامة، لا يبدأ دون تأكيد صريح.
- [Phase 8 Read-Only Evidence](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-readonly-evidence.yml)، [Contract Live Gate](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-contract-live-gate.yml)، و[Live Policy Evaluation](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-live-policy.yml): فحوص يدوية لحادثة محددة.
- [Phase 8B AI Patch Generator](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8b-ai-patch-generator.lock.yml) و[Isolated Patch Publisher](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8b-patch-publisher.yml): مسار استعادة مضبوط؛ إنشاء المسودة ونشرها مرحلتان منفصلتان، ولا يدمج أو ينشر إلى الإنتاج تلقائيًا.

## قواعد منع تكرار العمل

1. **تغيير عادي:** افتح PR؛ يتولى CI الفحص، وبعد الدمج إلى `main` يتولى Deploy Pages النشر ثم فحص الصحة. لا تعِد تشغيل الخطوات يدويًا إذا نجحت.
2. **حادثة واحدة:** استخدم محققًا واحدًا لكل رقم حادثة. لا تشغّل Copilot وClaude وVertex معًا؛ البدائل مخصصة عند تعطل المسار الأساسي فقط.
3. **إعداد AI:** شغّل Preflight أولًا. نجاحه يثبت المصادقة والإعداد فقط، ولا يثبت جودة نتيجة النموذج أو توفر الحصة.
4. **مشروع آخر:** التغيير والنشر والاختبارات تخص مستودع ذلك المشروع. لا تجعل CI في Devobs يعيد بناء تطبيق الهاتف. قبل تطوير موقع الخدمات، حدّد مستودعًا واحدًا كمصدر حقيقة؛ حاليًا صفحة Pages التجريبية موجودة في الملف `index.html` في جذر `Devobs`، بينما `al-dala-mobile` لا يحتوي إلا على README في المستوى الرئيسي.
5. **السكربتات الخارجية:** ارجع إلى النسخة الأصلية عند الحاجة؛ لا تنشئ نسخًا متفرقة منها داخل أكثر من مستودع.

## صفحات التشغيل

- [GitHub Actions في Devobs](https://github.com/hamedonassar95/Devobs/actions)
- [خطة منظومة المشاريع](PROJECT_ECOSYSTEM_EXECUTION_PLAN.md)
- [سجل القبول والنتائج المقاسة](INVESTIGATOR_ACCEPTANCE.md)
- [التوثيق العام للتشغيل والنشر](DEPLOYMENT.md)

لا تُكتب قيمة مفتاح أو رمز وصول في هذا المستند. تُراجع جاهزية الأسرار عبر Preflight وسجل التشغيل؛ GitHub لا يعرض القيمة المحفوظة للسر بعد إنشائه.
