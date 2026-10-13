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
1. يبني `Dockerfile` الموقع الثابت الحالي باستخدام صورة `nginxinc/nginx-unprivileged` مثبتة على digest، ويشغّل NGINX كمستخدم غير root على المنفذ `8080`. ملف المهمة هو `ecs/task-definition.template.json` واسم الحاوية `devobs-web`؛ يفحص health check المسار `/health`. هذا مسار تجريبي موازٍ لـ GitHub Pages، وليس استبدالًا له.
2. قالب المهمة يستخدم Fargate مع `awsvpc` و`X86_64`. قبل التسجيل، يحقن الـ workflow `ECS_TASK_EXECUTION_ROLE_ARN` ومنطقة AWS إلى نسخة مؤقتة من القالب، ثم يستبدل action صورة الحاوية بالصورة التي بُنيت من commit SHA.
3. يوفّر `infra/ecs-foundation.yml` موارد الأساس: ECR `devobs-site` مع tags غير قابلة للتغيير وتشفير AES256 والاحتفاظ بآخر 30 صورة، وCloudWatch Logs `/ecs/devobs-site` باحتفاظ 30 يومًا، وECS cluster، ودوري IAM منفصلين للنشر وتنفيذ المهام. يحتفظ CloudFormation بمستودع الصور وسجلّات CloudWatch عند حذف الـ stack.
4. بعد إنشاء foundation stack، أنشئ الشبكة الطرفية والخدمة عبر `infra/ecs-service.yml` كما هو موضح في القسم التالي. هذا القالب ينشئ ALB عامًا وHTTPS وDNS وخدمة Fargate في subnets خاصة، ولا يحتاج إلى صورة أولية داخل ECR.
5. أضف متغيرات **Repository variables** التالية من Settings → Secrets and variables → Actions → Variables:

| المتغير | القيمة المطلوبة |
| --- | --- |
| `AWS_REGION` | المنطقة التي أُنشئ فيها الـ stack والموارد |
| `AWS_ROLE_ARN` | مخرج `GitHubDeployRoleArn` من CloudFormation |
| `ECS_TASK_EXECUTION_ROLE_ARN` | مخرج `TaskExecutionRoleArn` من CloudFormation |
| `ECR_REPOSITORY` | `devobs-site` أو مخرج `EcrRepositoryName` |
| `ECS_SERVICE` | اسم الخدمة الفعلية؛ يجب أن يطابق `EcsServiceName` في الـ stack |
| `ECS_CLUSTER` | مخرج `EcsClusterName` من CloudFormation |
| `ECS_TASK_DEFINITION` | `ecs/task-definition.template.json` |
| `CONTAINER_NAME` | `devobs-web` كما يظهر في `containerDefinitions` |
| `ECS_DEPLOY_ENABLED` | اتركه غير مضبوط أو `false` حتى إكمال كل المتطلبات والمراجعات |

لا تضع مفاتيح AWS أو بيانات اعتماد طويلة العمر في Repository variables أو الملفات. المصادقة مصممة باستخدام OIDC.

**فحص الصور:** لم يضف القالب إعدادًا للمسح لأن خاصية المسح على مستوى مستودع ECR في CloudFormation أصبحت deprecated؛ الإعداد الموصى به على مستوى registry والحساب. راجع قواعد المسح الحالية، ثم أضف قاعدة scan-on-push تطابق مستودع `devobs-site` مع الحفاظ على أي قواعد أخرى. لا تستبدل إعداد registry كاملًا دون مراجعة أثره على باقي المستودعات.
### إعداد AWS OIDC وIAM
1. أضف مزود الهوية `https://token.actions.githubusercontent.com` في حساب AWS، مع audience يساوي `sts.amazonaws.com`.
2. اجعل trust policy لدور النشر تقبل audience المذكور وsubject مطابقًا تمامًا للصيغة الثابتة لهذا المستودع: `repo:hamedonassar95@104053101/Devobs@1404102641:environment:production`. أنشئ المستودع في 4 أكتوبر 2026، بعد بدء GitHub تطبيق الصيغة الثابتة؛ قيمة `repo:owner/repo:environment:production` القديمة لن تطابقه. لا تستخدم wildcard. هذه القيمة تفترض إعداد GitHub الافتراضي لصيغة `sub`؛ إذا خُصصت claims في إعدادات OIDC، حدّث قيمة `token.actions.githubusercontent.com:sub` في trust policy إلى الـ subject الكامل الفعلي، مع إبقاء `StringEquals` ودون wildcard.
3. في GitHub، أنشئ/راجع Environment باسم `production`، واجعل فروع النشر المسموحة `main` فقط، وأضف required reviewers قبل استخدام الدور. قيد الـ subject على بيئة GitHub يجعل قواعد البيئة جزءًا من حاجز OIDC.
4. امنح دور النشر أقل صلاحيات لازمة لرفع صورة إلى مستودع ECR المحدد، وتسجيل تعريف المهمة، ووصف الخدمة وتحديثها وانتظار استقرارها. اسمح بـ `iam:PassRole` فقط إلى `ECS_TASK_EXECUTION_ROLE_ARN` المحدد، مع قصر التمرير على خدمة `ecs-tasks.amazonaws.com`. دور تنفيذ المهمة منفصل ويحتاج فقط إلى سحب image من ECR وكتابة logs إلى المجموعة المحددة. راجع نطاق الموارد لكل فعل IAM في الوثائق الرسمية قبل اعتماد السياسة.
5. فعّل ECS deployment circuit breaker مع rollback للخدمة، وتأكد أن target group health check يطابق `/health`؛ انتظار استقرار الخدمة في GitHub Actions لا ينشئ rollback تلقائيًا.
6. أضف إلى حماية `main` اشتراط موافقة PR واحدة على الأقل إلى جانب الفحوص المطلوبة. المراجعة المسجلة في هذا المستودع وقت الفحص كانت بلا موافقات PR إلزامية (`required_approving_review_count: 0`)، لذلك لا تعتبر حماية البيئة وحدها بديلًا عن مراجعة تغييرات الكود.


