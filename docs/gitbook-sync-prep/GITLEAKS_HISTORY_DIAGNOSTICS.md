# تشخيص فشل Gitleaks في تاريخ Git

> **الحالة: VERIFIED MERGED PR #678 — 2026-11-17.** أُدمج إصلاح التشخيص وأصبحت الصفحة موجودة في GitBook الخاص. اجتازت الفحوص على التزام الدمج؛ أما السبب الجذري لفشل Dependabot السابق وإعادة نجاح فحصه فهما **UNVERIFIED**. لا توجد أدلة على تسريب أسرار من ذلك الفشل وحده.

## 1. الدليل المؤكد (VERIFIED)

- المستودع: `hamedonassar95/Devobs`، سير العمل `CI`، تشغيل GitHub Actions [#43858556890](https://github.com/hamedonassar95/Devobs/actions/runs/43858556890) في **2026-11-16**.
- الحدث `push` على فرع Dependabot لتحديث `firebase`، والالتزام المختار `2c40a80bfea7e1747064e379dc829ee34fc254e4`.
- نجح تثبيت Gitleaks **8.24.3** والتحقق من بصمة الحزمة، لكن خطوة `Scan commits for leaked secrets with Gitleaks` فشلت برسالة `git history verification failed`.
- خطوة `security` فشلت، ثم بوابة `validate` تبعت الفشل. **لم تُسجل نتيجة فحص مكتمل أو عدد تسريبات مؤكد**؛ لا تستنتج وجود أسرار مكشوفة من هذا الخطأ وحده.
- `.github/workflows/ci.yml` يستخدم `actions/checkout` بعمق `fetch-depth: 0` في مهمة الأمن؛ لذلك لا يصح افتراض أن الخطأ سببه shallow clone دون دليل إضافي.

## 2. ما بقي غير مثبت (UNVERIFIED)

- لا يتضمن السجل العام سبب Git الداخلي أو بيانات حدث `GITHUB_EVENT_PATH` الكاملة؛ لذلك **لا نعرف** أي عملية Git فشلت في التشغيل القديم.
- احتمال أن يكون SHA السابق في حدث `push` غير موجود محليًا، أو أن نطاق `rev-list` غير قابل للتحقق، **فرضية** وليست سببًا جذريًا مثبتًا.
- نجاح CI على `main` لا يُثبت تلقائيًا نجاح نفس نطاق Dependabot.

## 3. التغيير المنفَّذ في PR #678

- `scripts/verify_gitleaks_coverage.py`: تصنيف حالات إخفاق Git إلى مرحلة الالتزام المفحوص، ووجود الالتزام السابق للـpush، أو نطاق الالتزامات المطلوب فحصها؛ عرض اسم المرحلة ورمز الخروج فقط.
- التحقق من وجود SHA السابق ككائن `commit` عبر `git cat-file -e` قبل الاعتماد عليه في `before..after`.
- `tests/test_gitleaks_coverage.py`: اختبار الالتزام السابق المفقود، واختبار عدم ظهور مخرجات Git الخام في رسالة الفشل.
- **لم يتغير** إصدار Gitleaks أو شروط نجاحه أو نطاق الفحص أو صلاحيات GitHub Actions. في حالة الغموض يبقى فحص الأمن **FAIL / fail closed**؛ لا تجاوز ولا نجاح وهمي.

## 4. التحقق وحدوده

من نسخة موثوقة من المستودع، دون تشغيل نشر أو تغيير إعدادات:

```sh
python3 -m unittest discover -s tests -p 'test_gitleaks_coverage.py' -v
python3 -m unittest discover -s tests -p 'test_milestone_ledger.py' -v
python3 scripts/milestone_ledger.py --summary
```

**VERIFIED:** نجح [PR CI 44034375056](https://github.com/hamedonassar95/Devobs/actions/runs/44034375056) و[main CI 44034639484](https://github.com/hamedonassar95/Devobs/actions/runs/44034639484) على التزام الدمج. **UNVERIFIED:** لم يُعد إنتاج خطأ Dependabot التاريخي على هذا الالتزام؛ ينبغي أن يراجع المالك أي تشغيل جديد على فرع Dependabot قبل إعلان حل العطل نهائيًا. **لا تُعرض رموز أو سجلات خام أو نتائج أسرار في PR أو GitBook.** أي موافقة إنتاجية تتطلب قرارًا منفصلًا.

## مراجع الأدلة

- [التشغيل الفاشل في GitHub Actions](https://github.com/hamedonassar95/Devobs/actions/runs/43858556890)
- [الكود الحالي للتحقق من نطاق Gitleaks](https://github.com/hamedonassar95/Devobs/blob/main/scripts/verify_gitleaks_coverage.py)
- [وثائق Git الرسمية: git cat-file](https://git-scm.com/docs/git-cat-file)
- [وثائق Git الرسمية: git rev-list](https://git-scm.com/docs/git-rev-list)
