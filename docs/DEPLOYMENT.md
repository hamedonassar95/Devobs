# Devobs — المعاينة والتحكم في النشر

## نطاق المشروع
هذه الضوابط تخص مستودع `hamedonassar95/Devobs`. الصفحة الحالية مثال تعليمي يحمل محتوى الدلة موبايل؛ لا تعني أن فصل المشروعين قد اكتمل.

## الإعدادات التي تمت مراجعتها مباشرة — 6 أكتوبر 2026
- Settings → Pages → Source: GitHub Actions.
- بيئة `github-pages`: Selected branches and tags، فرع `main` فقط، دون tags.
- لا توجد أسرار أو متغيرات في بيئة الإنتاج.
- لا تتطلب البيئة موافقة نشر يدوية حاليًا؛ نقطة القرار هي دمج PR بعد الفحوص الإلزامية. سياسة الموافقات يجب مراجعتها عند انضمام متعاون.
- قاعدة Protect main تتطلب PR وvalidate ناجحًا من GitHub Actions، مع strict checks ودون bypass actors.
- الملفات تحتوي مسار نشر Pages واحدًا؛ Health Check يفحص الناتج ولا ينشر.
- مصدر GitHub Actions لا يربط Pages باسم workflow محدد؛ يجب مراجعة أي تغيير مستقبلي في ملفات workflows. لا يمثل ذلك تدقيقًا شاملًا لتطبيقات وخدمات خارجية.

## Preview
بعد نجاح فحوص PR، ينتج CI حزمة ZIP باسم يبدأ بـ `preview-pr-`.
افتح تشغيل CI من تبويب Checks، ثم قسم Artifacts أو رابط Download في Summary، ونزّل الحزمة وفك ضغطها وافتح `index.html`.
على Windows يمكن أيضًا تشغيل `py -3 -m http.server 8000 --bind 127.0.0.1` داخل مجلدها وفتح `http://127.0.0.1:8000`.
هذه معاينة HTML قابلة للتنزيل وليست استضافة مستقلة أو رابط موقع عام. فتح ملفات HTML المحلية على الآيفون يعتمد على التطبيق المستخدم؛ المعاينة المستضافة لاحقًا قرار منفصل.
- الاحتفاظ: 7 أيام، والتنزيل يتطلب تسجيل الدخول إلى GitHub.
- المحتوى: index.html وassets إن وجد، دون كامل المستودع.
- صلاحيات CI: contents: read؛ لا pages: write ولا id-token: write ولا ربط ببيئة الإنتاج.
- الفحوص الفاشلة لا تُنتج المعاينة.
- حزمة المعاينة لا تُستهلك في workflow الإنتاج ذي الصلاحيات الأعلى.
- Actions مثبتة إلى commit SHA؛ تفاصيل النسخة الجديدة: actions/upload-artifact v7.0.1، SHA 043fb46d1a93c77aae656e7c1c64a875d1fc6a0a.

## Production
1. PR ناجح يُدمج في main وفق قواعد المستودع.
2. CI يعمل على push إلى main.
3. Deploy Pages يقبل فقط نجاح CI الناتج عن push إلى main من المستودع نفسه.
4. مهمة eligible بصلاحية القراءة تتأكد أن SHA المختبر لا يزال رأس main؛ تتخطى التشغيل القديم عند اختلافهما.
5. مهمة deploy فقط تحصل على pages: write وid-token: write، وتستخدم SHA المختبر.
6. تجمع ملفات الموقع فقط وتنشرها في github-pages.
7. Deployment Health Check يتحقق من HTTP الناجح ووجود نص العلامة الحالي.

الفحص السابق للنشر يقلل خطر إعادة نشر commit قديم عند إعادة تشغيل CI؛ ليس قفلًا ذريًا يمنع تحرك main بين الفحص واكتمال النشر. concurrency يسلسل عمليات النشر. لا يُدّعى ضمان ذرية أو فحص بصري شامل للموقع.