### إنشاء موارد الأساس باستخدام CloudFormation
القالب `infra/ecs-foundation.yml` جاهز للمراجعة فقط؛ لم يُنشر إلى AWS. يتطلب مزود GitHub OIDC موجودًا مسبقًا في الحساب. يقيّد دور GitHub إلى subject ثابت لهذا المستودع وبيئة `production`، ومستودع ECR المحدد، وخدمة ECS المحددة، ودور تنفيذ المهام الذي ينشئه القالب. تبقى أفعال تسجيل/وصف task definition على `Resource: *` لأن ECS لا يتيح تضييقها إلى ARN واحد؛ أما تمرير الدور فيقتصر على دور التنفيذ مع شرط `iam:PassedToService = ecs-tasks.amazonaws.com`.

الأمر التالي مثال للمراجعة. استبدل رقم الحساب والمنطقة، واعرض change set وراجعه قبل تنفيذه. يلزم `CAPABILITY_IAM` لأن القالب ينشئ أدوار IAM:

```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
aws cloudformation deploy \
  --template-file infra/ecs-foundation.yml \
  --stack-name devobs-ecs-foundation \
  --region "$AWS_REGION" \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    "GitHubOidcProviderArn=arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/token.actions.githubusercontent.com" \
  --no-execute-changeset
```

بعد مراجعة change set والموافقة عليه، أعد الأمر دون `--no-execute-changeset` لإنشاء الموارد. اعرض المخرجات لاستخدامها في متغيرات GitHub:

```bash
aws cloudformation describe-stacks \
  --region "$AWS_REGION" \
  --stack-name devobs-ecs-foundation \
  --query 'Stacks[0].Outputs[].{Key:OutputKey,Value:OutputValue}' \
  --output table
```

قالب الأساس ينشئ ECR وCloudWatch Logs وECS cluster ودوري IAM فقط. القالب التالي ينشئ ALB وDNS وخدمة ECS، لكنه يعتمد على VPC وشبكاتك وشهادة ACM ونطاقك الموجود مسبقًا. لا يصبح مسار النشر جاهزًا لمجرد إنشاء stack واحد؛ راجع متطلبات الشبكة والمراجعات قبل التفعيل.
### إنشاء طبقة الشبكة وخدمة ECS
القالب `infra/ecs-service.yml` يكمل stack الأساس بعد مراجعته: ينشئ Application Load Balancer عامًا في subnetين عامين من Availability Zones مختلفتين، ويعيد توجيه HTTP إلى HTTPS، ويربط اسم النطاق بسجل Route 53 من نوع A، ويضع خدمة Fargate في subnetين خاصين. يستقبل task security group المنفذ 8080 من ALB فقط. شهادة ACM يجب أن تكون صادرة في منطقة هذا الـ stack وأن تغطي `DomainName`، ويجب أن يكون `HostedZoneId` لمنطقة Route 53 عامة تخدم ذلك النطاق.

