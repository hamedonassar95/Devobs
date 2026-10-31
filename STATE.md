# حالة مستودع Devobs

آخر تحديث: 2026-10-31 UTC؛ مزامنة إنجازات AI-9 v3 ودفتر الأدلة على فرع مراجعة مستقل.

## تكامل MCP لتوثيق OpenAI — فرع مراجعة غير مدموج (2026-10-31)

- **VERIFIED (repository configuration):** فرع `feature/read-only-docs-mcp-integration-20261031` يضيف خادم التوثيق الرسمي العام `https://developers.openai.com/mcp` إلى إعداد Codex المحلي الموثوق، ويوسع جرد التكاملات إلى سبعة مع اختبارات تمنع الادعاء بنجاح الاتصال.
- **UNVERIFIED (runtime):** لم يتم تشغيل جلسة Codex مرتبطة بهذا MCP أو اختبار handshake فعلي في حساب المالك؛ إعداد المسار لا يثبت تشغيله. الاستدعاءات إلى خادم التوثيق للقراءة فقط وليست استدلال AI مدفوعًا.
- **BLOCKED:** لا تُفعل OAuth أو OpenArt المدفوع أو خدمات SaaS أو أي تغيير في صلاحيات تطبيقات خارجية دون تفويض محدد. AI-9 وP01 يبقيان على حالهما.

## مستجدات 2026-10-31 — VERIFIED من GitHub (توثيق فقط)

