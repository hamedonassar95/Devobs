# Devobs — المعاينة والتحكم في النشر

## نطاق المشروع
هذه الضوابط تخص مستودع `hamedonassar95/Devobs`. الصفحة الحالية مثال تعليمي يحمل محتوى الدلة موبايل؛ لا تعني أن فصل المشروعين قد اكتمل.

## الإعدادات التي تمت مراجعتها مباشرة — 6 أكتوبر 2026
- Settings → Pages → Source: GitHub Actions.
- بيئة `github-pages`: Selected branches and tags، فرع `main` فقط، دون tags.
- لا توجد أسرار أو متغيرات في بيئة الإنتاج.
- لا تتطلب البيئة موافقة نشر يدوية حاليًا؛ نقطة القرار هي دمج PR بعد الفحوص الإلزامية. سياسة الموافقات يجب مراجعتها عند انضمام متعاون.
- قاعدة Protect main تتطلب PR وvalidate ناجحًا من GitHub Actions، مع strict checks ودون bypass actors.
- الملفات تحتوي مسار نشر Pages واحدًا؛ Health Check يفحص الناتج ولا ينشر.
- مصدر GitHub Actions لا يربط Pages باسم workflow محدد؛ يجب مراجعة أي تغيير مستقبلي في ملفات workflows. لا يمثل ذلك تدقيقًا شاملًا لتطبيقات وخدمات خارجية.

## مراجعة حية بعد الدمج — 15 أكتوبر 2026
- إعداد Pages الحالي: `workflow`، المصدر `main` من جذر المستودع، والحالة `built`.
- سياسة بيئة `github-pages` الحالية تسمح بفرع `main` فقط.
- تعذرت قراءة حماية `main` عبر رمز GitHub الحالي (HTTP 403)، لذلك تبقى مراجعة حماية الفرع المؤرخة في 6 أكتوبر هي آخر دليل متاح هنا.

