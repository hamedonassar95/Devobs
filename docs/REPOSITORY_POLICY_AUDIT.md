# إعداد تدقيق سياسة المستودع

يعمل `.github/workflows/repository-policy-audit.yml` كتدقيق للقراءة فقط لقواعد
حماية الفرع الافتراضي. يحتاج تفاصيل ruleset، بما فيها قائمة المتجاوزين؛ قد لا
يعيد GitHub هذه التفاصيل إلى الرمز الافتراضي `GITHUB_TOKEN`.

## إنشاء الرمز

1. افتح [إنشاء fine-grained token](https://github.com/settings/personal-access-tokens/new) من حساب GitHub الذي يملك المستودع.
2. اختر المستودع `Devobs` وحده ضمن **Repository access**.
3. ضمن **Repository permissions**، اجعل **Administration** على **Read-only** فقط، ولا تضف صلاحيات كتابة.
4. أنشئ الرمز وانسخه؛ لن تحتاج إلى وضعه في ملفات المشروع.

## إضافة الرمز وتشغيل التدقيق

1. افتح [أسرار Actions للمستودع](https://github.com/hamedonassar95/Devobs/settings/secrets/actions).
2. أضف **Repository secret** بالاسم `POLICY_AUDIT_TOKEN`، والصق الرمز في خانة القيمة، ثم احفظه. لا تضفه كسرّ لبيئة نشر.
3. افتح [سير تدقيق السياسات](https://github.com/hamedonassar95/Devobs/actions/workflows/repository-policy-audit.yml)، واختر **Run workflow** على `main`.
4. تأكد من ظهور `Repository policy audit passed`.

عند غياب السر، يستخدم المسار `GITHUB_TOKEN` للقراءة العامة. إذا أخفى API حقل
`bypass_actors` أو كانت صلاحية الرمز غير كافية، يتوقف التدقيق بنتيجة
**inconclusive**؛ لا يفترض أن القائمة فارغة ولا يغيّر إعدادات المستودع. لا تضع
الرمز في ملفات Git أو السجلات أو المحادثة، ودوّره أو ألغِه عند انتهاء الحاجة إليه.
