# مختبر Ansible المحلي لـ CBTA

هذا المختبر يوضح كيف يصف Playbook الحالة المطلوبة بصيغة YAML، ثم يجعل Ansible النظام يقترب منها باستخدام modules. لا يحتاج إلى Agent دائم على localhost، لكنه يفترض وجود ansible-core على جهاز التحكم. عند إدارة أجهزة بعيدة، يلزم اتصال مناسب مثل SSH لأنظمة Linux أو WinRM لأنظمة Windows، وقد تتطلب modules Python أو متطلبات أخرى على الهدف.

## حدود الأمان

- يستهدف المثال localhost فقط.
- يكتب ملفًا تجريبيًا داخل /tmp/devobs-cbta-demo ولا يستخدم sudo.
- لا يقرأ أسرارًا ولا يتصل بـ AWS أو خدمة خارجية.
- لا تغير hosts أو المسار إلى جهاز إنتاج.
- check mode لا يحاكي كل module بالكامل؛ راجع توثيق module المستخدمة.

## المتطلبات

استخدم ansible-core في بيئة تطوير معزولة أو virtual environment وفق سياسة إصدار الأدوات المعتمدة للفريق. لم يُضف هذا المختبر إلى CI ولا يثبت حزمًا تلقائيًا.

تحقق من الأداة:

    ansible-playbook --version

## خطوات المختبر

من جذر المستودع، شغّل معاينة أولًا:

    ansible-playbook -i 'localhost,' -c local ansible/playbooks/cbta_local_demo.yml --check --diff

راجع فرق الملف المتوقع. بعد ذلك طبّق الحالة على المسار المؤقت:

    ansible-playbook -i 'localhost,' -c local ansible/playbooks/cbta_local_demo.yml --diff

أعد الأمر نفسه مرة ثانية. في التشغيل المستقر يُتوقع أن تكون قيمة changed صفرًا. إذا ظهرت تغييرات متكررة، افحص المحتوى والصلاحيات واختيار module قبل اعتبار التمرين ناجحًا.

## ما الذي يثبته التمرين

- Playbook يعلن الحالة المرغوبة بدل الاعتماد على سلسلة أوامر shell.
- file وcopy modules تطبقان الدليل بصورة قابلة للتكرار.
- check mode وdiff يساعدان على مراجعة الأثر قبل التطبيق.
- نتيجة التشغيل الثاني دليل عملي على الاستقرار لهذا المثال، وليست إثباتًا أن كل Playbooks أو modules idempotent.

## التنظيف

بعد التأكد من المسار، احذف المجلد التجريبي المحدد فقط عند الحاجة:

    rm -r /tmp/devobs-cbta-demo