## AWS ECS — مسار تجريبي معطّل افتراضيًا
هذا مسار تجريبي منفصل عن نشر GitHub Pages. أُضيف إلى هذا الفرع Dockerfile وقالب مهمة Fargate، لكن موارد AWS لم تُجهّز ولم يُبنَ image أو يُختبر النشر. المستودع أُنشئ في 4 أكتوبر 2026؛ لذلك يستخدم GitHub صيغة OIDC الثابتة التي تتضمن owner ID وrepository ID. يظل الـ workflow متخطّى ما لم تكن قيمة متغير المستودع `ECS_DEPLOY_ENABLED` هي النص `true` حرفيًا.

### متطلبات المستودع وGitHub
1. يبني `Dockerfile` الموقع الثابت الحالي باستخدام صورة `nginxinc/nginx-unprivileged` مثبتة على digest، ويشغّل NGINX كمستخدم غير root على المنفذ `8080`. ملف المهمة هو `ecs/task-definition.template.json` واسم الحاوية `devobs-web`؛ يفحص الـ health check المسار `/health`. هذا مسار تجريبي موازٍ لـ GitHub Pages، وليس استبدالًا له.
2. قالب المهمة يستخدم Fargate مع `awsvpc` و`X86_64`. قبل التسجيل، يحقن الـ workflow `ECS_TASK_EXECUTION_ROLE_ARN` ومنطقة AWS إلى نسخة مؤقتة من القالب، ثم يستبدل action صورة الحاوية بالصورة التي بُنيت من commit SHA.
3. جهّز مسبقًا مستودع ECR مع tag immutability وscan-on-push، وECS cluster، وFargate ECS service، ومجموعة CloudWatch Logs باسم `/ecs/devobs-site`. اربط الخدمة بـ Application Load Balancer HTTPS وشهادة ACM؛ اسم الحاوية والمنفذ في target group هما `devobs-web:8080` ومسار الصحة `/health`. يُفضّل إبقاء المهام في subnets خاصة وتوفير NAT أو VPC endpoints اللازمة لسحب image وإرسال logs. الـ workflow يبني الصورة ويرفعها ويحدّث خدمة موجودة؛ لا ينشئ هذه الموارد.
3. أضف متغيرات **Repository variables** التالية من Settings → Secrets and variables → Actions → Variables:

| المتغير | القيمة المطلوبة |
| --- | --- |
| `AWS_REGION` | منطقة AWS التي توجد فيها الموارد |
| `AWS_ROLE_ARN` | ARN لدور IAM للنشر يفترضه GitHub عبر OIDC |
| `ECS_TASK_EXECUTION_ROLE_ARN` | ARN لدور تنفيذ مهام ECS، منفصل عن دور النشر |
| `ECR_REPOSITORY` | اسم مستودع ECR، لا عنوانه الكامل |
| `ECS_SERVICE` | اسم خدمة ECS الموجودة |
| `ECS_CLUSTER` | اسم أو ARN للـ cluster |
| `ECS_TASK_DEFINITION` | `ecs/task-definition.template.json` |
| `CONTAINER_NAME` | `devobs-web` كما يظهر في `containerDefinitions` |
| `ECS_DEPLOY_ENABLED` | اتركه غير مضبوط أو `false` حتى إكمال كل المتطلبات والمراجعات |

لا تضع مفاتيح AWS أو بيانات اعتماد طويلة العمر في Repository variables أو الملفات. المصادقة مصممة باستخدام OIDC.

