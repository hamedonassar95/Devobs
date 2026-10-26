# Devobs CI — فحص التكامل والنشر

المشروع الحالي صفحة HTML ثابتة مع CSS مضمّن؛ لا يحتاج npm أو مرحلة build.

## ما ينفذه CI

- يعمل على كل push إلى أي فرع، وعلى كل Pull Request، ويدعم التشغيل اليدوي والاستدعاء من workflows أخرى. لا توجد مرشحات paths تتجاوز فحص `validate`.
- يحافظ على اسم الفحص `validate` المطلوب في قاعدة `Protect main` الحالية.
- يتحقق من استخدام Python 3.10 أو أحدث، ويجمع ملفات `scripts/` و`tests/` لاكتشاف أخطاء الصياغة.
- يرفض استمرار فحص unittest إذا لم يكتشف أي حالات اختبار.
- يفحص HTML5 doctype وعناصر html/head/body/title/main/h1، والعنوان غير الفارغ.
- يتأكد من اللغة العربية واتجاه RTL وUTF-8 وviewport المتجاوب.
- يرفض IDs المكررة ومراجع aria-labelledby المفقودة وعلامات تعارض الدمج.
- يستخدم `scripts/stage_site.py` لإنشاء `_site` من النسخة التي جرى checkout لها، بعد تسجيل SHA الفعلي من `git rev-parse HEAD` والتحقق من أنه 40 خانة hex صغيرة. يشغّل `scripts/check_site.py` على `_site`، بما فيه اختبار HTTP محلي على loopback. معاينة PR ترفع نفس مجلد `_site` الذي اجتاز الفحص، بما فيه `deployment.json` والأصول المرئية، لمدة 7 أيام؛ إنها أثر قابل للتنزيل وليست نشرًا. Pages وVercel يستخدمان helper staging نفسه لكنهما ينشئان مخرجاتهما بشكل منفصل؛ هذا لا يثبت تطابق digest بايتًا ببايت أو استهلاك نشر Pages/Vercel لأثر CI نفسه. راجع [توثيق Git الرسمي لـ`git rev-parse`](https://git-scm.com/docs/git-rev-parse) و[توثيق GitHub الرسمي لرفع آثار workflow والاحتفاظ بها](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts).
- يفرض تثبيت الإجراءات الخارجية في GitHub Actions على commit SHA كامل، بما يشمل ملفات workflow وملفات lock وقوالب الوكلاء، عبر `scripts/check_action_pins.py`.
- يشغّل Bandit لفحص شيفرة Python، و`pip-audit` لفحص الثغرات المعروفة في الاعتماديات المباشرة والانتقالية المعلنة في `requirements-dev.txt`. يفشل الفحص عند العثور على ثغرة.
- تتحقق Dependabot أسبوعيًا من تحديثات حزم Python وإجراءات GitHub.
- يشغّل خادمًا محليًا مؤقتًا ويتحقق من HTTP 200 ونوع HTML وتطابق المحتوى في / و/index.html.
- يشغّل اختبارات حواجز التحقق، وحالات الحوادث والتعافي، وعقد التحقيق والثقة.
- يختار الاختبارات بحسب الملفات المتغيرة؛ تغييرات workflows والإجراءات المحلية تشغّل اختبارات عقود Python حتى عندما تكون درجة المخاطر متوسطة. إذا تعذّر تحديد فرق موثوق، مثل غياب commit الأساس، يشغّل الفحص الكامل بدل الاعتماد على قائمة ملفات ناقصة من حمولة الحدث.
- ينشئ معاينة HTML قابلة للتنزيل على Pull Requests بعد نجاح الفحوص؛ تُحتفظ بها 7 أيام ولا تنشر إلى الإنتاج.
- يبني صورة اختيارية للموقع الثابت ويختبرها محليًا على loopback؛ لا يرفع الصورة إلى سجل حاويات.
- يفحص صورة الموقع مرة واحدة بواسطة Trivy CLI 0.76.1، ثم يقيّم التقرير ببوابة محلية تفشل مغلقة: أخطاء Trivy أو قاعدة البيانات أو JSON المفقود/المعطوب تفشل المهمة، وHIGH/CRITICAL تمنع نجاح الفحص، بينما تُحسب MEDIUM/LOW/UNKNOWN دون منع النجاح. يُحفظ تقرير JSON كأثر سبعة أيام مع `if-no-files-found: error`. يجري التحقق من SHA256 للأرشيف مقابل ملف checksums المنزّل من إصدار Trivy نفسه؛ هذا تحقق checksum فقط وليس تحققًا مستقلًا من توقيع الإصدار. يستخدم وسم الصورة SHA الكامل من `git rev-parse HEAD` للنسخة التي جرى checkout لها، ويعرض الملخص عدد النتائج فقط وأول 12 خانة من SHA. لا يرفع CI الصورة إلى سجل. مهمة smoke test ومهمة Trivy تبنيان الصورة كلٌ على حدة، لذلك لا يثبت CI تطابق digest بينهما أو سلامة صورة منشورة أو تشغيل حي. راجع [مرجع Trivy الرسمي لخيارات فحص الصور](https://trivy.dev/latest/docs/references/configuration/cli/trivy_image/)، [توثيق Git الرسمي لـ`git rev-parse`](https://git-scm.com/docs/git-rev-parse)، [توثيق Python الرسمي لـ`argparse`](https://docs.python.org/3/library/argparse.html)، [توثيق GitHub الرسمي لأوامر workflow](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-an-environment-variable)، و[احتفاظ GitHub Actions بالآثار](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts#configuring-a-custom-artifact-retention-period-for-an-artifact).
- ينسّق إعداد Terraform ويفحص صحته بعد تهيئة المزوّد دون backend؛ لا ينفذ `plan` أو `apply` ولا يحتاج اعتماد GCP.

تشغيل CI على جميع الفروع لا ينشر إلى الإنتاج: وظيفة النشر الحالية ما زالت مشروطة بدفع ناجح إلى `main` فقط. راجع [أحداث GitHub Actions الرسمية](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

هذه فحوص متطلبات المشروع، وليست مدقق HTML/CSS شاملًا أو اختبار عرض في متصفح أو تدقيق وصول كاملًا. اختبار HTTP يخص الخادم المحلي، ولا يثبت صحة إعدادات الاستضافة أو النشر الفعلي. عند إضافة صفحات أو JavaScript أو عملية build يجب توسيع الفحوص.

## التسليم على دفعات صغيرة

استخدم [قالب Pull Request](../.github/pull_request_template.md) لتحديد هدف واحد وشروط قبوله والسلوك الحالي الذي يجب الحفاظ عليه. ابدأ بالأساس المطلوب، ثم أرسل التحسينات المستقلة في دفعات منفصلة؛ راجع فرق كل دفعة ومعاينتها قبل الانتقال إلى التالية.

عند تغيير الصفحة، نزّل معاينة PR من CI وافحصها على سطح المكتب وعرض هاتف ضيق، ثم تحقق من الروابط والمحتوى الأساسي. بعد الدمج، راجع Deployment Health Check وتأكد من تطابق SHA المنشور مع النسخة التي اجتازت CI. معاينة PR حزمة محلية وليست رابطًا عامًا، كما أن فحص صحة النشر لا يستبدل المراجعة البصرية في المتصفح.

## التشغيل محليًا

من جذر المستودع، باستخدام Python 3.10 أو أحدث:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/check_site.py
```

على Windows يمكن استبدال `python3` بـ `py -3`.

## التحقق والتفعيل

1. افتح PR الخاص بهذا التغيير وافحص تبويب Checks؛ يجب أن ينجح `validate`.
2. الاختبارات المرفقة تتحقق آليًا من رفض صفحات معطوبة دون تغيير صفحة الموقع.
3. لاختبار الحماية يدويًا: في فرع تجريبي وPR منفصل، احذف doctype من index.html؛ يجب أن يفشل validate ويمنع الدمج. أعد السطر وتحقق من نجاح التشغيل الجديد. لا تدمج نسخة الاختبار المعطوبة.
4. ادمج PR التحسين بعد مراجعته؛ يعمل الفحص تلقائيًا على main. بعد الدمج يتاح Actions → CI → Run workflow.
5. لا تغيّر اسم validate ولا تضف مرشحات paths تتخطى الفحص المطلوب.

لا تحتاج اختبارات unittest إلى حزم Python خارجية. أدوات الفحص الأمني مثبتة بإصدارات محددة في `requirements-dev.txt`؛ يستخدم `pip-audit --requirement requirements-dev.txt` صيغة ملف المتطلبات الموثقة في [دليل pip-audit الرسمي](https://github.com/pypa/pip-audit#usage). يتطلب تدقيق الثغرات الوصول إلى مصدر بيانات الثغرات عبر الشبكة. لا يلزم Secret أو خدمة مدفوعة لهذا الفحص؛ يلزم السماح بـ GitHub Actions وGitHub-hosted runners وactions/checkout. لا يحتاج إعداد حماية الفرع الحالي إلى تعديل.

للتفاصيل وحدود كل فحص أمني، راجع [دليل DevSecOps](DEVSECOPS.md).

## اعتماد GitHub في workflows المولدة

تُولّد ملفات `*.lock.yml` التالية من ملفات Markdown المقابلة عبر GitHub Agentic Workflows؛ عدّل المصدر ثم أعد التوليد، ولا تعدّل ملف lock يدويًا:

- `efficiency-improver.md`
- `incident-investigator.md`
- `incident-investigator-claude.md`
- `incident-investigator-vertex.md`
- `phase8b-ai-patch-generator.md`

تعتمد إجراءات GitHub التي يضيفها المترجم على إصدار `gh-aw` المثبت. لتحديثها، ثبّت إصداراً محدداً من الامتداد الرسمي ثم أعد توليد المصادر الخمسة:

```sh
gh extension install github/gh-aw --force --pin v0.92.0
gh aw compile --no-check-update --force-refresh-action-pins --validate \
  efficiency-improver incident-investigator incident-investigator-claude \
  incident-investigator-vertex phase8b-ai-patch-generator
```

تغييرات Dependabot على ملفات lock وحدها لا تعني أن المصدر المولد تغير؛ إعادة التوليد بإصدار مترجم أقدم قد تعيد الإصدارات القديمة. راجع إصدار المترجم وكل SHA في الناتج قبل الدمج. خطوة `Checkout repository` المضافة تلقائيًا في مسار المخرجات الآمنة تحفظ اعتماد GitHub عمدًا لأن إنشاء فرع وطلب سحب مسودة يحتاج إلى دفع commit. الخطوة مشروطة بنوع مخرج `create_pull_request`، والمخرجات محدودة بطلب واحد ومسارات ملفات مسموح بها في المصدر. عند تغيير هذا التصميم، أعد النظر في الاعتماد المحفوظ، واستخدم أقل صلاحيات ممكنة للرمز المخصص.

أما checkout في `aws.yml` فيستخدم مصادقة AWS عبر OIDC بعد النسخ ولا يحتاج اعتماد GitHub محفوظًا؛ لذلك يعطل `persist-credentials`.

ملف `CODEOWNERS` يوجّه التغييرات إلى المالك للمراجعة. لجعل هذه المراجعة شرطًا قبل الدمج، فعّل **Require review from Code Owners** في قواعد حماية الفرع `main`.

## نقطة البداية التي تم التحقق منها — لقطة تاريخية (5 أكتوبر 2026)

سجل تاريخي: في 5 أكتوبر 2026 كان CI موجودًا أصلًا في `.github/workflows/ci.yml`، وآخر تشغيل مرصود على main عند commit `6b340e24faa8a498c96244deebb5002e77159ee4` ناجح:
https://github.com/hamedonassar95/Devobs/actions/runs/37334898335

وفي ذلك التاريخ كانت قاعدة Protect main مفعلة وتتطلب `validate` من GitHub Actions؛ هذا التغيير طوّر الفحص الموجود. هذه اللقطة لا تصف الحالة الحالية؛ راجع [تقرير جاهزية Devobs الحالي](DEVOBS_READINESS_CURRENT.md) للأدلة المؤرخة على SHA أحدث.

## تحديث المرحلة 4 — 6 أكتوبر 2026

أضيفت معاينة HTML قابلة للتنزيل بعد نجاح PR، مع احتفاظ 7 أيام، وشروط أكثر تحديدًا لمسار الإنتاج. راجع [ضوابط المعاينة والنشر والرجوع](DEPLOYMENT.md). وصف «هذا التغيير لا يضيف نشرًا آليًا» أعلاه يوثق تحسين CI القديم فقط؛ المستودع الآن يحتوي workflow مستقلًا للنشر بعد نجاح CI.
