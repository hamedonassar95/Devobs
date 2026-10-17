---
phase: deployment
title: Deployment Strategy
description: Define deployment process, infrastructure, and release procedures
---

# النشر

## أثر التغيير

لا توجد تغييرات على حزمة الموقع أو الاستضافة أو إعدادات GitHub Actions. ملفات AI DevKit تُستخدم بعد جلب المستودع محليًا، ولا تنشر نفسها ولا تشغّل عمليات نشر.

## التوزيع

تصل ملفات الإعداد والمهارات إلى المساهمين عبر المستودع بعد مراجعة التغيير ودمجه. بعد الاستنساخ، يمكن للمساهم تشغيل فحوص AI DevKit الواردة في `docs/AI_DEVKIT.md`.

## التراجع

يمكن التراجع عن الإعداد بإرجاع ملفات `.ai-devkit.json` و`.agents/skills/` و`.claude/skills/` و`docs/ai/` ودليل الاستخدام إلى الحالة السابقة. لا توجد تغييرات بيانات أو بنية تحتية تحتاج إلى ترحيل.
