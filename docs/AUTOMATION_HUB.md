# مركز الأتمتة وسير التشغيل الموحد

هذه الصفحة هي نقطة البدء لمتابعة أتمتة Devobs والمشاريع المرتبطة بها. هي فهرس وروابط تشغيل؛ لا تنسخ الشيفرات أو الأسرار من مستودع إلى آخر.

## القرار التنظيمي

- `Devobs` هو مركز فهرسة وأتمتة: يوفر وحدات CI قابلة لإعادة الاستخدام لمستودعات متعددة، ويدير فحوصه ونشر موقعه الخاص.
- يوفر أيضًا إعداد AI DevKit مشتركًا للمساهمين في [Codex وClaude Code](AI_DEVKIT.md)، مع قالب لتطبيق سير التطوير نفسه في مستودع آخر.
- يبقى كل تطبيق أو مكتبة في مستودع مستقل، مع مصدر حقيقة وسجل تغييرات وسير عمل يخصه.
- لكل عملية مسار تلقائي أساسي واحد. استخدم التشغيل اليدوي عند الحاجة الموثقة فقط، ولا تعِد تشغيل المسار نفسه لمجرد أن خطوة لاحقة ما زالت تعمل.
- لا يعني ظهور مشروع في هذا الفهرس أنه متصل آليًا أو جاهز للإنتاج؛ حالة الاتصال تُثبت بنتيجة فحص فعلية.

## خريطة المستودعات

