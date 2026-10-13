# مختبر Ansible المحلي لـ CBTA

هذا المختبر يوضح كيف يصف Playbook الحالة المطلوبة بصيغة YAML، ثم يجعل Ansible النظام يقترب منها باستخدام modules. Ansible agentless في الاستخدام المعتاد: لا يتطلب تثبيت Ansible أو وكيل دائم على الأجهزة المُدارة، لكنه يحتاج ansible-core على جهاز التحكم. تتصل Ansible بأجهزة Linux عادةً عبر SSH، وتحتاج معظم modules إلى Python على الهدف. تستخدم أجهزة Windows غالبًا WinRM أو PSRP؛ تختلف المتطلبات حسب نظام التشغيل والـ module.

## حدود الأمان

- يستهدف المثال localhost فقط.
- يكتب ملفًا تجريبيًا داخل /tmp/devobs-cbta-demo ولا يستخدم sudo.
- لا يقرأ أسرارًا ولا يتصل بـ AWS أو خدمة خارجية.
- قد يعرض diff محتوى حساسًا؛ استخدمه لهذا المثال غير الحساس فقط، ولا تشارك مخرجات diff من إعدادات حقيقية قبل مراجعتها.
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

## مراجع Ansible الرسمية

- [Playbooks والحالة المطلوبة وidempotency](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_intro.html)
- [تثبيت Ansible ومتطلبات control node والأجهزة المُدارة](https://docs.ansible.com/projects/ansible/latest/installation_guide/intro_installation.html)
- [حدود check mode وdiff mode](https://docs.ansible.com/projects/ansible/latest/playbook_guide/playbooks_checkmode.html)