### إعداد AWS OIDC وIAM
1. أضف مزود الهوية `https://token.actions.githubusercontent.com` في حساب AWS، مع audience يساوي `sts.amazonaws.com`.
2. اجعل trust policy لدور النشر تقبل audience المذكور وsubject مطابقًا تمامًا للصيغة الثابتة لهذا المستودع: `repo:hamedonassar95@104053101/Devobs@1404102641:environment:production`. أنشئ المستودع في 4 أكتوبر 2026، بعد بدء GitHub تطبيق الصيغة الثابتة؛ قيمة `repo:owner/repo:environment:production` القديمة لن تطابقه. لا تستخدم wildcard، وتحقق من subject الفعلي في إعدادات OIDC للمستودع قبل إنشاء trust policy.
3. في GitHub، أنشئ/راجع Environment باسم `production`، واجعل فروع النشر المسموحة `main` فقط، وأضف required reviewers قبل استخدام الدور. قيد الـ subject على بيئة GitHub يجعل قواعد البيئة جزءًا من حاجز OIDC.
4. امنح دور النشر أقل صلاحيات لازمة لرفع صورة إلى مستودع ECR المحدد، وتسجيل تعريف المهمة، ووصف الخدمة وتحديثها وانتظار استقرارها. اسمح بـ `iam:PassRole` فقط إلى `ECS_TASK_EXECUTION_ROLE_ARN` المحدد، مع قصر التمرير على خدمة `ecs-tasks.amazonaws.com`. دور تنفيذ المهمة منفصل ويحتاج فقط إلى سحب image من ECR وكتابة logs إلى المجموعة المحددة. راجع نطاق الموارد لكل فعل IAM في الوثائق الرسمية قبل اعتماد السياسة.
5. فعّل ECS deployment circuit breaker مع rollback للخدمة، وتأكد أن target group health check يطابق `/health`؛ انتظار استقرار الخدمة في GitHub Actions لا ينشئ rollback تلقائيًا.
6. أضف إلى حماية `main` اشتراط موافقة PR واحدة على الأقل إلى جانب الفحوص المطلوبة. المراجعة المسجلة في هذا المستودع وقت الفحص كانت بلا موافقات PR إلزامية (`required_approving_review_count: 0`)، لذلك لا تعتبر حماية البيئة وحدها بديلًا عن مراجعة تغييرات الكود.

### التفعيل والتحقق
- بعد إكمال المتطلبات ومراجعة ملف المهمة وسياسة IAM، غيّر `ECS_DEPLOY_ENABLED` إلى `true`. التغيير في المتغير وحده لا يبدأ تشغيلًا؛ الـ workflow يستجيب إلى push على `main`، ولذلك سينفذ عند الدفع التالي إلى الفرع.
- أوقف المسار بإزالة المتغير أو إرجاعه إلى `false`. يظل النشر محصورًا في `main`، وتُسلسل التشغيلات ولا يُلغى تشغيل نشر سابق.
- خطوة ما قبل البناء تتحقق من المتغيرات والملفات ووجود اسم الحاوية. لا تثبت هذه الخطوة صحة الصورة أو ملاءمة إعدادات الشبكة وIAM؛ يلزم فحص إعدادات AWS الفعلية ومراجعة سجل التشغيل بعد أول نشر مخطط له.
- لا يوجد في هذه المرحلة إثبات أن خدمة ECS موجودة أو أن التطبيق يعمل داخل حاوية. لا تفعّل المتغير قبل إتمام قائمة المتطلبات أعلاه ومراجعتها.

## الموافقة والرجوع
المسار المعتمد لنشر Pages هو النشر بعد الدمج وفحص main؛ لا توجد موافقة إضافية لكل نشر.
للرجوع: أنشئ فرعًا من main الحالي، اعكس التغيير المسبب عبر revert، افتح PR واترك الفحوص تنجح ثم ادمجه. يصبح التراجع commit جديدًا يُختبر وينشر بالطريقة نفسها.
لا تستخدم force-push ولا تعطّل حماية main. إعادة تشغيل CI قديم ليست آلية rollback معتمدة.
لتعطيل حزم المعاينة أو إلغاء هذا التعديل، اعكس PR الذي أضافه عبر PR جديد.
المشروع الحالي صفحة ثابتة؛ هذه استعادة ملفات التطبيق وليست استعادة بيانات أو ترحيلات قاعدة بيانات. تجربة rollback الفعلية من المرحلة 5 ولم تنفذ هنا.

## أدلة الاختبار السابق
PR #10: https://github.com/hamedonassar95/Devobs/pull/10
- خطأ doctype أدى إلى فشل CI ومنع الدمج.
- استعادة الملف أدت إلى نجاح CI وCodeQL.
- لم يحدث دمج أو نشر لفرع الاختبار.

## مراجع رسمية راجعت بتاريخ 6 أكتوبر 2026
- https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
- https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run
- https://github.com/actions/upload-artifact/releases/tag/v7.0.1

## مراجع AWS/GitHub لمسار ECS
- https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- https://docs.github.com/en/actions/reference/security/oidc
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- https://github.com/aws-actions/amazon-ecs-deploy-task-definition#permissions
- https://github.com/nginx/docker-nginx-unprivileged
- https://hub.docker.com/r/nginxinc/nginx-unprivileged/tags
