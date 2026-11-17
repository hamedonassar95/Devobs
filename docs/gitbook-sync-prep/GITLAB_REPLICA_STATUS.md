# حالة نسخة Devobs على GitLab — 17 نوفمبر 2026

> **VERIFIED snapshot / READ ONLY.** بيانات GitLab وGitHub التالية تخص تاريخ الفحص فقط، ولا تُثبت تشغيل مزامنة مستمرة أو جاهزية النسخة للاعتماد الإنتاجي.

## المرجع الرسمي

- المصدر الوحيد المعتمد للشيفرة: [GitHub Devobs](https://github.com/hamedonassar95/Devobs).
- التزام GitHub `main` بعد [PR #678](https://github.com/hamedonassar95/Devobs/pull/678): `b2ccdcf5aaddb1a0b6c8423b98f19ed3e02245c5`.
- نجح [GitHub main CI #44034639484](https://github.com/hamedonassar95/Devobs/actions/runs/44034639484) على هذا الالتزام، بما فيه فحص الأمن و`validate`. الفحص الناجح لا يثبت نجاح إعادة تشغيل فشل Dependabot التاريخي.

## نتيجة GitLab (قراءة فقط)

| البند | الملاحظة |
| --- | --- |
| المستودع | [GitLab Devobs](https://gitlab.com/hamedonassar95/Devobs) |
| حالة الاستيراد من GitHub | `finished` (استيراد مكتمل، وليس دليل مزامنة دورية) |
| فرع `main` في GitLab | `663b0b29f7b8f92c256d401cc84f735fb3cb7dc5` |
| مقارنة المصدر والنسخة | **MISMATCH / STALE** — الالتزامان مختلفان |
| قائمة GitLab Pipelines | لم تعد سجلات في الاستعلام المتاح |
| قراءة أحدث Pipeline | HTTP 403؛ لا يجوز استنتاج نجاح أو فشل الوظائف من ذلك |
| GitBook | مساحة `Devobs Documentation` الخاصة استوردت SHA الدمج الصحيح في المجلد `docs/gitbook-sync-prep/` |

## ما هو المسموح الآن؟

استخدم GitLab لأغراض الاطلاع والمقارنة فقط. لا تُجر تغييرات على `main` أو قواعد الحماية أو تشغيلًا مباشرًا أو جدولة لخطوط CI. لا تنقل التحكم بالمصدر الأساسي إلى GitLab؛ لا تنشئ مشروعًا ثانيًا على أنه مصدر رئيسي.

يحتوي Devobs أصلًا على أداة [تدقيق GitLab للقراءة فقط](https://github.com/hamedonassar95/Devobs/blob/main/docs/GITLAB_READONLY_CI_AUDIT.md)، ولا حاجة إلى استحداث عملية مكررة. البرنامج يتطلب إعداد وصول مخوّل في بيئة التشغيل المستقلة؛ لا تنقل بيانات اعتماد إلى GitHub أو GitBook أو المحادثة.

## أداة التحقق اليدوي (مقترحة للمراجعة)

توفّر `scripts/check_gitlab_replica_parity.py` فحصًا عامًا باستخدام طلبَيْ `GET` ثابتَيْن إلى GitHub وGitLab، دون كلمات مرور أو رموز أو كتابة بيانات. تشرح [وثيقة الفحص](https://github.com/hamedonassar95/Devobs/blob/main/docs/GITLAB_REPLICA_PARITY.md) كيفية تشغيله، ورموز الخروج `MATCH / DRIFT / UNKNOWN`، وحدود المقارنة غير الذرّية. **إضافة الأداة إلى PR لا تعني تشغيلها تلقائيًا أو نشر GitBook.**

## شرط تحديث النسخة مستقبلًا

تنص [وثائق GitLab الرسمية](https://docs.gitlab.com/user/project/repository/mirror/pull/) على أن **Pull Mirroring** على GitLab.com يتطلب **Premium أو Ultimate**. لا نفترض أن الاشتراك الحالي يدعم ذلك. ينبغي أولًا الحصول على موافقة المالك على التكلفة والنطاق وصلاحيات الوصول، ثم توثيق حماية الفروع وحالات الاختلاف والاسترجاع وعدم تشغيل CI عند المزامنة قبل إجراء أي إعداد.

**النتيجة:** GitHub CI **PASS**، GitBook private sync **PASS**، GitLab SHA parity **FAIL (stale)**، وGitLab pipeline state **UNVERIFIED**. لا يوجد إذن بأي دمج أو نشر أو شراء خدمات.
