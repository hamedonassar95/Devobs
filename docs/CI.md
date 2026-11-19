# Devobs CI — فحص التكامل والنشر

الموقع المنشور صفحة HTML ثابتة مع CSS مضمّن ولا يحتاج npm أو مرحلة build. يوجد أيضًا تطبيق React اختياري مستقل تحت `apps/ai-intelligence-console/`؛ CI يختار له فحوص npm منفصلة عندما تتغير ملفاته، ولا يضيفه إلى أثر GitHub Pages.

## ما ينفذه CI

- يعمل على كل push إلى أي فرع، وعلى كل Pull Request، ويدعم التشغيل اليدوي والاستدعاء من workflows أخرى. لا توجد مرشحات paths تتجاوز فحص `validate`.
- يحافظ على اسم الفحص `validate` المطلوب في قاعدة `Protect main` الحالية.
- يختار فحوص Node الحالية حسب مسارات التغيير؛ أي تغيير داخل `apps/ai-intelligence-console/` يشغّل `npm ci` وتدقيق الاعتماديات بـ`npm audit` ثم الاختبارات وTypeScript وفحص بناء Vite من مجلد التطبيق باستخدام Node.js 24.
- يتحقق من استخدام Python 3.10 أو أحدث، ويجمع ملفات `scripts/` و`tests/` لاكتشاف أخطاء الصياغة.
- يرفض استمرار فحص unittest إذا لم يكتشف أي حالات اختبار.
- يفحص HTML5 doctype وعناصر html/head/body/title/main/h1، والعنوان غير الفارغ.
- يتأكد من اللغة العربية واتجاه RTL وUTF-8 وviewport المتجاوب.
- يرفض IDs المكررة ومراجع aria-labelledby المفقودة وعلامات تعارض الدمج.
- يستخدم `scripts/stage_site.py` لإنشاء `_site` من النسخة التي جرى checkout لها، بعد تسجيل SHA الفعلي من `git rev-parse HEAD` والتحقق من أنه 40 خانة hex صغيرة. يشغّل `scripts/check_site.py` على `_site`، بما فيه اختبار HTTP محلي على loopback. معاينة PR ترفع نفس المجلد المفحوص كأثر قابل للتنزيل لمدة 7 أيام. على دفع `main` فقط، يرفع CI محتوى `_site` المفحوص بالاسم الثابت `validated-site-main-<run_id>`؛ وظيفة Pages العادية في استدعاء reusable workflow نفسه تنزّل الأثر نفسه حتى بعد إعادة تشغيل الوظائف الفاشلة، ثم ترفض غيابه أو اختلاف SHA/manifest أو ملفات غير مسموحة وتعيد فحص الموقع قبل رفعه إلى Pages. إعادة التشغيل الكاملة تستخدم `overwrite: true` لاستبدال أثر التشغيل بالاسم نفسه، مع احتفاظ 7 أيام. إعادتان كاملتان متزامنتان قد تتنافسان على الاسم؛ `overwrite` لا يوفر قفلًا وقد تفشل إحدى عمليتي الرفع/التنزيل، لذا تجنب الإعادات المتزامنة. لم يُنفّذ اختبار rerun فعلي على GitHub، ولم يتغير سجل مراجعة #273. لا تعيد وظيفة Pages العادية إنشاء الموقع. مسار الاستعادة rollback ما زال يجهز SHA السابق ويفحصه منفصلًا. هذا يربط ملفات الموقع التي فحصها CI بمدخل Pages العادي داخل التشغيل نفسه، لكنه لا يثبت أي تحويلات لاحقة في GitHub Pages/CDN، ولا يجعل Vercel يستهلك الأثر نفسه؛ Vercel يواصل فحص مرشحه منفصلًا. راجع [توثيق Git الرسمي لـ`git rev-parse`](https://git-scm.com/docs/git-rev-parse)، [توثيق GitHub لآثار workflow](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)، [توثيق إعادة تشغيل workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs)، [متغيرات التشغيل الرسمية](https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables)، [توثيق upload-artifact وخيار الاستبدال](https://github.com/actions/upload-artifact)، و[إصدار وإجراء download-artifact v8.0.2 المثبت](https://github.com/actions/download-artifact/releases/tag/v8.0.2).
- يفرض تثبيت الإجراءات الخارجية في GitHub Actions على commit SHA كامل، بما يشمل ملفات workflow وملفات lock وقوالب الوكلاء، عبر `scripts/check_action_pins.py`.
- يثبت اعتمادات Python من `requirements-api.lock` و`requirements-dev.lock` باستخدام `pip --require-hashes`، ثم يشغّل Bandit و`pip-audit` على كامل الاعتمادات المقفلة، المباشرة والانتقالية. يفشل الفحص عند العثور على ثغرة.
- يشغّل فحص الأسرار في وظيفة `security` الحالية باستخدام Gitleaks CLI 8.24.3 من إصدار GitHub الرسمي، مع بصمة SHA-256 ثابتة للأرشيف، بدل الاعتماد على تخمين نطاق الإجراء. يتحقق السكربت من نسخة CLI وSHA checkout، ويختار النطاق من حمولة الحدث: `before..after` للدفع، و`base.sha..GITHUB_SHA` للـPR مع التحقق أن base وhead الخاصين بالـPR ضمن تاريخ checkout، والتاريخ الكامل للـworkflow اليدوي أو القابل لإعادة الاستخدام. يشمل نطاق PR commit الدمج الذي يجري اختباره حتى تُفحص أيضًا أي تغييرات في نتيجة الدمج. إذا كان الدفع أول إنشاء للفرع، يفحص تاريخ `after` المتاح؛ حذف الفرع موثق كحدث لا يتطلب فحصًا. يستخدم `-m` كي يعرض Git فروق ملفات commits الدمج لكل parent ولا يسقط patch الدمج بصمت. النطاق الفارغ أو غير القابل للتحقق، أو غياب سجل اكتمال Gitleaks أو تقرير JSON سليم، أو اختلاف SHA/نسخة الأداة، يفشل الوظيفة. ملخص Actions يعرض SHA checkout والمصدر، والنطاق، وعدد commits في سجل Git وبصمته، وعدّاد Gitleaks وعدد النتائج؛ لا يطبع ملفات النتائج أو قيم الأسرار ولا يرفعها كأثر. عدّاد Gitleaks يقيس commits التي احتوت فروقًا نصية قابلة للفحص؛ لذلك قد يكون أقل من عدد commits في التاريخ عند وجود commits للحذف فقط أو ملفات ثنائية. نجاح الفحص دليل على تشغيل الأداة على النطاق المعلن، وليس إثباتًا لغياب الأسرار القديمة خارج النطاق أو في القيم الثنائية/المتجاهلة، ولا يفحص أسرار بيئة التشغيل. راجع [توثيق Gitleaks الرسمي لإصدار 8.24.3](https://github.com/gitleaks/gitleaks/tree/v8.24.3) و[مرجع Git الرسمي لـ`git log`](https://git-scm.com/docs/git-log).
- تتحقق Dependabot أسبوعيًا من تحديثات حزم Python وإجراءات GitHub.
- يشغّل خادمًا محليًا مؤقتًا ويتحقق من HTTP 200 ونوع HTML وتطابق المحتوى في / و/index.html.
- يشغّل اختبارات حواجز التحقق، وحالات الحوادث والتعافي، وعقد التحقيق والثقة.
- يختار الاختبارات بحسب الملفات المتغيرة؛ تغييرات workflows والإجراءات المحلية تشغّل اختبارات عقود Python حتى عندما تكون درجة المخاطر متوسطة. إذا تعذّر تحديد فرق موثوق، مثل غياب commit الأساس، يشغّل الفحص الكامل بدل الاعتماد على قائمة ملفات ناقصة من حمولة الحدث.
- ينشئ معاينة HTML قابلة للتنزيل على Pull Requests بعد نجاح الفحوص؛ تُحتفظ بها 7 أيام ولا تنشر إلى الإنتاج.
- يبني صورة اختيارية للموقع الثابت ويختبرها محليًا على loopback؛ لا يرفع الصورة إلى سجل حاويات.
- يبني صورة الموقع مرة واحدة من commit ذي SHA كامل، ويسجل Docker image ID، ثم يشغّل smoke test على loopback ويولّد SBOM بصيغة CycloneDX ويفحص الثغرات في الصورة المحلية نفسها. يتحقق كل من مولّد SBOM وفاحص Trivy من أن Docker image ID ما زال مطابقًا للصورة التي بُنيت واختُبرت؛ لا يُعاد بناء الصورة بين الخطوات ولا تُرفع إلى سجل.
- يولّد Trivy CLI 0.76.1 تقرير JSON للثغرات وSBOM CycloneDX. يقيّم التقرير بوابة محلية تفشل مغلقة: أخطاء Trivy أو قاعدة البيانات أو JSON المفقود/المعطوب تفشل المهمة، وHIGH/CRITICAL تمنع نجاح فحص الثغرات، بينما تُحسب MEDIUM/LOW/UNKNOWN دون منع النجاح. يحفظ الأثر `trivy-image-sbom-<run_id>-<attempt>` تقرير الثغرات وملف SBOM وملف دليل JSON لمدة 7 أيام؛ الدليل يربط SHA المصدر ووسم الصورة وDocker image ID وإصدار Trivy وعدد المكونات وبصمة SHA-256 لملف SBOM، من دون أسماء الحزم في الملخص.
- SBOM جرد غير موقّع، وليس إثبات منشأ موقّعًا (provenance attestation)، ولا صورة إصدار موقعة أو دليل نشر. لا يرفع CI الصورة إلى سجل ولا يثبت تشغيل خدمة أو صحة أي استدعاء AI. يثبت تثبيت Trivy بتوقيع ملف checksums عبر Cosign ثم يطابق SHA-256 للأرشيف مع ذلك الملف. راجع [دليل Trivy الرسمي لتوليد SBOM](https://trivy.dev/latest/docs/supply-chain/sbom/)، [مرجع Trivy الرسمي لخيارات الصور](https://trivy.dev/latest/docs/references/configuration/cli/trivy_image/)، [توثيق Sigstore الرسمي للتحقق من blob](https://docs.sigstore.dev/cosign/verifying/verify/)، [توثيق Git الرسمي لـ`git rev-parse`](https://git-scm.com/docs/git-rev-parse)، [توثيق GitHub لآثار workflow](https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts)، و[سياسة احتفاظ GitHub Actions بالآثار](https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts#configuring-a-custom-artifact-retention-period-for-an-artifact).
- ينسّق إعداد Terraform ويفحص صحته بعد تهيئة المزوّد دون backend؛ لا ينفذ `plan` أو `apply` ولا يحتاج اعتماد GCP. كما يثبت Conftest 0.71.1 ببصمة SHA-256 ثابتة، ويطبّق سياسة HCL على `infra/terraform` ويشغّل اختبارات رفض fixtures؛ راجع [تكامل Terraform policy](integrations/terraform-policy.md) و[خيارات Conftest الرسمية](https://www.conftest.dev/options/).

تشغيل CI على جميع الفروع لا ينشر إلى الإنتاج: وظيفة النشر الحالية ما زالت مشروطة بدفع ناجح إلى `main` فقط. راجع [أحداث GitHub Actions الرسمية](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

هذه فحوص متطلبات المشروع، وليست مدقق HTML/CSS شاملًا أو اختبار عرض في متصفح أو تدقيق وصول كاملًا. اختبار HTTP يخص الخادم المحلي، ولا يثبت صحة إعدادات الاستضافة أو النشر الفعلي. فحوص تطبيق AI Intelligence تتحقق من الاختبارات والنوع والبناء فقط؛ لا تثبت تشغيل تكاملات Firebase أو Google أو Gemini.

## التسليم على دفعات صغيرة

استخدم [قالب Pull Request](../.github/pull_request_template.md) لتحديد هدف واحد وشروط قبوله والسلوك الحالي الذي يجب الحفاظ عليه. ابدأ بالأساس المطلوب، ثم أرسل التحسينات المستقلة في دفعات منفصلة؛ راجع فرق كل دفعة ومعاينتها قبل الانتقال إلى التالية.

عند تغيير الصفحة، نزّل معاينة PR من CI وافحصها على سطح المكتب وعرض هاتف ضيق، ثم تحقق من الروابط والمحتوى الأساسي. بعد الدمج، راجع Deployment Health Check وتأكد من تطابق SHA المنشور مع النسخة التي اجتازت CI. معاينة PR حزمة محلية وليست رابطًا عامًا، كما أن فحص صحة النشر لا يستبدل المراجعة البصرية في المتصفح.

## التشغيل محليًا

من جذر المستودع، باستخدام Python 3.10 أو أحدث:

```sh
python3 -m pip install --require-hashes -r requirements-api.lock
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

ملفا `requirements-api.txt` و`requirements-dev.txt` يعلنان الاعتمادات المباشرة. الملفان `requirements-api.lock` و`requirements-dev.lock` يقفلان الاعتمادات الانتقالية بإصدارات وSHA256؛ CI يثبت منهما بوضع التحقق من hash ثم يدقق القفلين بواسطة `pip-audit --requirement`. مجموعة unittest تحتاج اعتمادات API، فثبت `requirements-api.lock` قبل تشغيلها. يتطلب تدقيق الثغرات الوصول إلى مصدر بيانات الثغرات عبر الشبكة. لا يلزم Secret أو خدمة مدفوعة لهذا الفحص.

أُنشئت ملفات القفل باستخدام `pip-tools 7.6.2` وPython 3.12. ملف أدوات التطوير يثبت `pip` أيضًا حتى تكون عملية تثبيت CI نفسها محددة. لإعادة توليد الملفات بعد مراجعة تحديثات الاعتماديات:

```sh
python3 -m pip install pip-tools==7.6.2
pip-compile --generate-hashes --strip-extras --resolver=backtracking \
  --output-file=requirements-api.lock requirements-api.txt
pip-compile --allow-unsafe --generate-hashes --strip-extras --resolver=backtracking \
  --output-file=requirements-dev.lock requirements-dev.txt
```

اقرأ [وضع التحقق من hashes في pip](https://pip.pypa.io/en/stable/topics/secure-installs/#hash-checking-mode) و[دليل hashes في pip-tools](https://pip-tools.readthedocs.io/en/latest/#using-hashes). تغيير القفل يتطلب مراجعة فرق الإصدارات وإعادة تدقيق الثغرات. لا يحتاج إعداد حماية الفرع إلى تعديل.

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


## Pages artifacts across failed-job retries

The normal Pages upload and deployment share the attempt-specific name
`github-pages-candidate-<run_id>-<run_attempt>`, matching the existing manual
candidate and automatic-rollback isolation pattern. A failed-job retry downloads
and revalidates the same run-scoped `validated-site-main-<run_id>` input, then
uploads a new attempt-specific Pages artifact. Older uploads remain distinct;
the deployment action must select exactly the current attempt's name.

Observed on main SHA `691307aed3a4d846bf86d67ca11c19079598514b`, run
[43618844767](https://github.com/hamedonassar95/Devobs/actions/runs/43618844767):
the first deployment reported no `github-pages` metadata even though the upload
completed and the artifact was subsequently visible. Retrying only failed jobs
uploaded a second artifact under the same default name; deployment then rejected
the two matches. Validation, Node, Python, PostgreSQL RLS, security and container
checks passed. Attempt-specific names fix that reproducible retry collision;
they do not guarantee availability or immediate consistency of GitHub's API.

References: [upload-pages-artifact inputs](https://github.com/actions/upload-pages-artifact#inputs),
[deploy-pages inputs](https://github.com/actions/deploy-pages#inputs), and
[GitHub run variables](https://docs.github.com/en/actions/reference/workflows-and-actions/variables#default-environment-variables).

## Deployment manifest verification: bounded transport retries

`deployment-health-check.yml` retrieves `/deployment.json` with a bounded retry
loop that covers transient transport failures only.

Historical evidence: incident #707 recorded run
[44401423814](https://github.com/hamedonassar95/Devobs/actions/runs/44401423814)
on `main` at `c3998b951d8fb6b829e93105e6b34388722b2a63`. The failed job is
`production-release / verify / verify-production`, and its only failure
annotations are `Could not retrieve the deployment manifest.` plus the step exit
code, so the page fetch and title check had already succeeded. That run used
`curl --retry 5 --retry-delay 5` without `--retry-all-errors`; per the
[curl `--retry` documentation](https://curl.se/docs/manpage.html#--retry) only
timeouts, FTP 4xx and HTTP 408/429/5xx count as transient by default, so a
connection-reset-class exit was never retried by that option. The incident
reported curl exit `56` (receive error); the public job log requires admin
access, so that exact code is treated as incident-reported rather than
independently verified here. A single lost read-only GET was therefore enough to
fail verification and mark the release a rollback candidate. The explicit loop
below retries only that class of transport failure.

Limits:

- At most 3 attempts, so the step cannot loop indefinitely.
- Per attempt: `--connect-timeout 5` and `--max-time 20`; delay between
  attempts is 1s then 2s. Worst case is roughly 63s of curl time plus 3s of
  delay, inside the existing `timeout-minutes: 5` job bound.
- Only read-only GET requests. No request body, method override, upload flag or
  curl-internal `--retry` is used on the manifest fetch.
- Retried curl exit codes: `6` (resolve), `7` (connect), `18` (partial
  transfer), `28` (timeout), `35` (TLS handshake), `52` (empty reply), `55`
  (send), `56` (receive), `92` (HTTP/2 stream). Any other curl exit code fails
  immediately.
- TLS verification is never disabled: no `--insecure`, `-k` or
  `--no-check-certificate` anywhere in the step.
- HTTP status handling is unchanged and is never retried. A non-200 response
  still fails the job, except the pre-existing legacy rule where HTTP `404` with
  an empty `EXPECTED_SHA` reports a warning and passes. With a required expected
  SHA, `404` fails closed.
- The schema gate (`jq -er 'select(.schema_version == 1) | .source_sha'`), the
  exact `^[0-9a-f]{40}$` check and the `deployed_sha != EXPECTED_SHA`
  comparison are untouched, so an invalid manifest or a wrong commit cannot be
  retried into a pass.
- Failures print only the curl exit code and where the fetch stopped. No
  response body, header, environment dump or credential is logged, and
  `deployment.json` is re-downloaded per attempt rather than reused.

`tests/test_deployment_health_retry.py` extracts the real `run:` block from the
workflow, replaces only the site URL with a loopback mock server, and executes
it with the host's bash, curl and jq. It covers connection reset followed by
success, persistent reset, transport timeout, partial transfer followed by
success, persistent partial transfer, HTTP `404` with and without a required
expected SHA, HTTP `500`, invalid JSON and an invalid source SHA (neither may
echo the response body), an incorrect source SHA, and a first-attempt success
that must not warn. Persistent failures stop after exactly 3 requests; HTTP
errors stop after 1. When bash, curl or jq is unavailable the affected
behavioural cases skip with a reason instead of silently passing; the contract
cases still assert the retry-bound, exact retry-code list and fail-closed
invariants.

Remaining risks:

- Retries only help with faults shorter than the retry window. A Pages or CDN
  outage longer than about one minute still fails the check, by design.
- The retry does not detect a stale-yet-healthy response: if the host returns
  HTTP `200` with an old but well-formed manifest and no `EXPECTED_SHA` is
  supplied, the check passes. Callers that need exactness must pass
  `expected_sha`, as the release path already does.
- `--max-time 20` bounds a single transfer; a very large or slow manifest could
  exceed it and consume the attempts, which still fails closed.
- The loop retries DNS, TCP, TLS and HTTP/2 transport errors alike. It cannot
  distinguish a transient network fault from a persistent origin
  misconfiguration, so repeated failures remain failures.
- The retry logic is workflow bash, not application code, so only the extracted
  step is covered; other deployment workflows keep their own behaviour.
