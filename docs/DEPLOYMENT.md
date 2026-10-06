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
6. تجمع ملفات الموقع فقط وتنشرها في github-pages.
7. Deployment Health Check يتحقق من HTTP الناجح ووجود نص العلامة الحالي.

الفحص السابق للنشر يقلل خطر إعادة نشر commit قديم عند إعادة تشغيل CI؛ ليس قفلًا ذريًا يمنع تحرك main بين الفحص واكتمال النشر. concurrency يسلسل عمليات النشر. لا يُدّعى ضمان ذرية أو فحص بصري شامل للموقع.

## الموافقة والرجوع
المسار المعتمد نشر تلقائي بعد الدمج وفحص main؛ لا توجد موافقة إضافية لكل نشر.
للرجوع: أنشئ فرعًا من main الحالي، اعكس التغيير المسبب عبر revert، افتح PR واترك الفحوص تنجح ثم ادمجه. يصبح التراجع commit جديدًا يُختبر وينشر بالطريقة نفسها.
لا تستخدم force-push ولا تعطّل حماية main. إعادة تشغيل CI قديم ليست آلية rollback معتمدة.
لتعطيل حزم المعاينة أو إلغاء هذا التعديل، اعكس PR الذي أضافه عبر PR جديد.
المشروع الحالي صفحة ثابتة؛ هذه استعادة ملفات التطبيق وليست استعادة بيانات أو ترحيلات قاعدة بيانات. تجربة rollback الفعلية من المرحلة 5 ولم تنفذ هنا.

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