- دُمج [PR #328](https://github.com/hamedonassar95/Devobs/pull/328) لتثبيت أدلة v3 وحدود الاختبار المستقل: head `05a6397d9f221995774025ed372fff8a4de62d08`، merge `44380997850387fbc748890075bc3d414792cc6a`؛ اجتاز CI على رأس PR في [run 41149965696](https://github.com/hamedonassar95/Devobs/actions/runs/41149965696).
- دُمج [PR #329](https://github.com/hamedonassar95/Devobs/pull/329) لإضافة مقيّم v3 مغلق يدوي فقط: head `1b951ba55b25e2a89e1044d25b0b801384cd1aee`، merge `82bc271d145d374f5f12c4c1517eb936c1826549`؛ اجتاز CI على رأس PR في [run 41150448628](https://github.com/hamedonassar95/Devobs/actions/runs/41150448628) واجتاز CI على `main` بعد الدمج في [run 41150776263](https://github.com/hamedonassar95/Devobs/actions/runs/41150776263).
- العينات المستقلة المحجوزة `20270601–20270604` **لم تُشغّل**. دمج أداة التقييم لا يمنح تفويضًا بتشغيلها. حالة AI-9 تبقى **FAIL / NOT AUTHORIZED**، وP01 **NO-GO / BLOCKED**.
- دُمج [PR #330](https://github.com/hamedonassar95/Devobs/pull/330) لتكامل OpenArt MCP اختياري خاضع للموافقة: head `fec9c6e5f4c4f36c72eea49797b9ca2f2d89037c`، merge `dfc360857ffda586166df03799a6bec4be73486d`؛ [CI 41152893449](https://github.com/hamedonassar95/Devobs/actions/runs/41152893449) نجح على الرأس. كان CI على main بعد الدمج لا يزال جاريًا عند الفحص؛ لا تصريح لتفعيل OAuth أو توليد وسائط أو نشر أو ادعاء اكتمال التكامل التشغيلي.
- **VERIFIED:** دُمج [PR #331](https://github.com/hamedonassar95/Devobs/pull/331) في `main` على `08ca255967a1390888cab7010bb618180e83dba6`، لتحديث سجل إنجازات #328–#330 دون تفعيل خدمات إضافية.
- لا تغييرات تشغيلية أو مفاتيح أو إعدادات خدمات أو نشر SaaS؛ التشغيل المحجوز والدمج والنشر الإنتاجي يتطلبان تفويض المالك حسب قواعد `AGENTS.md`.

### تحديث الحالة السابق
آخر تحديث: 2026-10-30 UTC؛ توثيق بوابة إنفاذ إنفاق Railway لـP01.

## الهدف الكبير

تطوير DevOps وذكاء تشغيلي تدريجيًا داخل المستودع، باستخدام مكونات محلية ومجانية حيثما أمكن، ودون ادعاء الجاهزية الإنتاجية قبل اجتياز أدلة مستقلة.

## الحالة الحالية

- المستودع: `hamedonassar95/Devobs`.
- **VERIFIED تاريخيًا (2026-10-28):** أظهر `git ls-remote origin refs/heads/main` أن `origin/main` عند `bd3e06d51ff2232a172755ffc3dcca85406fab51` وقت كتابة ذلك التحديث.
- **VERIFIED (2026-10-29):** رأس `main` الذي تمت مراجعته هو `f40793886f0ea81f95c0d58b7b4155fbc4ff6574`. تقرير المراجعة الشاملة: [`docs/DEVOPS_PRODUCTION_READINESS_2026-10-29.md`](docs/DEVOPS_PRODUCTION_READINESS_2026-10-29.md).
- **VERIFIED بعد دمج PR #289:** merge commit هو `7fbc0c88fb3e0362c119dd9ddc2a03478753d33d`. اجتاز CI و`validate`، ونشر GitHub Pages والتحقق من الموقع بنجاح في run [`40963935169`](https://github.com/hamedonassar95/Devobs/actions/runs/40963935169). تحليل CodeQL على `main` نجح في run [`40963934050`](https://github.com/hamedonassar95/Devobs/actions/runs/40963934050). كما اجتاز PR CI وCodeQL قبل الدمج.
- **VERIFIED:** دُمج PR #287 الخاص بمرحلة AI-7 عند `2026-10-28T23:28:06Z` إلى `main` بهذا الـmerge commit. رأس PR كان `91b6cd88892bdeb056c2eed37b0aaff29b2749f1`.
- AI-1 إلى AI-7 موجودة الآن في `main`: إدخال أحداث محلي، كشف إحصائي للشذوذ، تحليل احتمالي، توصيات ثابتة، تقارير اتجاه، تغذية راجعة محلية، ولوحة/API محليان للقراءة فقط.
- لوحة AI-7 مرتبطة بـ`127.0.0.1` وتقرأ لقطة محلية مجمعة؛ لا توفر كتابة أو تنفيذ توصيات، ولا تُضمّن في مخرجات الموقع الثابت.
- هذا لا يجعل المشروع SaaS أو منصة إنتاجية، ولا يرفع تقييم الجاهزية تلقائيًا.

## أدلة التحقق

- **PASS على رأس PR:** اجتاز GitHub Actions CI وCodeQL. فحص Vercel كان `success` على رأس PR وظهر أيضًا `success` على merge commit. لم يشغّل AI Code Review استدلالًا نموذجيًا مدفوعًا بسبب بوابة الميزانية؛ نجاح workflow لا يعني أن مراجعة النموذج نُفذت. هذا لا يثبت صحة التطبيق أو سلامة إنتاجه.
- **PASS محليًا قبل الدمج:** مجموعة Node لمراحل AI-1 إلى AI-7 وحارس الحوادث: 71 ناجحة، 0 فشل، 0 تخطٍ.
- **PASS بعد الدمج (2026-10-28):** أُعيد تشغيل مجموعة Node نفسها على `main` عند SHA `bd3e06d51ff2232a172755ffc3dcca85406fab51` — 71 ناجحة، 0 فشل، 0 تخطٍ.
- **PASS بصري محلي:** Chromium/Playwright وملف اصطناعي مؤقت؛ عرض RTL على 390×844 و1440×900 بلا تجاوز أفقي أو أخطاء صفحة. طلبات الصفحة الستة كلها إلى loopback، دون طلبات صفحة خارجية.
- **PASS:** `node --test tests/ai_dashboard_api.test.mjs` — 4 ناجحة؛ تشمل HTTP محليًا وحدود العرض والخصوصية وست حالات اصطناعية.
- **PASS تاريخيًا على main:** `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v` — 528 ناجحة، 18 متجاوزة، 0 فشل.
- **PASS:** `python3 scripts/check_action_pins.py` على 39 ملف سير عمل/قالب، و`python3 scripts/check_site.py`.
- **PASS:** فحص Node syntax، وتحليل YAML، والروابط النسبية، و`git diff --check`، وتجربة staging محلية أثبتت أن اللوحة خارج الموقع الثابت.
- Node المستخدم محليًا `v24.19.0`. لا يوجد `package.json`؛ لذا أوامر npm lint/typecheck غير متاحة. `actionlint` و`yamllint` غير متاحين. لم يُجر اختبار على جهاز هاتف فعلي.
- التطابق 6/6 يخص مجموعة قواعد اصطناعية صغيرة فقط، وليس دقة على حوادث حقيقية.

## المفتوح أو المعلّق

- الخادم بلا مصادقة مستقلة، ومخصص لجهاز موثوق محليًا فقط؛ لا تستخدمه عبر نفق أو شبكة مشتركة.
- لا توجد مجموعة حوادث حقيقية موسومة أو تغذية راجعة حقيقية مصرح بها؛ جودة التحليل والتوصيات خارج الاختبارات الاصطناعية **UNVERIFIED**.
- لم يثبت تشغيل صحي للإنتاج، أو جاهزية تجارية، أو عزل عملاء، أو فواتير/دفع. فحص المتصفح محلي ببيانات اصطناعية فقط؛ P01 SaaS والجاهزية الإنتاجية **NO-GO / BLOCKED**.
- **P01 budget gate — NO-GO / BLOCKED:** المالك اعتمد سقفًا إجماليًا مشروطًا قدره 100 دولار شهريًا. **VERIFIED من رد Railway Support بتاريخ 2026-10-30:** لا يوجد سقف واحد للفاتورة؛ Compute وAgent منفصلان ورسوم الاشتراك خارجهما؛ لا ضمان لأقصى تأخير/تجاوز؛ التخزين والنسخ يواصلان الفوترة بعد إيقاف الأحمال؛ السجلات في US West ولا يوجد التزام تعاقدي بمعالجة أوروبية فقط. لذلك Railway لا يفي بشرط السقف أو الإقامة، واختبار Compute-only المسجل مسبقًا لا يمكنه إثبات سقف الفاتورة الكاملة، وما زال **NOT RUN**. AWS new experience مرشح بحثي فقط: حده قبل الضريبة؛ **AWS يعيّن عنوان تواصل من الأردن إلى Stockholm (`eu-north-1`)**؛ قبول المالك لهذه المنطقة لم يُسجل. شمول التخزين/الرسوم والتجاوز والمعالجة التعاقدية ما زال غير محسوم. التفاصيل في [ملف الأدلة](docs/P01_RAILWAY_SPEND_ENFORCEMENT_EVIDENCE.md). لم يُنشأ حساب أو مورد ولم يحدث إنفاق؛ لا ينتقل P01 قبل اختيار المالك للمزوّد/المنطقة وإثبات حد إجمالي فعلي لكل البنود.
- لا توجد مرحلة AI-8 محددة أو معتمدة في الخطة الحالية.
- AI-9 يبقى **FAIL**. حسب قرار المالك، أُغلق البحث عن المقيّم التاريخي ولا نتابع استعادته؛ المقيّم الاصطناعي v2 هو مسار القياس التطويري الحالي، ونتائجه لا تغيّر البوابة أو الكاشف الإنتاجي.
- دُمجت عبر PR #289 تعديلات قفل الاعتمادات، والتحقق من توقيع Trivy، وبناء/اختبار/فحص صورة واحدة، وحارس التزامن المحلي للـAPI، وتحديث وثائق الجاهزية. صورة التطبيق لم تُنشر إلى registry، ولا يوجد API SaaS منشور.
- **PASS على رأس PR `76fc18b`:** CI run [`40963695235`](https://github.com/hamedonassar95/Devobs/actions/runs/40963695235) وCodeQL نجحا؛ شملت الفحوص Python وNode وPostgreSQL RLS وBandit وpip-audit وGitleaks وTerraform وبناء الحاوية وsmoke وتوقيع Trivy وفحصها. Vercel status نجح. أعيدت كتابة اختبارات عقد CI القديمة بعد أن كشف التشغيل الأول اعتمادها على اسم job سابق.
- **PASS بعد الدمج:** CI run [`40963935169`](https://github.com/hamedonassar95/Devobs/actions/runs/40963935169) شمل `validate` ونشر Pages والتحقق الإنتاجي على `7fbc0c8`. نجح CodeQL بشكل منفصل على `main` في run [`40963934050`](https://github.com/hamedonassar95/Devobs/actions/runs/40963934050).
- الحارس المحلي للـAPI لا يغني عن حد شامل على البوابة أو اختبار حمل؛ لا تزال حماية المعدل العامة وتنسيق العمال المتعددين غير مثبتين.

## الخطوة التالية بالضبط

استمر حسب البوابات الأربع، وكل خطوة مكتملة تُرفع وتُدمج بعد نجاح CI. بوابة CI والحاوية أُغلقت للنسخة الحالية؛ الباقي:

1. **AI-9 وجودة النموذج — FAIL / غير جاهز:** البحث عن المقيّم التاريخي مغلق حسب قرار المالك؛ المقيّم الاصطناعي v2 هو مسار التطوير الحالي. قرر المالك أن Precision تبقى على مستوى النوافذ بلا بوابة حوادث جديدة. مرشح Z-score/المتوسط المتحرك لم يُعتمد. أحدث قياس تطويري متعدد المقاييس للبذور `20270201`–`20270220` أعطى Precision/Recall/FPR للطبقة `6.1670% / 84.6667% / 2.5695%`; Precision أخفقت في `20/20` بذرة، لذلك لا اعتماد ولا تغيير للكاشف الإنتاجي. التفاصيل في [التسجيل](docs/AI9_MULTIMETRIC_CONFIRMATION_V1_PREREGISTRATION.md) و[النتائج](docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.md).
2. **سلامة CI والحاوية — COMPLETE للنسخة الحالية:** قفل الاعتمادات، توقيع Trivy، وبناء صورة واحدة وفحص smoke وTrivy على Docker image ID نفسه؛ PR CI وmain CI نجحا. لم تُنشر صورة التطبيق إلى registry.
3. **API والهوية وعزل المستأجرين — PARTIAL / BLOCKED:** حارس الطلبات المحلي موجود. Railway في أمستردام قيد التقييم فقط؛ لا توجد موارد حية. يلزم دليل إنفاذ سقف الميزانية، وحسم الإقامة التعاقدية، وقرارات الهوية والبيانات، ثم اختبار حدود البوابة والتحميل وRLS على staging مصرح به.
4. **التشغيل والاستعادة والاعتماد النهائي — BLOCKED:** يلزم رصد وتنبيهات وSLO، اختبار backup/restore وRPO/RTO، runbooks ومسؤول on-call ومراجعات الخصوصية والقانون والدعم، ثم قرار مستقل لأي pilot أو إطلاق.

هذا التقسيم لخطة التنفيذ الحالية، وليس تصريحًا بأن الجاهزية تحققت. الحالة العامة P01 والجاهزية الإنتاجية **NO-GO / BLOCKED**. لا توجد مرحلة AI-8 معتمدة.

## قرارات وحدود لا تتغير دون موافقة المالك

- لا خدمات أو مكتبات مدفوعة، ولا مفاتيح API أو استدلال LLM خارجي.
- لا استخدام بيانات تشغيل حقيقية قبل موافقة صريحة ومراجعة الخصوصية والاحتفاظ.
- التحليلات احتمالية وإرشادية؛ التوصيات اقتراح فقط ولا تنفيذ تلقائي.
- **توجيه المالك المستمر لهذا المسار:** كل خطوة مكتملة تُرفع في فرعها، تُفتح لها PR، وتُدمج بعد نجاح CI على رأسها، ثم ننتقل للخطوة التالية. لا تُترك الخطوات المكتملة محليًا فقط.
- الدمج على `main` قد ينشر الموقع الثابت عبر GitHub Pages، وهذا داخل مسار الدمج الذي طلبه المالك. هذا التوجيه لا يجيز نشر SaaS أو إنشاء موارد مدفوعة أو استخدام بيانات حقيقية أو تغيير أسرار وخدمات؛ هذه تحتاج موافقة محددة.
- تُنجز مرحلة واحدة كل مرة، وتُسجل أدلتها وحدودها قبل الانتقال للمرحلة التالية.

## ملحق AI-9 المحلي — 2026-10-30

- هذا ملحق تطويري محلي على الفرع `feature/ai9-synthetic-eval-v2`؛ لا يغيّر الأدلة التاريخية أو `main` ولا يرفع أو يدمج شيئًا. المقيّم الجديد في `scripts/ai_intelligence/ai9_synthetic_evaluation_v2.mjs` **ليس** استعادة للمقيّم التاريخي ولا إعادة تقييم رسمية.
- بروتوكول v2 الاصطناعي مثبت قبل القياس، بالبذرة `20261105` والافتراضات `before=0s`, `after=120s`, وإغلاق الحلقة بعد نافذتي هدوء. النتيجة: المرشح Precision 3.6408%، Recall 100%، FPR 5.2757%؛ بقيت بوابتا Precision وFPR **FAIL**، وحلقتان غير مؤهلتين عند نهاية العينة. [التقرير](docs/AI9_SYNTHETIC_EVALUATION_V2_RESULTS.md).
- خُطّط متعدد البذور قبل التشغيل، وثُبتت البذور `20261201`–`20261220`. المتوسط/التباين السكاني لـPrecision: baseline 1.6649% / 0.0005081 نقطة مئوية²؛ المرشح 3.4973% / 0.0165009 نقطة مئوية². المتوسط/التباين لـFPR: baseline 11.7757% / 0.0261140 نقطة مئوية²؛ المرشح 5.5080% / 0.0436793 نقطة مئوية². اجتازت Recall فقط 20/20؛ أخفقت Precision وFPR في 20/20 لكلا النسختين. [التسجيل](docs/AI9_SYNTHETIC_MULTI_SEED_V1_PREREGISTRATION.md) و[النتائج](docs/AI9_SYNTHETIC_MULTI_SEED_V1_RESULTS.md).
- التشخيص اللاحق للبذرة المستهلكة `20261105`: من 794 FP للمرشح، 527 في وصفات تحوي ضوضاء، و267 في نوافذ سالبة حول سلاسل أعطال اصطناعية؛ 715/794 تضمنت إشارة EWMA، و79 جاءت من قنوات Z-score/المتوسط المتحرك غير المعدلة. لم يثبت هذا سببًا واقعيًا عامًا. حلقتا المرشح المفتوحتان عند EOF في سلسلتين اصطناعيتين ضابطتين، دون إغلاق مُصطنع. [تحليل FP والحلقات ووحدات Precision](docs/AI9_SYNTHETIC_FP_AND_EPISODE_DIAGNOSTIC_V2.md).
- Precision على مستوى الحوادث عُرضت وصفيًا فقط لهذه البذرة: 0.3802% baseline و0.9634% للمرشح وفق تعريف مطابقة الحلقة المسجل في التقرير. لم تُطبق بوابة 80% على هذه الوحدة؛ قرار الوحدة/البوابة للمالك قبل أي تعديل.
- **الحالة الثابتة:** AI-9 **FAIL**؛ P01 **NO-GO / BLOCKED**؛ التقدير الفني 6/10 لا يتغير. لا تغيير إنتاجي أو push أو PR أو merge أو نشر. نتائج 20 بذرة تخص مولّدًا اصطناعيًا واحدًا فقط، ولا تثبت جاهزية عامة.

## قرار المالك ومرشح Z-score/المتوسط المتحرك — 2026-10-30

- **قرار المالك:** Precision gate تبقى على مستوى النوافذ؛ لا تُضاف بوابة حوادث. عتبة النافذة تبقى 80%، Recall 80%، وFPR 5% دون تغيير.
- **مرشح تطويري جديد:** `ai9-zma-2of3-alert-grouping-v1` يؤكد Z-score والمتوسط المتحرك إذا ظهرا في نافذتين من آخر ثلاث نوافذ مقاسة؛ يحتفظ بمرشح EWMA الحالي، ويبقي error-rate spike دون تعديل. تُجمع الإنذارات التي يفصلها حتى 120 ثانية في ملخص حلقة وصفي، من دون ملء النوافذ أو تغيير مقياس Precision.
- **القياس المقترن على البذور المعاد استخدامها 20261201–20261220:** متوسط Precision الأساسي/مرشح EWMA/المرشح الجديد = 1.6649% / 3.4973% / 3.1960%. متوسط FPR = 11.7757% / 5.5080% / 5.3445%. اجتياز البوابتين Precision وFPR: 0/20 للأساسي، 0/20 لمرشح EWMA، و0/20 للمرشح الجديد؛ Recall اجتاز 20/20 لكل نسخة. اجتاز FPR للمرشح الجديد بذرة واحدة فقط. البذور سبق استخدامها، لذلك النتيجة paired تطويرية وليست مستقلة.
- **الحالة:** المرشح الجديد لم يجتز Precision أو FPR؛ لا اعتماد أو نقل إلى الإنتاج. AI-9 **FAIL** وP01 **NO-GO / BLOCKED**. [التسجيل المسبق](docs/AI9_ZMA_GROUPING_CANDIDATE_V1_PREREGISTRATION.md)، [النتائج](docs/AI9_ZMA_GROUPING_CANDIDATE_V1_RESULTS.md).

## طبقة تأكيد ما بعد الكاشف — 2026-10-30

- سُجّل تصميم `ai9-post-detector-confirmation-v1` قبل التنفيذ والقياس. المكوّن المحلي `scripts/ai_intelligence/post_detector_confirmation.mjs` مستقل عن الكاشف: يؤكد استمرار القناة نفسها في 2 من 3 نوافذ أو تزامن مقاييس مختلفة للخدمة خلال 120 ثانية؛ يجمع التنبيهات ويغلق الحادثة بعد نافذتي هدوء مرصودتين. تعدد قنوات الكاشف على المقياس نفسه لا يُحسب استقلالًا. بذور `20270101`–`20270120` جديدة وفق فحص الشجرة وقت التسجيل.
- شُغّل المقيم المسجل مرة واحدة على Node محليًا، قبل أي تكامل. جدول المقارنة ومتوسطات 20 بذرة والتباين السكاني موثقة في [التقرير](docs/AI9_POST_DETECTOR_CONFIRMATION_V1_RESULTS.md) و[نتيجة JSON ذات البصمات](docs/AI9_POST_DETECTOR_CONFIRMATION_V1_RESULTS.json). Precision/Recall/FPR: الأساسي `1.6594% / 100% / 11.8176%`؛ مرشح EWMA `3.4172% / 100% / 5.6392%`؛ المرشح مع الطبقة `8.4783% / 82% / 1.7708%`. مرّ Recall وFPR للطبقة في `20/20`، لكن Precision في `0/20`.
- مقابل مرشح EWMA: Precision زادت `5.0611` نقطة مئوية، وRecall نقصت `18` نقطة؛ أي `3.56` نقطة Recall مفقودة لكل نقطة Precision، و`108/600` نافذة إيجابية فائتة. بقيت `6/120` حالات أعطال بلا بداية حادثة مؤكدة خلال نافذة المطابقة، و`27` حادثة مفتوحة عند نهاية العينات. المسار متعدد المقاييس مغطى بالعقود فقط؛ المولد أحادي المقياس لكل خدمة.
- الانتشار الاصطناعي `0.198939%`. عند هذا الانتشار، Precision النظري الأعلى مع Recall=100% هو `3.8339%` عند FPR=5%، و`79.9467%` عند FPR=0.05%. ملفات التقييم المتتبعة صناعية/غير مراجعة أو أمثلة تقارير، ولا توجد سلسلة حوادث تشغيلية ممثلة نستطيع منها تقدير الانتشار الحقيقي.
- تحقق محلي: اختبارات العقد `14/14`، ومجموعة Node كاملة `102/102`، وفحوص الصياغة و`git diff --check` نجحت. ثبت المكوّن في commits محلية `0956853` و`6420c03`، وسجل النتائج في commit توثيق مستقل لاحقًا. لم يتغير كاشف الإنتاج أو البوابات، ولم يحدث push أو PR أو merge.
- **الحالة لا تتغير:** AI-9 **FAIL** لأن Precision أقل كثيرًا من 80% في كل البذور؛ P01 **NO-GO / BLOCKED**. الطبقة نموذج منفصل وليست جاهزة للدمج التشغيلي: ينقصها service ID/mapping حقيقي، قياس متعدد المقاييس، حالة durable واستعادة/تكرار delivery آمنة، وربط التنبيهات وتشغيلها، وبيانات حوادث/ضوابط موسومة ومصرح بها.

## تقييم تطويري متعدد المقاييس لطبقة التأكيد — 2026-10-30

- سُجلت السياسة `ai9-multimetric-confirmation-v1` قبل توليد البيانات. جُمّدت 20 بذرة جديدة `20270201`–`20270220`، مع 56 خدمة اصطناعية × 3 مقاييس، و`45,240` نافذة لكل بذرة (`90` موجبة و`45,150` سالبة). مكوّنات التنفيذ في `e81ea73`, `fa38182`, `eafa438`, و`d25a24e`؛ التسجيل في [الخطة المسجلة](docs/AI9_MULTIMETRIC_CONFIRMATION_V1_PREREGISTRATION.md).
- شُغّل المقيم مرة واحدة بعد تجميد المولّد والمقيم والاختبارات. متوسط Precision/Recall/FPR: الكاشف الأساسي `1.9997% / 82.5556% / 8.0656%`; المرشح `ai9-ewma-noise-candidate-v1` `3.5644% / 84.6667% / 4.5673%`; المرشح مع طبقة التأكيد `6.1670% / 84.6667% / 2.5695%`. تباينات المتوسطات عبر نسب البذور (سكاني، pp²)، الأعداد المفقودة، بصمات المدخلات، وتفاصيل البذور في [التقرير](docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.md) و[JSON](docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json).
- مقارنة الطبقة بمرشح EWMA أعطت `+2.6027` نقطة مئوية Precision بلا فقد Recall مقاس (`0` نافذة موجبة إضافية مفقودة، `0/20` بذور فقدت Recall)؛ وانخفض FPR بمقدار `1.9978` نقطة. بقي Precision دون `80%` في `20/20`، لذلك لا ينجح أي إصدار في البوابة الكاملة. هذه مقارنة اصطناعية داخل عائلة مولّد واحدة وليست دليلًا عامًا أو إعادة تقييم AI-9 الرسمي.
- بقيت `150` حلقة مفتوحة عند EOF للطبقة في جميع البذور العشرين؛ لا تضيف العينات نوافذ هدوء مصطنعة. إسناد التأكيد إلى الاستمرار `16,315` وإلى تزامن مقاييس مختلفة `14,239` نافذة، مع تداخل `5,827` بين السببين. لا يُجمع الرقمان كحالات منفصلة.
- الانتشار الاصطناعي `90/45,240 = 0.198939%`. عند Recall كامل، أقصى Precision نظريًا عند FPR `5% / 1% / 0.1% / 0.05% / 0.01% / 0%` هو `3.8339% / 16.6205% / 66.5927% / 79.9467% / 95.2230% / 100%`. لا يحتوي المستودع على corpus تشغيلي ممثل وموسوم يمكن تقدير الانتشار الواقعي منه.
- وقت كتابة هذا التقييم لم يكن يوجد سوى checkpoint JSON محلي. أُضيف لاحقًا نموذج ملف محلي يجمع checkpoint وoutbox ذريًا في [مفكرة التأكيد](docs/AI9_CONFIRMATION_JOURNAL_V1_IMPLEMENTATION.md)، لكنه ليس مخزنًا مستضافًا أو متعدد العمال ولا يرسل تنبيهات. لا يزال `service_id` غير موثوق في مخطط الأحداث، ولا يوجد ربط إنتاجي للمقاييس بالخدمات أو مجموعة حوادث واقعية مصرح بها/holdout ممثل.
- التحقق المحلي قبل القياس: Node suite `104/104`، الاختبارات المركزة `2/2`، syntax checks و`git diff --check` PASS. ملف النتائج يحفظ المجاميع وبصمات canonical لكل seed فقط، بلا سلاسل أو قيم خام. لم يتغير كاشف الإنتاج أو العتبات أو تعريف البوابة.
- **الحالة لا تتغير:** AI-9 **FAIL**؛ P01 **NO-GO / BLOCKED**؛ التقدير الفني `6/10`. لا يُعتمد المرشح ولا تُفعّل الطبقة إنتاجيًا.

## عقد checkpoint لطبقة التأكيد — 2026-10-30

- سُجل عقد `ai9-confirmation-checkpoint-v1` قبل التنفيذ في [التسجيل](docs/AI9_CONFIRMATION_CHECKPOINT_V1_PREREGISTRATION.md)، على `origin/main` عند `e76e2bd83ec3738998cb560fa890a0a47e40059c`.
- أضافت وحدة [طبقة التأكيد](scripts/ai_intelligence/post_detector_confirmation.mjs) checkpoint JSON بإصدار واضح، واستعادة مشروطة بتطابق إصدار السياسة، وترتيبًا حتميًا للمفاتيح، وبصمة/نتيجة آخر نافذة لكل خدمة. إعادة النافذة الأخيرة المطابقة تعيد النتيجة المخزنة بلا تغيير حالة؛ إعادة الوقت نفسه بمحتوى مختلف تفشل بـ`idempotency_conflict`؛ الأقدم يبقى مرفوضًا.
- اختبارات العقد [الجديدة](tests/post_detector_confirmation_checkpoint.test.mjs) `7/7`، و`node --test tests/*.test.*` `111/111`؛ فحوص الصياغة و`git diff --check` PASS. لا تقييم جودة أو بذور أو بيانات حقيقية في هذه الخطوة.
- هذا العقد **تسلسل واستعادة محليان فقط**. أضيفت لاحقًا مفكرة تطويرية ذرية بملف واحد؛ لا توفر تعدد عمال/مضيفين ولا exactly-once أو توصيلًا حيًا. تبقى حماية/احتفاظ وهوية خدمة واختبارات استعادة تشغيلية وحدود تشغيل موثقة مطلوبة قبل أي تكامل حي. التفاصيل في [سجل التنفيذ](docs/AI9_CONFIRMATION_CHECKPOINT_V1_IMPLEMENTATION.md) و[مفكرة outbox](docs/AI9_CONFIRMATION_JOURNAL_V1_IMPLEMENTATION.md).
- **الحالة لا تتغير:** AI-9 **FAIL**، P01 **NO-GO / BLOCKED**، والتقدير الفني `6/10`. لا تغييرات على الكاشف الإنتاجي أو تعريف البوابات.

## التسجيل المسبق لمفكرة checkpoint وoutbox — 2026-10-30

- سُجلت الخطوة التالية قبل التنفيذ في [عقد مفكرة التأكيد v1](docs/AI9_CONFIRMATION_JOURNAL_V1_PREREGISTRATION.md)، على `origin/main` عند `71dbdbb958edec0238a0a601db4bc0243529aeca`.
- النطاق محصور في تخزين محلي تطويري يجمع checkpoint وحوادث outbox في استبدال ذري واحد؛ لا تعديل للكاشف أو البوابات، ولا تكامل حي أو بيانات حقيقية. العقد المقترح single-writer وبحد 8 MiB و10,000 حدث، وسيُختبر في مجلد مؤقت.
- هذا تسجيل فقط: لم يبدأ التنفيذ أو تشغيل اختبار/مقيّم في هذه الخطوة. AI-9 **FAIL** وP01 **NO-GO / BLOCKED**.

## مفكرة checkpoint وoutbox التطويرية — 2026-10-30

- نُفذ التسجيل السابق على فرع `feature/ai9-confirmation-outbox-v1` من `origin/main` `71dbdbb958edec0238a0a601db4bc0243529aeca`؛ commit التسجيل `1f7d048` سبق كود التنفيذ.
- أُضيفت وحدة [`post_detector_confirmation_journal.mjs`](scripts/ai_intelligence/post_detector_confirmation_journal.mjs): تستعيد checkpoint طبقة التأكيد، وتخزنها مع أحداث فتح/إغلاق/انقطاع الحوادث في استبدال ذري واحد؛ قفل حصري، `0600`، مجلد خاص موجود مسبقًا، ومعرفات أحداث حتمية. الإقرار يحذف pending IDs ذريًا، وإعادة آخر نافذة لا تعيد إحياء أحداث أُقرت.
- حدود الاختبار المسجلة: 8 MiB، 10,000 حدث pending، كاتب متعاون واحد. التسليم اللاحق at-least-once ويحتاج المستهلك لإزالة التكرار حسب `event_id`؛ قفل متروك بعد تعطل يفشل مغلقًا ولا يُسرق تلقائيًا.
- الاختبارات الجديدة [`post_detector_confirmation_journal.test.mjs`](tests/post_detector_confirmation_journal.test.mjs) `10/10`، ومجموعة Node `121/121`، واثنان من عقود CI وواحد release gate PASS؛ فحص تثبيت Actions على 39 ملفًا و`git diff --check` PASS. سجل الأدلة الكامل في [تقرير التنفيذ](docs/AI9_CONFIRMATION_JOURNAL_V1_IMPLEMENTATION.md).
- هذا ملف تطوير محلي فقط؛ لا ربط بـPostgreSQL أو API أو مزود تنبيهات ولا تكامل حي. لا يدعم تعدد العمال/المضيفين أو تشفيرًا أو أصالة تشفيرية أو سياسة احتفاظ.
- فُتحت PR #301 عند الرأس `a12d5ceee7540104355e86446a800667c0abdb11`؛ نجح CI [`41065078966`](https://github.com/hamedonassar95/Devobs/actions/runs/41065078966) وCodeQL [`41065073727`](https://github.com/hamedonassar95/Devobs/actions/runs/41065073727)، ونجح فحص Vercel للمعاينة. دُمجت في `main` عند `2470f15b11159396bca72a57ddceed4bffc30409`.
- بعد الدمج نجح CI على `main` في [`41065461283`](https://github.com/hamedonassar95/Devobs/actions/runs/41065461283)، بما فيه نشر Pages و`verify-production`؛ ونجح CodeQL على `main` في [`41065458495`](https://github.com/hamedonassar95/Devobs/actions/runs/41065458495).
- **الحالة لا تتغير:** AI-9 **FAIL**، P01 **NO-GO / BLOCKED**، والتقييم الفني `6/10`. لم تُشغّل أي بوابة جودة أو بيانات حقيقية ولم يتغير الكاشف أو تعريف البوابات.

## موصل الكاشف بطبقة التأكيد — 2026-10-30

- سُجل تصميم `ai9-detector-confirmation-adapter-v1` قبل التنفيذ في [التسجيل المسبق](docs/AI9_DETECTOR_CONFIRMATION_ADAPTER_V1_PREREGISTRATION.md)، أساسه `origin/main` عند `498e629dcd0c2d915226444e736c30aff8e97b69`.
- أضيف [`post_detector_confirmation_adapter.mjs`](scripts/ai_intelligence/post_detector_confirmation_adapter.mjs) ليشغّل محلل المقاييس الحالي ثم يمرر أسماء الإشارات فقط إلى طبقة التأكيد أو مفكرة الـoutbox. يرفض أنواع الأحداث الأخرى، والتكرار، والطوابع غير المتزامنة قبل تعديل حالة التأكيد. لا يستنتج هوية الخدمة من بيانات الحدث ولا يثبت هوية/صلاحية المرسل.
- يغطي [اختبار العقد](tests/post_detector_confirmation_adapter.test.mjs) مسار الكاشف الحقيقي مع بيانات اصطناعية، والإشارة المعزولة، والاستمرار، والتزامن بين مقياسين، والرفض قبل تغيير الحالة، وإعادة تشغيل المفكرة دون إعادة إنشاء حدث مُقَرّ. لم تُحسب مقاييس جودة أو بوابات ولم تُستخدم بذور AI-9.
- تحقق محليًا: الاختبارات المركزة `6/6`؛ مجموعة Node `127/127`؛ عقد CI `2/2` وعقد بوابة الإصدار `1/1`؛ فحص 39 pin، و`check_agent_spec.py` و`check_site.py` وفحوص الصياغة و`git diff --check` نجحت. مجموعة Python الكاملة حاولت تشغيل 534 اختبارًا لكنها أخفقت في تهيئة اختبار staging لغياب حزمة `psycopg` في البيئة؛ هذه الحزمة غير لازمة لتغيير JavaScript، وتظل نتيجة Python CI المستضافة مطلوبة.
- أُدرج فحص الموصل واختباره في Node job. على رأس التنفيذ `ca4d744037a6f2694d85a52a82c8d71d7dc5839e` نجح PR #303 CI في run [`41067497186`](https://github.com/hamedonassar95/Devobs/actions/runs/41067497186)، ونجح CodeQL في run [`41067491831`](https://github.com/hamedonassar95/Devobs/actions/runs/41067491831)، ونجحت معاينة Vercel. هذه النتائج سبقت تحديث هذا السجل؛ يلزم نجاح الفحوص المطلوبة على رأس PR النهائي قبل الدمج، ولا ندعي بعد نتيجة على `main`.
- الحدود: نموذج تركيب محلي فقط؛ `serviceId` من caller خارجي ولا يُوثق أو يُربط بخدمة حقيقية هنا. لا مصادقة أو حدود مستأجرين أو توصيل تنبيهات فعلية، والمفكرة تبقى single-writer محلية. لا استخدام شبكة أو خدمة أو بيانات حقيقية.
- **الحالة لا تتغير:** AI-9 **FAIL**، P01 **NO-GO / BLOCKED**، وبوابات القياس ثابتة. مراجعة مصدر الهوية وربط الخدمة اللاحقة موثقة في [تدقيق الربط](docs/AI9_AUTH_SERVICE_INTEGRATION_AUDIT.md)؛ لم يثبت وجود مسار موثوق بين runtime الـNode وواجهة Python الحالية.

## تدقيق ربط هوية الخدمة بـ AI-9 — 2026-10-30

- روجع `main` عند `72e1a5f2332441c6e4e04beab054e4e97458bc78` قراءة فقط. موصل AI-9 في JavaScript لا يستدعى من تطبيق؛ مستهلكه التنفيذي الوحيد هو اختبار العقد. موثق في [تدقيق الربط](docs/AI9_AUTH_SERVICE_INTEGRATION_AUDIT.md).
- في مسار Python، متحقق OIDC يعيد `AuthenticatedPrincipal`، وواجهة API الحالية للقراءة فقط وتخوّل tenant/project عبر `OfflineTenantGate` وPostgreSQL RLS. لا يوجد سجل tenant/service أو endpoint يجمع هذه الهوية مع موصل Node.
- القرار الفني المقترح للمراجعة: إبقاء التحقق من الهوية وتخويل الخدمة عند حد Python الحالي، وإضافة سجل خدمة tenant-scoped تحت RLS قبل تكامل AI-9. يبقى اختيار استضافة آلة الحالات مفتوحًا: نقلها إلى Python لتوحيد حد الهوية، أو تعريف بروتوكول داخلي موثّق ومصادق عليه لعملية Node منفصلة. لم ينفذ أي خيار في هذه المراجعة.
- لا يُعامل callback `authorizeService` أو نجاح الاختبارات المحلية كإثبات مصادقة. لا خدمة أو هوية مزود أو قاعدة بيانات حية أو بيانات حقيقية استُخدمت.
- **الحالة لا تتغير:** AI-9 **FAIL** وP01 **NO-GO / BLOCKED**. لا قياس جودة، ولا تعديل للكاشف أو العتبات أو تعريف البوابات.

## حد تفويض الخدمة لموصل التأكيد — 2026-10-30

- سُجل مسبقًا العقد `ai9-confirmation-service-auth-boundary-v1` على `origin/main` عند `d7a9ab663bc26ab54b8dcbd07c4e8072844f26af` في [وثيقة التسجيل](docs/AI9_CONFIRMATION_SERVICE_AUTH_BOUNDARY_V1_PREREGISTRATION.md)، قبل أي تعديل تنفيذي.
- يتطلب موصل [`post_detector_confirmation_adapter.mjs`](scripts/ai_intelligence/post_detector_confirmation_adapter.mjs) الآن اعتمادين بالضبط: طبقة التأكيد و`authorizeService`. بعد فحص شكل الغلاف وصياغة `serviceId` فقط، يرسل كائنًا مجمدًا لا يحوي إلا معرّف الخدمة إلى callback. لا تُفحص الطوابع الزمنية أو أحداث المقاييس إلا بعد موافقة حرفية `true`. الرفض والقيمة غير المنطقية والأخطاء تفشل مغلقًا بأكواد ثابتة، ولا تمرر تفاصيل الخطأ ولا تغيّر حالة التأكيد.
- اختبار العقد [`post_detector_confirmation_adapter.test.mjs`](tests/post_detector_confirmation_adapter.test.mjs) يغطي callback مسموحًا/مرفوضًا/غير منطقي/استثنائيًا، وترتيب التفويض قبل فحص timestamp أو محتوى الأحداث، وعدم كشف تفاصيل callback. لا يثبت أي اختبار هوية حقيقية أو صحة سياسة تفويض.
- تحقق محليًا: الاختبار المركّز `8/8`، مجموعة Node `129/129`، عقد CI `2/2` وrelease gate `1/1`، تثبيت 39 ملف Actions، `check_agent_spec.py` و`check_site.py`، فحوص الصياغة و`git diff --check` كلها PASS. نتائج CI/CodeQL/Vercel وmain CI/Pages ستضاف بعد اكتمالها.
- سجل التنفيذ وحدوده في [تقرير التطبيق](docs/AI9_CONFIRMATION_SERVICE_AUTH_BOUNDARY_V1_IMPLEMENTATION.md). لا مزود هوية أو token أو سجل خدمات أو ربط مستأجرين أو شبكة أو قاعدة بيانات؛ callback المحلي مجرد نقطة ربط ويجب أن يغلق على سياق موثوق قبل أي تكامل.
- **الحالة لا تتغير:** AI-9 **FAIL** وP01 **NO-GO / BLOCKED**؛ لم تُشغّل مقاييس الجودة أو بذور التقييم، ولم يتغير الكاشف أو العتبات أو تعريف البوابات. هذه الخطوة لا تفعّل staging أو إنتاجًا.

## تسجيل مسبق لسجل خدمات tenant-scoped تحت PostgreSQL RLS — 2026-10-30

- سُجل تصميم `ai9-tenant-service-registry-rls-v1` قبل التنفيذ في [التسجيل المسبق](docs/AI9_TENANT_SERVICE_REGISTRY_RLS_V1_PREREGISTRATION.md)، على `main` عند `c778fe4e7ff9f26e7cd2d7f4b9bba1623bc9de6f`.
- العقد يضيف migration منفصلًا `002_service_registry.sql` بعد `001_tenant_rls.sql`، وجدول `service_registry` بمفتاح `(tenant_id, project_id, service_id)` وسياسة قراءة RLS تربط tenant وsubject بالعضوية. واجهة التخويل المقترحة `PostgresTenantStore.authorize_service(subject, tenant, project, service_id)` تقرأ tuple مسجلًا بصلاحية قراءة فقط وتفشل مغلقًا عند خلل المخطط/الدور.
- تجارب العقد المخططة تشمل تكرار معرف الخدمة واسم المشروع بين مستأجرين، ومنع subject/tenant/project/service غير المطابق، ورفض الكتابة، وانجراف الصلاحيات والسياسات، وفحص الأقفال، باستخدام PostgreSQL 17 المؤقت في GitHub Actions فقط.
- هذا تسجيل تصميم فقط؛ لم يُنفذ SQL أو كود ولم يُشغّل اختبار أو تقييم في هذه الخطوة. لا route أو تكامل Node/Python أو خدمة حية. AI-9 **FAIL** وP01 **NO-GO / BLOCKED** بلا تغيير.

## تنفيذ سجل خدمات tenant-scoped تحت PostgreSQL RLS — 2026-10-30

- اكتمل التنفيذ المسجل في فرع `feature/ai9-tenant-service-registry-rls-v1` فوق `main` عند `c778fe4e7ff9f26e7cd2d7f4b9bba1623bc9de6f`. أضيف migration مستقل `deploy/postgres/002_service_registry.sql`؛ لم يتغير `001_tenant_rls.sql`.
- أضيف `PostgresTenantStore.authorize_service(subject, tenant, project, service_id)` لاستعلام tuple مطابق ضمن هوية tenant/subject محددة في معاملة قراءة فقط. الغياب أو عدم العضوية يعيد `False`، والمدخل غير الصالح يرفض بـ`access_denied`، وأخطاء المخطط/الدور/قاعدة البيانات تفشل مغلقًا. فحص الجاهزية والأقفال يتحققان الآن من `project_ci` و`memberships` و`service_registry` وسياساتهم الثلاث الدقيقة.
- اختبارات `tests/test_postgres_rls_integration.py` تغطي أسماء المشاريع/الخدمات المتطابقة بين المستأجرين، رفض العضوية أو tuple غير المطابق، المدخلات الخبيثة، الصلاحيات والكتابة وRLS وانجراف السياسة والأقفال. على PostgreSQL مؤقت محلي v17.11: `python3 -m unittest discover -s tests -p 'test_postgres_rls_integration.py' -v` — `Ran 21 tests ... OK`. مجموعة Python الكاملة على الاعتمادات المقفلة: `python3 -m unittest discover -s tests -v` — `Ran 543 tests ... OK (skipped=21)`. التفاصيل في [تقرير التنفيذ](docs/AI9_TENANT_SERVICE_REGISTRY_RLS_V1_IMPLEMENTATION.md).
- هذه خطوة تخزين/تخويل داخلية فقط؛ لا يوجد مسار API يناديها، ولا طريقة تشغيلية لتسجيل الخدمات، ولا توصيل بين Node وPython. CI المستضاف وCodeQL على الرأس النهائي لم يُتحققا بعد في لحظة هذا السجل.
- لا تقييم AI-9 ولا تعديل للكاشف أو البوابات. الحالة ثابتة: AI-9 **FAIL**، P01 **NO-GO / BLOCKED**، النموذج التقني **6/10**. لا قاعدة بيانات مستضافة أو نشر أو بيانات حقيقية.

## أدلة ما بعد دمج سجل خدمة AI-9 — 2026-10-30

- دُمج PR #306 عند `83f729b6aa2fff0f617e6a38a1a6bfc0c5315c26`، وكان رأسه `c59f88e3db4b44c991152f931c4ab2875ff75c42`. نجح CI للـPR في [run 41075077622](https://github.com/hamedonassar95/Devobs/actions/runs/41075077622)، بما فيه `postgres-rls` وPython وsecurity و`validate`؛ ونجح CodeQL في [run 41075072434](https://github.com/hamedonassar95/Devobs/actions/runs/41075072434). نجحت معاينة Vercel.
- على commit الدمج `83f729b6aa2fff0f617e6a38a1a6bfc0c5315c26` نجح main CI في [run 41075299391](https://github.com/hamedonassar95/Devobs/actions/runs/41075299391) وCodeQL في [run 41075298698](https://github.com/hamedonassar95/Devobs/actions/runs/41075298698). شمل CI نجاح `postgres-rls` وPython وsecurity ومسح صورة الحاوية وsite-contract و`validate`، ثم نشر GitHub Pages والتحقق `verify-production`.
- هذه أدلة مستودع وCI ونشر الموقع الثابت فقط. لم يُنشأ PostgreSQL مستضاف أو endpoint أو خدمة مدفوعة، ولم تُنقل بيانات. AI-9 **FAIL** وP01 **NO-GO / BLOCKED**، والتقييم التقني بقي **6/10**.

## واجهة تخويل خدمة AI-9 عبر Python وRLS — 2026-10-30

- سُجلت سياسة `ai9-python-service-authorization-api-v1` قبل التنفيذ في [التسجيل المسبق](docs/AI9_SERVICE_AUTHORIZATION_API_V1_PREREGISTRATION.md)، ودُمج PR #308 عند `6f16e2f923536526ef563377f2dc6775c4dc370c`. على رأس PR نجحت `validate` و`postgres-rls` و`security` و`terraform-validate` وفحص الصورة و`site-contract` في [CI run 41079417300](https://github.com/hamedonassar95/Devobs/actions/runs/41079417300) وCodeQL لكل من Python وJavaScript/TypeScript وActions في [run 41079412299](https://github.com/hamedonassar95/Devobs/actions/runs/41079412299)؛ تخطت اختبارات Python وNode لأن PR كان توثيقيًا. نجحت معاينة Vercel. بعد الدمج نجحت `validate` و`postgres-rls` و`security` و`terraform-validate` وفحص الصورة و`site-contract` في [main CI run 41079655634](https://github.com/hamedonassar95/Devobs/actions/runs/41079655634)، وCodeQL في [run 41079654362](https://github.com/hamedonassar95/Devobs/actions/runs/41079654362)؛ نجح نشر Pages و`verify-production`، بينما تخطت اختبارات Python وNode لأن التغيير كان تسجيلًا توثيقيًا.
- أضيف المسار `GET /v1/tenants/{tenant}/projects/{project}/services/{service_id}/authorization` في `scripts/devobs_intelligence/api_app.py`. لا يعمل إلا بعد التحقق من bearer token الحالي، ويأخذ subject من principal الموثق والنطاق من المسار، ثم يستدعي `PostgresTenantStore.authorize_service` مرة واحدة. فقط القيمة المنطقية الحرفية `True` تعيد `204` فارغًا؛ الرفض موحد `403`، ومشكلات التخزين/النتائج غير المنطقية تفشل مغلقًا بـ`503`. المسار محمي بحد المعدل والتزامن الموجودين، ولا يكتب السجل أو يستقبل مقاييس أو يشغل كاشف AI-9.
- أضيفت اختبارات عقد في `tests/test_intelligence_api_security.py` واختبار WSGI موقّع على PostgreSQL RLS في `tests/test_postgres_rls_integration.py`. محليًا: `python3 -m unittest discover -s tests -p 'test_intelligence_api_security.py' -v` — 17/17 نجاح؛ اختبار PostgreSQL المركّز على PostgreSQL 17 مؤقت — 22/22 نجاح؛ مجموعة Python — `Ran 549 tests ... OK (skipped=22)`، وشغلت حالات PostgreSQL المنفصلة دون تخطٍ.
- دُمج التنفيذ في PR #309 عند `60d64f14ee63c94806674b1a537d0180869b41d0`. نجح رأس PR في [CI run 41081064798](https://github.com/hamedonassar95/Devobs/actions/runs/41081064798) و[CodeQL run 41081060607](https://github.com/hamedonassar95/Devobs/actions/runs/41081060607)، بما فيه Python وPostgreSQL RLS وsecurity و`validate`؛ تخطت Node tests لأن التعديل Python فقط. بعد الدمج نجح [main CI run 41081294563](https://github.com/hamedonassar95/Devobs/actions/runs/41081294563) و[CodeQL run 41081293399](https://github.com/hamedonassar95/Devobs/actions/runs/41081293399)، ونُشر Pages ونجح `verify-production`.
- تقرير التنفيذ وحدوده في [AI9_SERVICE_AUTHORIZATION_API_V1_IMPLEMENTATION.md](docs/AI9_SERVICE_AUTHORIZATION_API_V1_IMPLEMENTATION.md). هذا يربط هوية Python الموثقة بسجل RLS، لكنه لا يربط مصدر مقاييس أو عملية Node بآلة AI-9. يلزم تسجيل تشغيل خدمة مستقل؛ و`devobs_migrator` يبقى للمخططات فقط، دون صلاحية إدراج خدمات مضافة هنا.
- لا قاعدة بيانات مستضافة أو OIDC حي أو endpoint عام أو بيانات حقيقية أو موارد مدفوعة. لم يُجر أي benchmark أو تقييم AI-9 ولم تتغير العتبات أو الكاشف. الحالة: AI-9 **FAIL**، P01 **NO-GO / BLOCKED**، التقييم التقني **6/10**.

## تدقيق ضريبة AWS للأردن — 2026-10-30

- فُحصت صفحة [AWS Tax Help الرسمية](https://aws.amazon.com/tax-help/) في 2026-10-30؛ استجابت الصفحة بنجاح ولم يظهر فيها مدخل خاص بالأردن. غياب مدخل من الصفحة لا يثبت عدم استحقاق ضريبة.
- **UNVERIFIED:** الضريبة المطبقة على عنوان فوترة أردني، كيان AWS الذي سيصدر الفاتورة، وإمكان احتساب الضريبة والرسوم الدورية ضمن سقف إجمالي مضمون. توثيق حد المشروع يصف حدًا قبل الضريبة؛ لذلك لا يوجد دليل على سقف فاتورة شامل قدره 100 دولار.
- لم يُنشأ حساب AWS ولم يُرسل طلب دعم ولم تُنشأ موارد. تبقى AWS خيارًا بحثيًا فقط، وP01 **NO-GO / BLOCKED** وAI-9 **FAIL**.

## ضوابط الإنفاق المبكر في AWS — 2026-10-30

- تؤكد [وثائق AWS الرسمية لحدود الإنفاق](https://docs.aws.amazon.com/accounts/latest/reference/create-spend-limit.html) تنبيهات عند 50% و75% و90%، أو عند توقع بلوغ الحد خلال 10 أيام. وتذكر ضوابط اختيارية تمنع إطلاق موارد جديدة قبل الحد بنحو 7 أيام، وتوقف موارد خاملة محددة من EC2 وRDS وSageMaker قبل نحو 5 أيام؛ التطبيقات النشطة تبقى عاملة خلال ضابط الموارد الخاملة.
- ضوابط الإنذار المبكر اختيارية ولا تثبت الإيقاف الشامل. الوثيقة لا تحدد زمنًا أقصى أو تجاوزًا أقصى لحد الإيقاف النهائي. حد الإنفاق الأساسي يظل قبل الضريبة ولا يثبت سقف الفاتورة الإجمالي.
- لم تُفعّل أي إعدادات؛ لم يُنشأ حساب أو مورد ولم يُصرف مال. تبقى P01 **NO-GO / BLOCKED** وAI-9 **FAIL**.

## Post-merge AI-9 v3 and milestone ledger — 2026-10-31

- **VERIFIED GitHub merged PRs:** [#326](https://github.com/hamedonassar95/Devobs/pull/326) at `1357cc6b2a4520511fa098bb6c9248be7a2e9172` and [#327](https://github.com/hamedonassar95/Devobs/pull/327) at `5982bd239f7fc083163ce99e24f9bc3e20e75f5d`. Original v3 PR head was `fa87cdb547f927beb82377e112432f62644f4a10`; historical replay is preserved in [the v3 report](docs/AI9_COHERENT_ONSET_V3_REPLAY_RESULTS.md).
- **VERIFIED PR-head checks:** [run 41148812810](https://github.com/hamedonassar95/Devobs/actions/runs/41148812810) passed required `validate`, Node, Python, security, PostgreSQL RLS, Terraform, container scan and site contract. On the merged main SHA, [push CI 41149697591](https://github.com/hamedonassar95/Devobs/actions/runs/41149697591) passed `validate`, Node, Python and other required checks. The same exact main CI run also passed GitHub Pages `production-release / Publish production site` and `production-release / verify / verify-production` after `validate`; this verifies the static site on that SHA, **not** a live SaaS API or AI-9 production rollout.
- **Development comparison on reused synthetic seed 20270201 only:** Joint v2 TP/FP/FN/TN `58/8/32/45142`; coherent onset v3 `73/8/17/45142`; v3 Precision `90.1235%`, Recall `81.1111%`, FPR `0.0177%`. **Not** an independent performance estimate; the algorithm is a development-only candidate and does not modify the production detector.
- **Durable progress:** the [milestone index](docs/MILESTONE_LEDGER.json) has been updated on a separate branch to include #326/#327 and to point quality readiness to the v3 evidence, preventing duplicate implementation requests without a check of GitHub. Merging this branch remains a separate owner-controlled decision.
- **Next gate:** [the independent evaluation plan](docs/AI9_V3_INDEPENDENT_EVAL_GATE.md) preserves seeds `20270601`–`20270604` as untouched in this workflow, requires a separate explicit one-time authorization and independent no-collision review, and does not run them in CI or tests.
- **DECISION UNCHANGED:** AI-9 **FAIL / NOT AUTHORIZED FOR PRODUCTION**; P01 **NO-GO / BLOCKED**. No staging cloud provider, paid model, real data, commercial tenancy or autonomous operational change was activated by this phase.
