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


## حماية الدمج بمراجعة مستقلة (25 أكتوبر 2026)

**VERIFIED (GitHub REST API):** قاعدة `Protect main` الحالية مفعلة وتلزم فحص `validate`، لكن قيمة `required_approving_review_count` هي **0**. وجود PR ناجح الفحوص **لا** يساوي موافقة بشرية مستقلة. مثال موثق: PR #245 انتقل إلى Ready ثم اندمج بتاريخ 2026-10-25 رغم أن الهدف الأصلي إبقاؤه Draft؛ نجح نشر Pages التلقائي بعد الدمج. لا ينسب سجل GitHub الفعل تلقائيًا إلى وكيل معين؛ افحص سجل التدقيق والعمليات قبل الحكم على السبب.

**الإصلاح المقترح في الفرع المستقل:** أصبح مدقق المستودع يرفض القيمة صفر، والقيمة الناقصة، والقيمة غير الصحيحة، ويطلب موافقة PR واحدة على الأقل. هذا **كشف انحراف فقط**؛ ليس تعديلًا لقواعد GitHub، وليس بوابة CI ملزمة عند كل PR. تفعيل الضابط الفعلي يتطلب تعديل Ruleset من واجهة GitHub بموافقة منفصلة.

### احتياطات قبل التفعيل

1. **تحقق من وجود مراجع بشري ثانٍ مخول بالمراجعة وله Write أو أعلى.** لا يستطيع مؤلف PR الموافقة عليه بنفسه. إذا كان المستودع يُدار بحساب واحد فقط، فقد يؤدي فرض موافقة واحدة إلى حظر كل عمليات الدمج. لا تضبط العدد من 0 إلى 1 قبل ترتيب نموذج مراجعة قابل للتنفيذ.
2. راجع قائمة المتعاونين وحدود صلاحياتهم، وقواعد الاستثناء، ووصول التطبيقات. لا تمنح صلاحيات جديدة تلقائيًا ولا تعتبر موافقة Copilot بمثابة موافقة بشرية؛ وفق GitHub لا تُحتسب مراجعته ضمن متطلبات الموافقة.
3. عندما يتوفر مراجع مؤهل ويوافق مالك الحساب تحديدًا على تغيير السياسة، افتح [قواعد المستودع الحالية](https://github.com/hamedonassar95/Devobs/rules/24507159) ثم فعّل **Require a pull request before merging → Required approving reviews: 1**، مع إبقاء `validate` وCodeQL ومنع القوة/الحذف كما هي. راجع أثر `Dismiss stale approvals` و`Require approval of the most recent reviewable push` على الفريق قبل تفعيلهما.
4. بعد تغيير الإعداد، أعد قراءة GitHub Ruleset للتحقق من عدد المراجعات وباقي الشروط. نفّذ تدقيق السياسة عبر [Repository policy audit](https://github.com/hamedonassar95/Devobs/actions/workflows/repository-policy-audit.yml) باستخدام رمز القراءة المصرح به، ولا تصف خطأ الصلاحيات على أنه نجاح.
5. **لا تدمج فرع هذا الإصلاح قبل اتخاذ قرار بشأن المراجع.** تشغيل المدقق الجديد بعد الدمج على Ruleset الحالي سيفشل عمدًا (policy drift) إلى أن تصبح الموافقات مطلوبة.

### AI Intelligence: نموذج السيطرة المسموح

- **AI = جمع أدلة، تقييم مخاطر، توصيات، واقتراح تغييرات قابلة للمراجعة.** لا يمنح نموذج AI صلاحية الدمج أو النشر أو تعديل الأسرار أو الفوترة.
- حماية `main` الفعلية تتحقق من GitHub Ruleset وهوية المراجع المستقلة؛ لا تعتمد على نص من نموذج أو فحص CI وحده.
- مسارات `open_draft_pr` و`write_branch` تظل **PROPOSE_ONLY** في `scripts/devobs_intelligence/policy.py`، والانتقال إلى `APPROVED` محجوب حتى يتوفر تحقق خارجي من الهوية والموافقة.
- لا تفعّل استدلالًا مدفوعًا أو أتمتة تنفيذ ذاتي لمجرد أن الوثائق أو الاختبارات أصبحت خضراء.

### مراجع رسمية للتحقق

- [GitHub: Available rules for rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)
- [GitHub: Approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)
- [OWASP: AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [OWASP: Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [NIST: AI Risk Management Framework](https://www.nist.gov/itl/ai-risk-management-framework)

**الحالة:** VERIFIED هو تصميم الفاحص وبيانات قواعد GitHub المقروءة. UNVERIFIED هو وجود مراجع مستقل، أو تنفيذ تغيير قواعد الحماية، أو اختبار استدلال AI فعلي؛ لم تُغيّر إعدادات الحساب أو الفرع `main` في هذا التحضير.
