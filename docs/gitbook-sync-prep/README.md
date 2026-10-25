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

## وثائق Devobs القائمة

الملفات التالية تبقى مصادرها الحالية في المستودع؛ هذه الحزمة لا تستبدلها ولا تنسخها:

- [README الحالي](https://github.com/hamedonassar95/Devobs/blob/main/README.md)
- [مركز الأتمتة](https://github.com/hamedonassar95/Devobs/blob/main/docs/AUTOMATION_HUB.md)
- [دليل CI](https://github.com/hamedonassar95/Devobs/blob/main/docs/CI.md)
- [نطاق وضوابط DevSecOps](https://github.com/hamedonassar95/Devobs/blob/main/docs/DEVSECOPS.md)

## حالة الدليل

**PROPOSED:** مسار المجلد وإعداداته المحلية مقترحان للمراجعة. يلزم التحقق من وجهة Git Sync والفرع ومجلد المشروع في واجهة GitBook قبل أي اتصال أو تشغيل مزامنة.
