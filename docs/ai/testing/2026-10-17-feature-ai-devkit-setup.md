---
phase: testing
title: Testing Strategy
description: Define testing approach, test cases, and quality assurance
---

# التحقق والجودة

## الفحوص المنفذة

- `npx --yes ai-devkit@0.70.1 skill list`: التأكد من ظهور المهارات المحلية.
- `npx --yes ai-devkit@0.70.1 lint`: فحص بنية إعداد AI DevKit ووثائقه.
- `npx --yes ai-devkit@0.70.1 lint --feature ai-devkit-setup`: فحص وثائق المراحل السبع للميزة.
- `git diff --check`: فحص المسافات وأخطاء التنسيق في فرق Git.
- تحقق أمر تتبع المهام الاختياري `npx --yes ai-devkit@0.70.1 task list --name ai-devkit-setup --json` وأعاد `unknown command 'task'`؛ لذلك لا يُعتمد على تسجيل المهام الدائم.

هذا التغيير إعداد ووثائق فقط؛ لا يتضمن تعديل منطق التطبيق أو سير عمل النشر، لذلك لم تُشغّل اختبارات التطبيق.

## مراجعة يدوية

- التأكد من أن مجلدي المهارات يحتويان ملفات فعلية لا روابط رمزية إلى مسارات محلية.
- التأكد من وجود إشعار المصدر ونسخة الرخصة المرفقة.
- التأكد من تطابق أسماء المهارات مع `.ai-devkit.json`.
- مراجعة أي تحديث للمهارات قبل اعتماده، خصوصًا التعليمات التي تطلب أدوات أو صلاحيات خارجية.
