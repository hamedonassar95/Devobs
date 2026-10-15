# تكاليف GitHub Code Quality وضوابطها

**تاريخ المراجعة:** 15 أكتوبر 2026  
**المصدر الأساسي:** [عرض تكاليف GitHub Code Quality وإدارتها](https://docs.github.com/en/enterprise-cloud@latest/code-security/how-tos/maintain-quality-code/view-and-manage-cost)

## ما الذي يغطيه هذا الدليل؟

GitHub Code Quality منتج مدفوع من GitHub Team وGitHub Enterprise Cloud. وهو منفصل عن سير عمل CodeQL الموجود في المستودع؛ ظهور فحص CodeQL في GitHub لا يثبت وحده أن منتج Code Quality مفعّل.

لا يظهر في ملفات Devobs المحلية إعداد يثبت تفعيل Code Quality أو ميزانيته. يجب تأكيد حالة التفعيل والإنفاق من **Settings → Code quality** ومن **Billing & Licensing**؛ فهذه إعدادات حساب GitHub ولا يمكن التحقق منها من ملفات المستودع.

## مصادر التكلفة

| المصدر | طريقة الاحتساب والأثر |
| --- | --- |
| ترخيص المساهم | ترخيص مستقل لكل مساهم نشط وفريد في مستودع مفعّل. يُعدّ المساهم نشطًا إذا دُفع أحد commitاته إلى المستودع خلال آخر 90 يومًا. لا تُحتسب حسابات GitHub App bots. تعطيل Code Quality قد يحرر تراخيص المساهمين الفريدين للدورة التالية، ولا يخفض فاتورة الفترة الحالية. |
| دقائق GitHub Actions | كل فحص Code Quality يستهلك دقائق Actions عند استخدام runners مستضافة من GitHub. يحدد تقرير الاستخدام التفصيلي هذه الفحوص عبر `workflow_path` بالقيمة `dynamic/github-code-quality/codeql`. |
| أرصدة GitHub AI | ميزات الذكاء الاصطناعي تستخدم رصيد AI مشتركًا مع منتجات GitHub AI الأخرى، ومنها Copilot؛ لا يوجد رصيد منفصل خاص بـ Code Quality. ويعتمد الاستهلاك على عدد الرموز المستخدمة. قيمة الرصيد المنشورة حاليًا هي 0.01 دولار أمريكي لكل نقطة AI. |

تأتي رسوم الترخيص ودقائق Actions وأرصدة AI من مقاييس فوترة مختلفة؛ راجع كلًا منها على حدة قبل توسيع التفعيل.

## قياس الاستخدام

1. نزّل تقرير الاستخدام من **Billing & Licensing** لمعرفة إنفاق Code Quality ودقائق Actions على مستوى المستودع أو المؤسسة. هذا هو التقرير الذي يتيح إسناد هذه التكاليف إلى مستودع محدد.
2. افتح صفحة **AI usage** واجمع البيانات حسب **Product** لمتابعة حصة Code Quality من رصيد الذكاء الاصطناعي المشترك. راقب إجمالي الرصيد أيضًا، لأن Copilot ومنتجات أخرى قد تستخدمه.
3. بعد أي تجربة، قارن عدد المساهمين النشطين، وعدد الفحوصات، واستهلاك AI الفعلي قبل اتخاذ قرار التوسّع. لا يمكن تقدير الإنفاق بدقة مسبقًا.

## ضوابط التكلفة المتاحة

- فعّل الميزة على مستودعات محددة فقط، وابدأ بتجربة صغيرة بدل تفعيلها على كل المستودعات.
- أنشئ ميزانية قبل بدء التجربة. ميزانية Code Quality حدّ فعلي للإيقاف؛ خيار إيقاف الاستخدام عند بلوغ الحد مفعّل ولا يمكن تعطيله. استخدم ميزانية خاصة بـ Code Quality إذا أردت تحديد تكلفته وحده، وميزانية أرصدة AI إذا أردت وضع حد إجمالي لاستهلاك منتجات الذكاء الاصطناعي.
- اترك صفحة **AI findings** مغلقة ما لم تكن هناك حاجة لها. هي في معاينة عامة ومغلقة افتراضيًا، لكن المستودعات التي فعّلتها أثناء المعاينة قد تبقى مفعّلة.
- إذا أُوقف Code Quality على مستودع، تتوقف فحوصه المستقبلية واستهلاك دقائق Actions وأرصدة AI الناتج عنها. قد تستمر رسوم الترخيص حتى دورة الفوترة التالية.

## ما لا يمكن ضبطه منفردًا

- لا توجد طريقة موثوقة لحساب الفاتورة بدقة قبل التفعيل؛ الاستهلاك يتغير بحسب المساهمين وتكرار الفحوص والنتائج.
- لا يمكن تعطيل ميزات الذكاء الاصطناعي التي تعمل داخل طلبات السحب مع إبقاء Code Quality مفعّلًا. لإيقاف هذا الاستهلاك يجب تعطيل Code Quality للمستودع.
- لا يدعم المنتج اختيار نموذج ذكاء اصطناعي بديل لتخفيض التكلفة.

## سياسة مقترحة لمستودع Devobs

1. لا تفعّل Code Quality على مستوى المؤسسة أو كل المستودعات دون تجربة وميزانية معتمدة.
2. إن تقررت التجربة، فعّل Devobs وحده أولًا، وضع حدًا صلبًا لميزانية Code Quality وراقب رصيد AI المشترك.
3. أبقِ AI findings مغلقًا حتى تظهر حاجة واضحة إليه.
4. راجع تقرير الاستخدام بعد أول دورة فوترة، ثم قرر الإبقاء أو التوسيع أو التعطيل.
5. استمر في استخدام CI وCodeQL الحاليين كضوابط المستودع. يضبط CI الموجود التزامن لإلغاء التشغيل الأقدم على الفرع نفسه، ويحتفظ بمعاينات طلبات السحب سبعة أيام؛ هذه الضوابط تقلل بعض دقائق Actions والملفات المؤقتة، لكنها لا تضبط ترخيص Code Quality أو رصيد AI.

فوترة Vertex AI في Google Cloud منفصلة عن أرصدة GitHub AI. راجعها في مشروع Google Cloud نفسه.

## المصادر الرسمية

- [عرض تكاليف GitHub Code Quality وإدارتها](https://docs.github.com/en/enterprise-cloud@latest/code-security/how-tos/maintain-quality-code/view-and-manage-cost)
- [فوترة GitHub Code Quality](https://docs.github.com/en/enterprise-cloud@latest/billing/concepts/product-billing/github-code-quality)
- [تفعيل GitHub Code Quality](https://docs.github.com/en/enterprise-cloud@latest/code-security/how-tos/maintain-quality-code/enable-code-quality)
- [تعطيل GitHub Code Quality](https://docs.github.com/en/enterprise-cloud@latest/code-security/how-tos/maintain-quality-code/disable-code-quality)
- [إعداد ميزانيات المنتجات ذات الفوترة حسب الاستخدام](https://docs.github.com/en/enterprise-cloud@latest/billing/how-tos/set-up-budgets)
- [عرض استخدام المنتجات والتراخيص وتنزيل تقارير الاستخدام](https://docs.github.com/en/enterprise-cloud@latest/billing/how-tos/products/view-productlicense-use)