| المجال | المستودع | الاستخدام وحدود المسؤولية |
| --- | --- | --- |
| مركز الأتمتة ووحدات CI المشتركة | [Devobs](https://github.com/hamedonassar95/Devobs) | فهرس وحدات CI المشتركة لـBash وNode.js وPython وPHP/Composer، بالإضافة إلى CI وفحص النشر والاستجابة للحوادث الخاصة بـDevobs. Pages ينشر `index.html` من جذر المستودع فقط؛ لا ينشر `devobs/index.html`. |
| مكتبة سكربتات مرجعية | [DevOps-Bash-tools](https://github.com/hamedonassar95/DevOps-Bash-tools) | نسخة Fork عامة لمكتبة سكربتات تستدعي [وحدة Bash CI المشتركة](https://github.com/hamedonassar95/DevOps-Bash-tools/blob/main/.github/workflows/shellcheck.yaml) من Devobs على SHA ثابت؛ تفحص ملفات `.sh` المتغيرة في PR/push وتتيح فحص المكتبة كاملة يدويًا. تُراجع السكربتات المطلوبة قبل استخدامها؛ لا تُنسخ المكتبة كاملة إلى Devobs. |
| بوابة وكلاء الذكاء الاصطناعي | [unity-gateway](https://github.com/hamedonassar95/unity-gateway) | مشروع Fork منفصل للتجربة والتقييم؛ ليس جزءًا من نشر Devobs الحالي. |
| تطبيق صيانة الهواتف | [phone-repair-assistant-v2](https://github.com/hamedonassar95/phone-repair-assistant-v2) | تطبيق مستقل وخاص. يستدعي [CI الخاص به](https://github.com/hamedonassar95/phone-repair-assistant-v2/blob/main/.github/workflows/ci.yml) وحدة Node.js المشتركة من Devobs على SHA ثابت ([PR #4](https://github.com/hamedonassar95/phone-repair-assistant-v2/pull/4)). تبقى بيانات العملاء والأسرار وإصدارات التطبيق في مستودعه. |
| موقع الخدمات | [al-dala-mobile](https://github.com/hamedonassar95/al-dala-mobile) | مستودع مستقل بوصف موقع الخدمات. جرد الملفات الحالي أظهر `README.md` فقط؛ لا يوجد نشر مستقل مثبت. صفحة Pages التجريبية الحالية تُبنى من الملف `index.html` في جذر مستودع `Devobs`، لذلك لا يوجد حتى الآن مسار نشر مستقل مثبت لهذا الموقع. |
| أمثلة وتعلّم | [skills-introduction-to-github](https://github.com/hamedonassar95/skills-introduction-to-github)، [Spoon-Knife](https://github.com/hamedonassar95/Spoon-Knife)، [Next.js](https://github.com/hamedonassar95/Next.js) | أمثلة أو قوالب تعليمية؛ لا تُعامل كأنها أتمتة إنتاجية متصلة. |

مشاريع Fork الأخرى، مثل `browser-compat-data` و`edwards25519` و`opensource.guide` و`pyperformance` و`remix-project` و`sentry-docs` و`server`، تبقى منفصلة عن مسارات التشغيل الخاصة بـDevobs. `server` هو fork لتطبيق Nextcloud Server؛ استفدنا من أفكار تنظيم فحوص PHP فيه، بينما تبقى شيفرة الخادم نفسها خارج Devobs.

## المسار الأساسي للنشر والاستجابة

المسار المعتاد يعمل ضمن **تشغيل CI واحد**. يحلل `change-analysis` الملفات المتغيرة وحجم الفرق وتكرار تغييرات الملفات خلال آخر 90 يومًا، ثم يختار فحوص Python وNode المناسبة ويعرض تقدير مخاطر قابلًا للتفسير. يبقى فحص الأمان وعقد الموقع مطلوبين دائمًا. التقدير حتمي واستشاري، ولا يتصل بنموذج AI خارجي أو يمنع النشر بمفرده. يقلل هذا العمل المكرر وزمن الاختبارات غير المرتبطة؛ ولا يغيّر حجم الـrunner المستضاف.

للخدمات التي لديها مقاييس CPU والذاكرة، يوفر Devobs أيضًا [إجراء توصية السعة](RESOURCE_OPTIMIZATION.md). يحسب زيادة أو تخفيضًا أفقيًا محدودًا اعتمادًا على المئين 95 وحدود المشروع وفترة التهدئة. الإجراء يعرض توصية فقط ولا يملك صلاحية تعديل موارد السحابة؛ على كل مشروع وصل مصدر المقاييس ومهايئ منصته بعد مراجعة الميزانية والصلاحيات. لا ينطبق التحجيم على موقع Pages الثابت نفسه.

بعد نجاح الفحوص على دفعة إلى `main`، يستدعي CI مسار `Deploy Pages` القابل لإعادة الاستخدام، ثم فحص `Deployment Health Check` ضمن التشغيل نفسه. النشر يرفض SHA قديمًا إذا تقدّم `main` أثناء الفحوص، ويفحص الصحة أن النسخة الحية تطابق SHA الذي جرى التحقق منه. عند فشل فحص الإصدار الجديد، يحاول المسار استعادة SHA المنشور السابق بعد التأكد أنه سلف للـ`main` الحالي واجتيازه فحوص الاستعادة؛ يتوقف إذا تعذّر إثبات ذلك. طلبات الدمج تنتج معاينة قابلة للتنزيل ولا تنشر إلى الإنتاج. التشغيلات تستخدم runner مستضافًا قياسيًا (`ubuntu-24.04`)؛ لا يوجد runner مخصص معرف في ملفات Actions.

| الغرض | المسار المعتمد | متى يُستخدم |
| --- | --- | --- |
| فحص التغيير والنشر والتحقق | [CI](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml) | المسار التلقائي الأساسي؛ تشغيل واحد من الفحوص إلى التحقق بعد النشر. |
| CI مشترك لمشاريع Node.js/npm | [Reusable Node.js CI](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/reusable-node-ci.yml) | يستعيد ذاكرة npm، يثبت `package-lock.json` بواسطة `npm ci`، ثم يشغّل `test` و`lint` و`typecheck` و`build` إذا كانت معرفة في `package.json`. |
| CI مشترك لمشاريع Python | [Reusable Python CI](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/reusable-python-ci.yml) | يجهز إصدار Python، يدعم تخزين pip المؤقت عند تحديد ملف المتطلبات، ثم يترجم المسارات ويشغّل `unittest` أو `pytest` حسب إعداد المشروع. |
| CI مشترك لمشاريع PHP/Composer | [Reusable PHP CI](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/reusable-php-ci.yml) | يجهز PHP وComposer، يخزن تنزيلات Composer مؤقتًا، يتحقق من `composer.json` و`composer.lock`، ويفحص ثغرات الاعتماديات. يشغّل سكربتات الاختبار وlint التي يحددها المشروع؛ وفي PR يتجاوز التشغيل المكلف للتغييرات الوثائقية فقط، مع الرجوع للفحص الكامل عند تعذر كشف التغيير. |
| توصية سعة الحمل | [Capacity recommendation action](https://github.com/hamedonassar95/Devobs/tree/main/.github/actions/capacity-recommendation) | إجراء مشترك يقرأ ملف مقاييس JSON حديثًا ويعطي قرارًا مفسرًا ضمن حد أدنى وأعلى وعدد زيادة أقصى وفترة تهدئة. لا يتصل بمزود سحابي ولا يطبّق التغيير؛ اربط المخرجات بمهايئ خاص بالمشروع وفق [الدليل](RESOURCE_OPTIMIZATION.md). |
| فحص Bash التلقائي | [ShellCheck](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/shellcheck.yml) | يستدعي CI المشترك محليًا ويفحص كل سكربتات Bash عند تعديل `.sh` أو إعدادات الفحص، مع مستوى `warning`. |
| CI مشترك لسكربتات Bash | [Reusable Bash CI](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/reusable-bash-ci.yml) | يشغّل ShellCheck بوضع Bash لفحص الصياغة والأنماط بمستوى `warning` افتراضيًا. يفحص كل ملفات `.sh` المتتبعة افتراضيًا، ويقبل فحص الملفات المتغيرة في PR/push لتسريع CI أو قائمة صريحة؛ ولا ينفذ السكربتات أو يحتاج أسرارًا. |
| وحدة النشر القابلة لإعادة الاستخدام | [Deploy Pages](https://github.com/hamedonassar95/Devobs/actions/workflows/deploy-pages.yml) | يستدعيها CI بعد نجاح جميع الفحوص؛ لا تشغلها منفردة. |
| فحص صفحة استعادة Pages | [Rollback target quality check](https://github.com/hamedonassar95/Devobs/blob/main/.github/workflows/rollback-quality-check.yml) | يفحص HTML من SHA السابق كبيانات باستخدام validator موثوق قبل أن يسمح مسار النشر باستعادته. |
| وحدة فحص الموقع | [Deployment Health Check](https://github.com/hamedonassar95/Devobs/actions/workflows/deployment-health-check.yml) | يستدعيها النشر تلقائيًا، وتبقى متاحة أيضًا للفحص اليدوي. |
| تدقيق انحراف سياسة الفرع | [Repository policy audit](https://github.com/hamedonassar95/Devobs/actions/workflows/repository-policy-audit.yml) | فحص أسبوعي ويدوي للقراءة فقط يراجع حماية الفرع الافتراضي وruleset و`validate` وقواعد CodeQL؛ يرصد الانحراف ولا يغيّر إعدادات GitHub. |
| فرز فشل CI أو فحص يدوي | [Incident Response](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-response.yml) | يتابع فشل CI وفحص الصحة اليدوي ويجمع الأدلة؛ لا يغيّر الشيفرة ولا ينشرها. |
| تحقيق AI في حادثة | [Incident Investigator — Copilot](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator.lock.yml) | Copilot هو المسار الأساسي. عند فشل استدعائه، يطلق [قاطع مزوّد AI](https://github.com/hamedonassar95/Devobs/actions/workflows/ai-provider-circuit-breaker.yml) مسار [Vertex](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator-vertex.lock.yml) تلقائيًا مرة واحدة للحادثة. استخدم Vertex يدويًا فقط إذا لم يبدأ المسار الآلي بعد فحص تشغيلاته، واستخدم [Claude](https://github.com/hamedonassar95/Devobs/actions/workflows/incident-investigator-claude.lock.yml) يدويًا عند الحاجة؛ تحقق دائمًا من عدم وجود تقرير قبل تشغيل بديل. |
| فحص بيانات مزوّدي AI | [AI Provider Preflight](https://github.com/hamedonassar95/Devobs/actions/workflows/ai-provider-preflight.yml) | تشغيل يدوي للتحقق من الإعداد والمصادقة؛ لا يرسل طلبًا إلى نموذج AI. |
| نشر نسخة محددة | [One-click deploy](https://github.com/hamedonassar95/Devobs/actions/workflows/one-click-deploy.yml) | حالة استثنائية تتطلب اختيار النسخة وتأكيدًا صريحًا؛ ليس بديلًا للنشر التلقائي المعتاد. |
| استعادة إصدار Pages | [Rollback Pages](https://github.com/hamedonassar95/Devobs/actions/workflows/rollback-pages.yml) | استعادة يدوية عند الحاجة، وفق [دليل التراجع](RELEASE_ROLLBACK.md). |

تستخدم وحدات النشر المعتاد و`One-click deploy` و`Rollback Pages` مجموعة التزامن `github-pages`، لذلك لا تعمل عمليات النشر والتراجع بالتوازي. الاستعادة التلقائية تخص ملف Pages الثابت فقط؛ لا تعكس تغييرات قاعدة بيانات أو خدمات خارجية.

## عمليات يدوية منفصلة

هذه العمليات ليست جزءًا من النشر المعتاد؛ شغّل الواحدة المطلوبة فقط بعد مراجعة مدخلاتها:

- [Efficiency Improver](https://github.com/hamedonassar95/Devobs/actions/workflows/efficiency-improver.lock.yml): تجربة AI يدوية محدودة، تنتج بحد أقصى PR مسودة واحدًا.
- [Amazon ECS](https://github.com/hamedonassar95/Devobs/actions/workflows/aws.yml): نشر منفصل إلى AWS، لا يبدأ دون تأكيد صريح.
- [Facebook Page post](https://github.com/hamedonassar95/Devobs/actions/workflows/facebook-post.yml): نشر رسالة عامة، لا يبدأ دون تأكيد صريح.
- [Phase 8 Read-Only Evidence](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-readonly-evidence.yml)، [Contract Live Gate](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-contract-live-gate.yml)، و[Live Policy Evaluation](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8-live-policy.yml): فحوص يدوية لحادثة محددة.
- [Phase 8B AI Patch Generator](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8b-ai-patch-generator.lock.yml) و[Isolated Patch Publisher](https://github.com/hamedonassar95/Devobs/actions/workflows/phase8b-patch-publisher.yml): مسار استعادة مضبوط؛ إنشاء المسودة ونشرها مرحلتان منفصلتان، ولا يدمج أو ينشر إلى الإنتاج تلقائيًا.

## قواعد منع تكرار العمل

1. **تغيير عادي:** افتح PR؛ يتولى CI الفحوص المتوازية. بعد الدمج إلى `main` يتولى تشغيل CI نفسه النشر ثم فحص الصحة. لا تعِد تشغيل الخطوات يدويًا إذا نجحت.
2. **حادثة واحدة:** استخدم محققًا واحدًا لكل رقم حادثة. لا تشغّل Copilot وClaude وVertex معًا؛ البدائل مخصصة عند تعطل المسار الأساسي فقط.
3. **إعداد AI:** شغّل Preflight أولًا. نجاحه يثبت المصادقة والإعداد فقط، ولا يثبت جودة نتيجة النموذج أو توفر الحصة.
4. **مشروع آخر:** تبقى شيفرة المشروع ونشره في مستودعه، ويمكنه استدعاء وحدة CI المناسبة من Devobs عبر `workflow_call`. يحدد المستودع المستهلك إعداداته واختباراته، ويثبت استدعاءه على commit SHA كامل. لا تمرر الأسرار إلى وحدات CI المشتركة؛ هذه الوحدات لا تحتاجها. قبل تطوير موقع الخدمات، حدّد مستودعًا واحدًا كمصدر حقيقة؛ حاليًا صفحة Pages التجريبية موجودة في الملف `index.html` في جذر `Devobs`، بينما `al-dala-mobile` لا يحتوي إلا على README في المستوى الرئيسي.
5. **السكربتات الخارجية:** ارجع إلى النسخة الأصلية عند الحاجة؛ لا تنشئ نسخًا متفرقة منها داخل أكثر من مستودع.
6. **سياسة المستودع:** راجع نتيجة Repository policy audit الأسبوعية؛ أصلح أي انحراف يدويًا في GitHub Settings بعد المراجعة، ولا تحوّل هذا الفحص إلى كاتب آلي للإعدادات.

## اعتماد الوحدات في مشروع آخر

في مستودع المستهلك، أنشئ workflow صغيرًا يستدعي الوحدة المطلوبة بمسار `uses` كامل مثبت على SHA من مستودع Devobs، ثم مرر الإعدادات عبر `with`. لا تستخدم `secrets: inherit`. تنفذ الوحدة checkout لمستودع المستهلك، وتملك صلاحية `contents: read` فقط. للمشروع الجديد، اختر وحدة حسب بيئته؛ لا تستدعِ CI الخاص بـDevobs لأنه يشغّل فحوص الموقع والنشر والحوادث الخاصة بهذا المستودع.

مثال Node.js (استبدل `<DEVOBS_SHA>` بمعرّف commit كامل):

```yaml
jobs:
  validate:
    permissions:
      contents: read
    uses: hamedonassar95/Devobs/.github/workflows/reusable-node-ci.yml@<DEVOBS_SHA>
    with:
      node_version: "22"
      working_directory: .
```

مثال Python:

```yaml
jobs:
  validate:
    permissions:
      contents: read
    uses: hamedonassar95/Devobs/.github/workflows/reusable-python-ci.yml@<DEVOBS_SHA>
    with:
      python_version: "3.12"
      requirements_file: requirements.txt
      test_runner: pytest
      test_path: tests
```

مثال PHP/Composer:

```yaml
jobs:
  validate:
    permissions:
      contents: read
    uses: hamedonassar95/Devobs/.github/workflows/reusable-php-ci.yml@<DEVOBS_SHA>
    with:
      php_version: "8.3"
      working_directory: backend
      composer_test_script: test
      composer_lint_script: lint
```

تعمل مراجعة Composer audit افتراضيًا. غيّر أسماء سكربتات Composer لتطابق `composer.json` في مشروعك، أو مرّر قيمة فارغة لتعطيل سكربت اختياري. عند PR لا تُشغّل فحوص PHP إذا تغيّرت الوثائق وحدها؛ أما push والتشغيل اليدوي وأي فشل في تحديد الملفات فيؤدي إلى فحص كامل حفاظًا على التغطية.

مثال Bash (يفحص ملفات `.sh` المتغيرة في PR/push؛ استخدم `all` للفحص الكامل):

```yaml
jobs:
  bash-ci:
    permissions:
      contents: read
    uses: hamedonassar95/Devobs/.github/workflows/reusable-bash-ci.yml@<DEVOBS_SHA>
    with:
      working_directory: .
      scan_mode: changed
      shellcheck_severity: warning
```

كل مشروع يحدد ملف الاعتمادات ومشغّل الاختبارات المناسبين. وحدة Bash تفحص الصياغة والأنماط فقط ولا تنفذ السكربتات؛ تبقى الاختبارات السلوكية الخاصة بالمشروع في مستودعه. لا تفترض الوحدات وجود مفاتيح Supabase أو اعتماد سحابي. يحتفظ المستودع المستهلك بأسراره وإعدادات النشر الخاصة به؛ أضف وحدة جديدة إلى Devobs عند وجود نمط متكرر ومراجَع عبر أكثر من مشروع.

إذا كان فرع محمي يتطلب اسم فحص قديمًا مثل `validate`، اجعل استدعاء الوحدة في job منفصل، ثم أبقِ job تجميعيًا بالاسم المطلوب ينتظر نجاحها. لا تعتمد على اسم الفحص الداخلي للوحدة لتلبية قواعد فرع لم تُراجع.

## صفحات التشغيل

- [GitHub Actions في Devobs](https://github.com/hamedonassar95/Devobs/actions)
- [خطة منظومة المشاريع](PROJECT_ECOSYSTEM_EXECUTION_PLAN.md)
- [سجل القبول والنتائج المقاسة](INVESTIGATOR_ACCEPTANCE.md)
- [التوثيق العام للتشغيل والنشر](DEPLOYMENT.md)

لا تُكتب قيمة مفتاح أو رمز وصول في هذا المستند. تُراجع جاهزية الأسرار عبر Preflight وسجل التشغيل؛ GitHub لا يعرض القيمة المحفوظة للسر بعد إنشائه.
