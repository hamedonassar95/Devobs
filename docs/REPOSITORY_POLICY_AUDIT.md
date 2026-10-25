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

قد يرفض GitHub REST API بعض الطلبات بسبب حدود الاستخدام عبر HTTP 403 أو 429؛
عند 429 افحص `Retry-After` أو `X-RateLimit-Reset` قبل إعادة المحاولة. راجع
[دليل GitHub الرسمي لحدود REST API](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api).


## حوكمة Devobs: مالك منفرد الآن وفريق مستقبلاً (25 أكتوبر 2026)

**VERIFIED (GitHub REST):** قواعد `Protect main` فعّالة، وتُلزم `validate` وتمنع الحذف والدفع بالقوة، لكن `required_approving_review_count=0`. هذا لا يوفر اعتمادًا بشريًا مستقلًا. في PR #245 تحولت المسودة إلى Ready ثم جرى الدمج، فأطلق `main` سير النشر. سجل الحساب وحده لا يثبت من نفذ الدمج.

### سياسة المدقق بحسب وضع الفريق

- **`--review-mode solo` (الافتراضي حاليًا):** يقبل 0 موافقات PR إذا بقيت الضوابط الأخرى ناجحة؛ يرفض الأعداد السلبية وغير الصحيحة والقيم الناقصة؛ ويعرض **تحذيرًا** بأن نجاح CI لا يمثل موافقة منفصلة. هذا يمنع تحويل تدقيق الأمان إلى فشل دائم لدى مالك واحد.
- **`--review-mode team` (مستقبلاً):** بعد إضافة مراجع بشري مستقل مؤهل، يشترط المدقق موافقة واحدة على الأقل. هذا لا يغيّر قواعد GitHub بنفسه، بل يكتشف اختلاف الحالة الحية عن السياسة المختارة.
- لا يعتبر قبول `solo` موافقة على الدمج الآلي، ولا يحوّل مدقق المستودع إلى منع قاطع للدمج: الحماية الفعلية تنفذها GitHub Rulesets/Environments. لا ترفع عدد المراجعات من صفر قبل تأمين مراجع ثانٍ؛ مؤلف PR لا يستطيع الموافقة على طلبه.

### بوابة النشر اليدوية المقترحة لمالك منفرد

يوجد سير نشر GitHub Pages يستخدم بيئة `github-pages` في ملفات المستودع الحالية. بعد التأكد من ملاءمة خطة GitHub ومسار النشر والاستعادة، يستطيع المالك إعداد **Required reviewers** على هذه البيئة وإضافة **حسابه الحالي** كمراجع وحيد، مع إبقاء **Prevent self-review غير مفعّل** ليتمكن من اعتماد تشغيل بدأه بنفسه. عندها ينتظر Job الذي يستخدم البيئة المراجعة قبل النشر. هذه ليست مراجعة مستقلة للشفرة؛ الغرض إعطاء المالك فرصة مراجعة نتائج CI قبل إصدار الإنتاج.

**تحذير:** هذا الإعداد لا يمنع الدمج إلى `main`؛ قد تُنفذ خطوات أخرى لا ترتبط بالبيئة. راجع بالتحديد وظائف `production-release` و`deploy-pages` وفحوص الصحة ومسار الاستعادة قبل تفعيل القاعدة. كما أن اشتراط المراجعة سيؤخر الاستعادة الآلية التي تستخدم `github-pages` حتى يوافق المالك؛ لا تغيّر إعدادات البيئة دون تجربة سيناريو الفشل والاستعادة. قد تحتاج سياسة الاستعادة إلى تصميم منفصل ومدروس.

خطوات المالك **بعد موافقة منفصلة على تغيير إعدادات النشر**: [Settings → Environments](https://github.com/hamedonassar95/Devobs/settings/environments) → `github-pages` → `Required reviewers` → حساب المالك الحالي → اترك `Prevent self-review` غير محدد → احفظ وتحقق من Job تجريبي مسموح به بعد فحص التكاليف والسياسات. **لم تُنفّذ أي من هذه التغييرات** في هذا الفرع.

### حدود AI Intelligence والأمان

- يسمح للوكيل بجمع أدلة CI وتحليل الحوادث وكتابة مقترحات على فروع مستقلة؛ لا تمنحه الموافقة على الدمج أو النشر أو الأسرار أو المصروفات.
- تبقى العمليات `open_draft_pr` و`write_branch` في سياسة AI Intelligence حالة `PROPOSE_ONLY`، و`APPROVED` محجوبة لحين تطوير تحقق مستقل من الهوية والموافقة.
- يُمنع ربط حسابات العملاء أو نقل وثائق GitBook الخاصة إلى مستودع عام قبل مراجعة البيانات. لا تربط تشغيل النماذج المدفوعة بمجرد نجاح CI.
- الانتقال إلى وضع الفريق يحتاج مراجعًا مستقلًا حقيقيًا، إذ لا يُعد حساب ثانٍ يتحكم به الشخص نفسه مراجعة مستقلة بالمعنى التشغيلي.

### مراجع رسمية

- [GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub: Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments)
- [GitHub: Managing environments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)
- [GitHub: Reviewing deployments](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/review-deployments)
- [OWASP: Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [NIST: AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

**الحالة:** مقترح مدقق على فرع منفصل. تم تأكيد `main` وقواعد الحماية عبر قراءة GitHub؛ حالة Reviewer لبيئة `github-pages` **غير متحققة** ولم تتغير. لا يوجد تشغيل إنتاجي أو تعديل Ruleset ضمن هذا الفرع.

### الاختبار المقترح قبل الموافقة على PR

شغّل من جذر المستودع على الفرع المستقل، دون توفير أي أسرار:

```bash
python3 -m unittest discover -s tests -p 'test_check_repo_policy.py' -v
python3 -m compileall -q scripts tests
```

يُتوقع اجتياز الاختبارات في وضعي `solo` و`team`. الوضع الفردي يقبل العدد 0 ويعرض تحذيرًا؛ أما وضع الفريق فيرفض العدد 0. هذا لا يثبت سلامة السياسة الحية؛ يجب تشغيل التدقيق الفعلي بعد أن يؤكد المالك إمكانية تطبيق قواعد المراجعة. لا تُشغّل أعمال نشر أو استدلال مدفوع كجزء من الفحص.

**الحالة الحالية:** توثيق وفاحص مقترحان على فرع مستقل؛ لم تُغيَّر سياسة GitHub الحية أو بيئة النشر أو صلاحيات التطبيقات، ولم يُشغَّل نشر إنتاجي بهذا الفرع.