## أدلة آخر نشر إنتاجي — 15 أكتوبر 2026
- دُمج PR [#110](https://github.com/hamedonassar95/Devobs/pull/110) في commit [`ce625cd`](https://github.com/hamedonassar95/Devobs/commit/ce625cdcebbb438c5db2529b3e5dd2bc5c076ec2).
- نجح [CI](https://github.com/hamedonassar95/Devobs/actions/runs/38773344512) على commit الدمج.
- نجح [Deploy Pages](https://github.com/hamedonassar95/Devobs/actions/runs/38773391874) ونشر SHA المختبر.
- نجح [Deployment Health Check](https://github.com/hamedonassar95/Devobs/actions/runs/38773488015)، وتطابق SHA في `deployment.json` مع commit الدمج.

## تحقق أحدث من main — 22 أكتوبر 2026

- رأس main الذي جرى التحقق منه: `40647754fc247195a2c523e9011ddb146201a915`.
- نجح [CI رقم 39711232712](https://github.com/hamedonassar95/Devobs/actions/runs/39711232712) و[Push on main رقم 39711231865](https://github.com/hamedonassar95/Devobs/actions/runs/39711231865) على SHA نفسه.
- نجح نشر GitHub Pages وفحص صحة الموقع ومقارنة SHA المنشور في CI رقم 39711232712. نجحت كذلك فحوص الأمان وعقد الموقع والتحقق.
- تخطى هذا التشغيل فحوص Node وPython لأن التغيير الذي أطلقه كان توثيقيًا فقط. لا يُعد هذا التشغيل دليلًا على تنفيذها.
- تدقيق Repository Policy Audit الأحدث، [رقم 39280011409](https://github.com/hamedonassar95/Devobs/actions/runs/39280011409)، أخفق قبل قراءة قواعد المستودع لأن GitHub API أعاد HTTP 401. يجب تصحيح رمز القراءة ثم إعادة التدقيق.
- لم تتغير مراجعة إعدادات GitHub الحية في هذا السجل: حماية الفرع موثقة آخر مرة في 6 أكتوبر، وقراءة حديثة لإعدادات Ruleset لم تكن متاحة لهذه الجلسة.

## Preview
بعد نجاح فحوص PR، ينتج CI حزمة ZIP باسم يبدأ بـ `preview-pr-`.
افتح تشغيل CI من تبويب Checks، ثم قسم Artifacts أو رابط Download في Summary، ونزّل الحزمة وفك ضغطها وافتح `index.html`.
على Windows يمكن أيضًا تشغيل `py -3 -m http.server 8000 --bind 127.0.0.1` داخل مجلدها وفتح `http://127.0.0.1:8000`.
هذه معاينة HTML قابلة للتنزيل وليست استضافة مستقلة أو رابط موقع عام. فتح ملفات HTML المحلية على الآيفون يعتمد على التطبيق المستخدم؛ المعاينة المستضافة لاحقًا قرار منفصل.
- الاحتفاظ: 7 أيام، والتنزيل يتطلب تسجيل الدخول إلى GitHub.
- المحتوى: index.html وassets إن وجد، دون كامل المستودع.
- صلاحيات CI: contents: read؛ لا pages: write ولا id-token: write ولا ربط ببيئة الإنتاج.
- الفحوص الفاشلة لا تُنتج المعاينة.
- حزمة المعاينة لا تُستهلك في workflow الإنتاج ذي الصلاحيات الأعلى.
- Actions مثبتة إلى commit SHA؛ تفاصيل النسخة الجديدة: actions/upload-artifact v7.0.1، SHA 043fb46d1a93c77aae656e7c1c64a875d1fc6a0a.

## Production
1. PR ناجح يُدمج في main وفق قواعد المستودع.
2. CI يعمل على push إلى main.
3. Deploy Pages يقبل فقط نجاح CI الناتج عن push إلى main من المستودع نفسه.
4. مهمة eligible بصلاحية القراءة تتأكد أن SHA المختبر لا يزال رأس main؛ تتخطى التشغيل القديم عند اختلافهما.
5. مهمة deploy فقط تحصل على pages: write وid-token: write، وتستخدم SHA المختبر.
6. تجمع ملفات الموقع فقط، وتضيف `deployment.json` مع `schema_version` وSHA المصدر المختبر، ثم تنشرها في github-pages.
7. Deployment Health Check يتحقق من HTTP ومحتوى الصفحة، ثم يقارن SHA المنشور مع SHA تشغيل CI الذي أطلق النشر. يتحقق أولًا من أن مهمة النشر نفذت فعلًا، لذلك لا يعامل تجاوز CI قديم على أنه فشل في إصدار لم يُنشر. التشغيل اليدوي يعرض SHA المنشور؛ وإذا كان النشر التاريخي يفتقر إلى manifest، يسجل ذلك بوضوح ويكتفي بفحص HTTP والمحتوى.
8. قبل النشر تُحفظ قيمة SHA المنشور حاليًا من manifest. إذا فشل فحص صحة الإصدار الجديد بعد نجاح النشر، يحاول المسار استعادة ذلك SHA فقط عندما يكون مختلفًا عن المرشح وموجودًا كسلف في `main` الذي لم يتغير أثناء النشر. يفحص أولًا صفحة HTML للهدف كبيانات باستخدام validator موثوق، ثم يتحقق فحص الصحة من SHA المستعاد. يبقى تشغيل CI فاشلًا لتوثيق خلل الإصدار المرشح حتى لو نجحت الاستعادة. إذا غاب manifest أو تحرك `main` أو فشل فحص الصفحة، يتوقف المسار ويترك المعالجة لـIncident Response ودليل التراجع اليدوي.

فحص `eligible` يقلل خطر إعادة نشر commit قديم عند إعادة تشغيل CI، لكنه ليس قفلًا ذريًا يمنع تحرك main بعد الفحص. لذلك يعيد حارس الاستعادة فحص SHA الحالي، ويتوقف بدل الكتابة فوق نشر أحدث. concurrency يسلسل عمليات النشر. لا يُدّعى ضمان ذرية أو فحص بصري شامل للموقع.

النشر اليدوي بإجراء واحد والرجوع الحاليان ينشئان manifest أيضًا، ويتحقق كل منهما من SHA المرشح أو الإصدار قبل إعلان نجاح التحقق. ملفات rollback الموجودة على وسوم إصدارات تاريخية قديمة لا تحتوي هذا السلوك؛ تبقى قابلة للتشغيل وفق عقد مدخلاتها، ويشير الفحص اليدوي إلى غياب manifest بدل الادعاء بأنه تحقق من commit.

## الموافقة والرجوع
المسار المعتمد نشر تلقائي بعد الدمج وفحوص main؛ لا توجد موافقة إضافية لكل نشر. عند فشل فحص صحة Pages، توجد استعادة تلقائية محدودة إلى آخر SHA منشور في manifest وفق الحراس أعلاه.
للرجوع: أنشئ فرعًا من main الحالي، اعكس التغيير المسبب عبر revert، افتح PR واترك الفحوص تنجح ثم ادمجه. يصبح التراجع commit جديدًا يُختبر وينشر بالطريقة نفسها.
لا تستخدم force-push ولا تعطّل حماية main. إعادة تشغيل CI قديم ليست آلية rollback معتمدة.
لتعطيل حزم المعاينة أو إلغاء هذا التعديل، اعكس PR الذي أضافه عبر PR جديد.
المشروع الحالي صفحة ثابتة؛ هذه استعادة ملفات التطبيق وليست استعادة بيانات أو ترحيلات قاعدة بيانات. لم تُجرَ تجربة فشل حيّة للنشر بهدف اختبار الاستعادة التلقائية؛ سيظل فشل فحص المرشح ظاهرًا في CI حتى عند نجاح استعادة النسخة السابقة.

## اختبار Vercel على مشروع تجريبي
- سير `Vercel staging test` يدوي فقط، ويُطلق من `main` مع SHA كامل لمرشح مختلف عن رأس `main`. يعامل ملفات المرشح كبيانات في مجلد `candidate`، ويستخدم أدوات التحقق الموثوقة من `main`.
- يتحقق من محتوى `_site` ثم ينشر معاينة فقط إلى مشروع Vercel تجريبي قابل للتخلص منه، ويفحص SHA والنص المتفق عليه ومسارات الملفات الخاصة. لا ينفذ نشرًا إلى هدف الإنتاج ولا ترقية ولا ربط نطاق.
- يقرأ `buildCommand` و`outputDirectory` من `deploy/vercel-staging.json` عبر [`--local-config`](https://vercel.com/docs/cli/global-options#local-config) لأوامر Vercel CLI؛ لا يضيف أو يغيّر `vercel.json` في جذر المستودع، لذلك لا يغيّر إعداد بناء Git Integration للمشروع الحالي. وثائق [إعداد `vercel.json`](https://vercel.com/docs/project-configuration/vercel-json) تشرح حقلي `buildCommand` و`outputDirectory`.
- أنشئ بيئة GitHub `vercel-staging` وضع فيها `VERCEL_TOKEN` و`VERCEL_ORG_ID` و`VERCEL_PROJECT_ID` الخاص بالمشروع التجريبي فقط. استخدم رمز Vercel محدودًا إلى هذا المشروع؛ توثيق [Access Tokens](https://vercel.com/docs/accounts/access-tokens) يذكر دعم نطاق مشروع واحد واستخدام الرمز مع CLI وREST API. إذا لم يكن إنشاء رمز مشروع متاحًا لحسابك، اعزل المشروع التجريبي في فريق أو حساب منفصل.
- `VERCEL_AUTOMATION_BYPASS_SECRET` اختياري لفحوص HTTP عند تفعيل Deployment Protection؛ عند غيابه يفشل الفحص برسالة واضحة إذا منعته الحماية. لا تنسخ بيانات اعتماد المشروع الإنتاجي إلى هذه البيئة.

## أدلة الاختبار السابق
PR #10: https://github.com/hamedonassar95/Devobs/pull/10
- خطأ doctype أدى إلى فشل CI ومنع الدمج.
- استعادة الملف أدت إلى نجاح CI وCodeQL.
- لم يحدث دمج أو نشر لفرع الاختبار.

## مراجع رسمية راجعت بتاريخ 6 أكتوبر 2026
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run
- https://github.com/actions/upload-artifact/releases/tag/v7.0.1
