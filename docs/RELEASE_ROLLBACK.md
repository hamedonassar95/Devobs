# Release & Rollback Runbook

هذا المستند يعرّف آلية الإصدار والرجوع الآمن لموقع Devobs المنشور على GitHub Pages.

## الهدف

عند ظهور مشكلة في إصدار جديد على الإنتاج، لا نعدّل فرع `main` مباشرة ولا نعيد كتابة التاريخ.
بدلاً من ذلك نعيد نشر Release مستقر سابق عبر Workflow يدوي ومحمي.

## أول Baseline معتمد

- Release: `v1.0.0`
- Commit: `fa1e543c178d7e7f6933f79f3a0b905d73789916`
- الحالة: Stable release
- Pre-release: No
- Target وقت الإصدار: `main`

هذا الـSHA هو المرجع المعروف لأول نسخة مستقرة، ويُستخدم للتحقق عند الحاجة.

## آلية Rollback

Workflow:
`.github/workflows/rollback-pages.yml`

التشغيل يتم يدويًا فقط من GitHub Actions.

### الحواجز الأمنية

قبل أي نشر، الـWorkflow:

1. يطلب Tag بصيغة Semantic Versioning مثل `v1.0.0`.
2. يطلب كتابة كلمة التأكيد `ROLLBACK` حرفيًا.
3. يتحقق من وجود الـTag داخل المستودع.
4. يحول الـTag إلى Commit SHA محدد.
5. يتحقق أن GitHub Release منشور وليس Draft.
6. يرفض أي Pre-release.
7. يعيد تشغيل اختبارات المشروع على Commit الإصدار المطلوب.
8. ينشر نفس Commit المحدد إلى GitHub Pages.
9. ينفذ Production HTTP health check بعد النشر.
10. يسجل Release وCommit ونتيجة التحقق في GitHub Actions Job Summary.

## طريقة التنفيذ

من GitHub:

`Actions → Rollback Pages → Run workflow`

ثم:

- Release tag: مثال `v1.0.0`
- Confirmation: `ROLLBACK`

لا تستخدم Tag غير معروف أو إصدار غير مستقر.

## ما الذي لا يفعله Rollback

Rollback التشغيلي لا يرجع `main` إلى الخلف، ولا يحذف commits ولا يعيد كتابة Git history.

هو يعيد نشر نسخة مستقرة معروفة إلى Production فقط.

هذا يحافظ على:

- سجل Git كامل.
- حماية `main`.
- إمكانية إصلاح المشكلة بشكل طبيعي عبر Pull Request جديد.
- القدرة على العودة لاحقًا إلى أحدث نسخة سليمة.

## Forward recovery

بعد Rollback:

1. افتح Branch إصلاح منفصل.
2. أصلح سبب المشكلة.
3. افتح Pull Request إلى `main`.
4. انتظر نجاح CI وCodeQL.
5. ادمج الإصلاح.
6. تحقق من Deployment Health Check.
7. أنشئ Release جديدًا Patch مثل `v1.0.1`.

## ملاحظة مهمة

أي Deployment ناجح لاحق من `main` قد يستبدل النسخة التي تم نشرها بالـRollback.
لذلك يجب إصلاح سبب المشكلة قبل إعادة النشر المعتاد.

## تحسين أمني لاحق

يوصى بحماية Tags الإنتاجية مثل `v*` بقواعد Repository Ruleset تمنع الحذف أو التعديل غير المقصود، خصوصًا عند إضافة أعضاء آخرين للمشروع.
