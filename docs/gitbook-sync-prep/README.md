# تجهيز GitBook لمستودع Devobs

هذه حزمة تحضير معزولة لمراجعة تكامل GitBook Git Sync. وجود الملفات لا يفعّل المزامنة ولا يثبت نجاحها، ولا يغيّر فهرس المستودع الحالي.

## النطاق

- مسار المشروع المقصود مستقبلًا هو هذا المجلد فقط: `docs/gitbook-sync-prep/`.
- مصدر التوثيق المقترح هو فرع GitHub بعد مراجعة التغيير. لا توجّه GitBook إلى جذر المستودع ضمن هذا التحضير.
- لا تُستورد صفحات GitBook الخاصة أو تُنسخ إلى هذا المستودع. لم تُنسخ أي صفحة خاصة في هذه الحزمة.
- لا يوجد تشغيل مزامنة أو نشر أو تغيير إعدادات حساب ضمن هذا التغيير.

## صفحات الحزمة

- [سياسة المحتوى والنطاق](CONTENT_SCOPE.md)
- [قائمة التحقق للمزامنة الأولية](INITIAL_SYNC_CHECKLIST.md)
- [تشخيص فشل Gitleaks في تاريخ Git](GITLEAKS_HISTORY_DIAGNOSTICS.md) — مراجعة مبنية على أدلة CI العامة؛ ليست موافقة نشر أو دليل إغلاق العطل.
- [حالة نسخة Devobs على GitLab](GITLAB_REPLICA_STATUS.md) — مقارنة الالتزامات العامة وحدود التوثيق والربط، لا تشغيل مزامنة أو Pipeline.
- [فحص جاهزية موارد Devobs المجانية](FREE_STAGING_READINESS.md) — تقرير أمان يدوي محدود دون مفاتيح أو نشر.

## وثائق Devobs القائمة

الملفات التالية تبقى مصادرها الحالية في المستودع؛ هذه الحزمة لا تستبدلها ولا تنسخها:

- [README الحالي](https://github.com/hamedonassar95/Devobs/blob/main/README.md)
- [مركز الأتمتة](https://github.com/hamedonassar95/Devobs/blob/main/docs/AUTOMATION_HUB.md)
- [دليل CI](https://github.com/hamedonassar95/Devobs/blob/main/docs/CI.md)
- [نطاق وضوابط DevSecOps](https://github.com/hamedonassar95/Devobs/blob/main/docs/DEVSECOPS.md)

## حالة الدليل

**PROPOSED:** مسار المجلد وإعداداته المحلية مقترحان للمراجعة. يلزم التحقق من وجهة Git Sync والفرع ومجلد المشروع في واجهة GitBook قبل أي اتصال أو تشغيل مزامنة.

## إعداد الموقع على مستوى GitBook

يعرّف [`gitbook-docs.yaml`](gitbook-docs.yaml) خريطة موقع واحدة على مستوى GitBook، ويشير إلى محتوى هذا المجلد فقط. إذا اختير هذا المجلد مستقبلًا بوصفه **Project directory** في Git Sync، فإن `content.directory: ./` يعني هذا المجلد؛ وتبقى `.gitbook.yaml` و`SUMMARY.md` هما إعداد الفضاء وفهرس صفحاته. الملف لا يتصل بـ GitBook ولا يبدأ مزامنة أو نشرًا.

مفتاح الفضاء `devobs-gitbook-sync-prep` **مقترح محليًا**، وليس معرّفًا ثبت أنه يطابق فضاءً قائمًا. توثيق المستودع يذكر Git Sync سابقًا على `main`، بينما أظهرت قراءة بيانات GitBook للقراءة فقط بتاريخ 2026-11-25 أن الموقع مُدرج كعام، لكن بنيته لا تعرض مساحات منشورة. تتعارض هذه الملاحظة مع سجل الربط السابق في المستودع؛ لذلك تبقى وجهة الربط الحية، والفرع، ومجلد المشروع، ومفتاح الفضاء **UNVERIFIED**. لا تستخدم الإعداد قبل مطابقة هذه القيم مع إعداد GitBook الفعلي ومراجعة أثرها على المساحة الحالية.

قبل أي ربط أو تشغيل مزامنة أو نشر، يلزم اعتماد بشري صريح للمستودع والفرع ومجلد المشروع واتجاه المزامنة وخصوصية الموقع ومفتاح الفضاء. لا يجيز هذا التحضير كتابة GitBook إلى GitHub أو تعديل إعداداته.

### مراجع GitBook الرسمية

- [إعداد المحتوى وملف `gitbook-docs.yaml`](https://gitbook.com/docs/docs-as-code/git-sync/content-configuration) — يشرح خريطة الموقع، مفاتيح الفضاء، ومسارات المحتوى.
- [Git Sync في المستودعات متعددة المجلدات](https://gitbook.com/docs/docs-as-code/git-sync/monorepos) — يشرح Project directory والمسارات النسبية.
- [مخطط YAML الرسمي](https://api.gitbook.com/gitbook-docs.yaml) — المخطط المشار إليه في حقل `$schema` للتحقق من بنية الملف.