يتطلب الإعداد شبكة VPC موجودة. يلزم subnet عام في كل من منطقتين مختلفتين للـ ALB (كل subnet يفضّل ألا يقل عن `/27` وأن يتوفر فيه 8 عناوين IP حرة)، وsubnet خاص للمهام في كل منطقة. تأكد من مسارات الإنترنت للـ public subnets، ومن خروج private subnets عبر NAT Gateway أو نقاط VPC الخاصة بـ ECR API وECR DKR وS3 وCloudWatch Logs. لا تُمنح المهام Public IP؛ قواعد الخروج تسمح بـ HTTPS وDNS فقط حسب النطاق المحدد بالقالب.

ينشئ القالب مهمة NGINX تأسيسية مثبتة على digest، لكنه ينشئ الخدمة بـ `DesiredCount: 0` حتى لا تُشغّل صفحة NGINX الافتراضية. عند نشر commit إلى `main` بعد استيفاء الحماية وتفعيل المتغير، يمرر الـ workflow `desired-count: 1` إلى إجراء ECS المثبت ويشغّل نسخة واحدة من التطبيق. الخدمة تشير إلى عائلة task definition باسم `devobs-site` دون رقم revision؛ توثيق ECS يقرر أن هذا يستخدم أحدث revision نشط، الذي يسجله الـ workflow. يختبر ALB المسار `/` حتى تعمل مهمة التهيئة والتراجع، بينما يفحص container health check في تعريف التطبيق `/health`.

**تنبيه تكلفة:** تنفيذ قالب الخدمة ينشئ ALB وسجل DNS ومجموعات أمان وخدمة ECS حتى مع صفر مهام. الـ ALB يفرض رسومًا مستمرة، وقد تضيف NAT Gateway رسومًا أخرى. لم أنفذ هذا القالب ولم أنشئ أي موارد.

بعد مراجعة CloudFormation change set وقيم الشبكة والشهادة والنطاق، هذا مثال لإعداد change set فقط؛ لا ينفذ التغييرات بسبب `--no-execute-changeset`. استبدل القيم التجريبية. القالب لا ينشئ أدوار IAM جديدة:

```bash
aws cloudformation deploy \
  --template-file infra/ecs-service.yml \
  --stack-name devobs-ecs-service \
  --region "$AWS_REGION" \
  --parameter-overrides \
    VpcId=vpc-0123456789abcdef0 \
    VpcCidrBlock=10.0.0.0/16 \
    PublicSubnetA=subnet-0123456789abcdef0 \
    PublicSubnetB=subnet-0abcdef1234567890 \
    PrivateSubnetA=subnet-01111111111111111 \
    PrivateSubnetB=subnet-02222222222222222 \
    DomainName=www.example.com \
    HostedZoneId=Z012345678EXAMPLE \
    AcmCertificateArn=arn:aws:acm:us-east-1:123456789012:certificate/01234567-89ab-cdef-0123-456789abcdef \
    EcsClusterName=devobs-production \
    EcsServiceName=devobs-site \
    TaskExecutionRoleArn=arn:aws:iam::123456789012:role/DevobsTaskExecutionRole \
  --no-execute-changeset
```

افحص مخرجات الخدمة بعد تنفيذها يدويًا وبعد الموافقة على change set، واستخدم `EcsClusterName` و`EcsServiceName` كمتغيري GitHub. أبقِ `ECS_DEPLOY_ENABLED` معطّلًا إلى حين التأكد من نطاق IAM وbranch protection والمراجعين وDNS وصحة الشهادة. إعداد النشر الحالي يثبت العدد المطلوب عند مهمة واحدة؛ إذا أُضيف ECS autoscaling مستقبلًا، راجع هذا الخيار كي لا يكتب النشر فوق العدد الذي تديره سياسة التوسع.

مراجع هذا الجزء:
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-ecs-service.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-elasticloadbalancingv2-loadbalancer.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-elasticloadbalancingv2-listener.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/TemplateReference/aws-resource-elasticloadbalancingv2-targetgroup.html
- https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service_definition_parameters.html
- https://github.com/aws-actions/amazon-ecs-deploy-task-definition/blob/v2.6.4/action.yml

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
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecr-repository.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-logs-loggroup.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ecs-cluster.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-iam-role.html
- https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/using-iam-template.html
- https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonelasticcontainerservice.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-scanning.html
- https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- https://docs.github.com/en/actions/reference/security/oidc
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_providers_create_oidc.html
- https://docs.aws.amazon.com/AmazonECR/latest/userguide/image-push.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definitions.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/deployment-circuit-breaker.html
- https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_execution_IAM_role.html
- https://github.com/aws-actions/amazon-ecs-deploy-task-definition#permissions
- https://github.com/aws-actions/amazon-ecs-deploy-task-definition/blob/v2.6.4/action.yml
- https://github.com/nginx/docker-nginx-unprivileged
- https://hub.docker.com/r/nginxinc/nginx-unprivileged/tags
