# إعداد تدقيق سياسة المستودع

يعمل `.github/workflows/repository-policy-audit.yml` كتدقيق للقراءة فقط لقواعد
حماية الفرع الافتراضي. يحتاج تفاصيل ruleset، بما فيها قائمة المتجاوزين؛ قد لا
يعيد GitHub هذه التفاصيل إلى الرمز الافتراضي `GITHUB_TOKEN`.

## إعداد الرمز

1. أنشئ fine-grained personal access token مخصصًا لمستودع `Devobs` فقط.
2. امنحه صلاحية المستودع **Administration: read** فقط، من دون صلاحيات كتابة.
3. أضفه في **Settings → Secrets and variables → Actions** باسم
   `POLICY_AUDIT_TOKEN`.
4. شغّل **Actions → Repository policy audit → Run workflow** على `main`، ثم
   تأكد من ظهور `Repository policy audit passed`.

عند غياب السر، يستخدم المسار `GITHUB_TOKEN` للقراءة العامة. إذا أخفى API حقل
`bypass_actors`، يتوقف التدقيق بنتيجة **inconclusive** ويشرح السر المطلوب؛ لا
يفترض أن القائمة فارغة ولا يغيّر إعدادات المستودع. لا تضع الرمز في ملفات Git
أو السجلات أو المحادثة، ودوّره أو ألغِه عند انتهاء الحاجة إليه.
