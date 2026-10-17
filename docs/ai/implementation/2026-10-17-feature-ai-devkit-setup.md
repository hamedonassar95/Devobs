---
phase: implementation
title: Implementation Guide
description: Technical implementation notes, patterns, and code guidelines
---

# التنفيذ

## Lifecycle progress

- [x] Phase 7: implementation checked against design
- [x] Phase 8: tests completed or documented as not applicable
- [ ] Phase 9: final code review complete

## الملفات

- `.ai-devkit.json`: البيئات، المراحل، ومجموعة المهارات المختارة؛ وضع النسخ مفعّل لكل مهارة.
- `.agents/skills/`: نسخ المهارات التي يقرأها Codex.
- `.claude/skills/`: نسخ المهارات التي يقرأها Claude Code.
- `dev-lifecycle/scripts/check-status.sh`: يقرأ مخرجات AI DevKit لتحديد مستندات الميزة، ويتحقق من اكتمال متطلبات المراحل، ويحفظ تقدم المراحل 7–9 في مستند التنفيذ.
- `licenses/AI-DevKit-Apache-2.0.txt`: نص الرخصة للمهارات المنسوخة.
- `THIRD_PARTY_NOTICES.md`: مصدر المهارات وإشعار نسبتها.
- `docs/ai/<phase>/`: توثيق الميزة لكل مرحلة من دورة الحياة.
- `docs/AI_DEVKIT.md`: خطوات إعداد المساهم والتحقق.

## الإعداد والتحقق

```bash
npx --yes ai-devkit@0.70.1 lint
npx --yes ai-devkit@0.70.1 lint --feature ai-devkit-setup
```

توجد المهارات في المستودع بعد استنساخه؛ لا يحتاج استخدامها إلى روابط نحو ذاكرة التخزين المؤقت أو مجلد المنزل لمنشئ الملفات. لتحديث نسخ المهارات من السجل وفق الإعداد، راجع الدليل وشغّل أمر التثبيت ذي `--overwrite` ثم راجع الفرق قبل الالتزام.

## حدود التكامل

لا يغير هذا الإعداد تطبيق الويب أو GitHub Actions أو وحدات CI المشتركة أو إعدادات السحابة. يظل AI DevKit أداة محلية اختيارية للمساهمين.
