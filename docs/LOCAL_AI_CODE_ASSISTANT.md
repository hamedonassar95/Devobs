# مساعد برمجة محلي مجاني

يوفر Devobs مسارًا اختياريًا لمساعدة المطور في تعديل الشيفرة باستخدام **Aider**
مع **Ollama** ونموذج يختاره المطور ويثبته على جهازه. لا يحتاج هذا المسار إلى
مفتاح API أو اشتراك استدلال سحابي. تُرسل الطلبات إلى Ollama المحلي على
`127.0.0.1` فقط؛ إعداد Compose يعطّل نماذج Ollama السحابية. يبقى تنزيل Ollama
والنموذج واستهلاك CPU/GPU والذاكرة والتخزين على جهاز المطور.

## النطاق والضوابط

- Aider أداة برمجة تفاعلية، وليست وكيلًا يعمل في الخلفية. تستطيع تعديل الملفات
  التي تطلب العمل عليها؛ راجع الفروق بنفسك قبل اعتمادها.
- الإعداد يعطّل الالتزامات التلقائية والتزامات الملفات المتسخة والتحليلات وفحص
  التحديث عند كل تشغيل. لا يشغّل CI أو الاختبارات أو النشر ولا يفتح PR.
- `--subtree-only` يحصر خريطة المستودع بالمجلد الذي شُغّلت منه الأداة. ابدأ من
  مجلد الميزة المقصودة، وأضف الملفات الضرورية فقط عبر أمر `/add` داخل Aider.
- `.aiderignore` يستبعد ملفات البيئة والمفاتيح والسجلات وبيانات النماذج من سياق
  الأداة. لا تضف أسرارًا أو بيانات عملاء يدويًا إلى المحادثة أو ملفاتها.
- يتطلب المشغّل شجرة Git نظيفة، ويرفض أسماء النماذج السحابية، ويتحقق من أن
  الخدمة المحلية تعمل مع تعطيل السحابة وأن النموذج موجود محليًا.
- لا يثبّت المستودع Aider أو Ollama تلقائيًا، ولا يضمّن أوزان نماذج. رخصة
  النموذج مستقلة عن رخصة البرنامج؛ راجعها وملاءمة حجمها لجهازك قبل التنزيل.

## الإعداد خطوة بخطوة

1. ثبّت Docker وDocker Compose وGit وPython 3.12. لا تشغّل المساعد فوق تعديلات
   غير محفوظة؛ أنشئ فرعًا أو worktree نظيفًا أولًا.
2. شغّل خادم Ollama المحلي من جذر المستودع:

   ```sh
   docker compose -f models/docker-compose.yml up -d ollama
   ```

   خدمة Devobs تربط المنفذ على `127.0.0.1` وتضبط `OLLAMA_NO_CLOUD=1`. إذا كان
   لديك حاوية قديمة أنشئت قبل هذا الإعداد، أعد إنشاء خدمة Ollama لتطبيقه:

   ```sh
   docker compose -f models/docker-compose.yml up -d --force-recreate ollama
   ```

3. اختر نموذجًا محليًا بعد مراجعة رخصة أوزانه ومتطلبات جهازك. اعرض النماذج
   المثبتة أو نزّل النموذج الذي اخترته يدويًا داخل الحاوية:

   ```sh
   docker compose -f models/docker-compose.yml exec ollama ollama list
   docker compose -f models/docker-compose.yml exec ollama ollama pull <model>
   ```

4. ثبّت نسخة Aider المثبتة في هذا الدليل داخل بيئة Python منفصلة. تتطلب الحزمة
   Python 3.10–3.12؛ نستخدم 3.12 هنا:

   ```sh
   mkdir -p "$HOME/.venvs"
   python3.12 -m venv "$HOME/.venvs/devobs-aider"
   "$HOME/.venvs/devobs-aider/bin/python" -m pip install "aider-chat==0.86.2"
   ```

   على Windows، استخدم WSL أو Git Bash مع Python 3.12. لا تثبّت الحزمة داخل
   بيئة اعتماديات التطبيق.

5. بعد تفعيل البيئة، حدّد مجلدًا داخل Devobs تريد العمل فيه، ثم شغّل المشغّل
   مع اسم النموذج كما يظهر في `ollama list`:

   ```sh
   source "$HOME/.venvs/devobs-aider/bin/activate"
   cd /path/to/Devobs/scripts
   DEVOBS_LOCAL_CODE_MODEL='<model>' ../scripts/devobs_local_aider.sh
   ```

   داخل جلسة Aider أضف ملفات المهمة عبر `/add path/to/file`، واطلب اقتراحًا أو
   تعديلًا محددًا. راجع `/diff` ثم اخرج وافحص `git diff` يدويًا.

6. بعد الانتهاء، أوقف Ollama إذا لم تعد تحتاجه:

   ```sh
   docker compose -f models/docker-compose.yml stop ollama
   ```

## التراخيص والمراجع

- Aider v0.86.2 (تحقق 12 نوفمبر 2026): رخصة Apache-2.0 في [ملف LICENSE upstream](https://github.com/Aider-AI/aider/blob/v0.86.2/LICENSE.txt)، والحزمة في [PyPI](https://pypi.org/project/aider-chat/0.86.2/).
- توثيق [استخدام Ollama مع Aider](https://aider.chat/docs/llms/ollama.html)، و[إعداداته](https://aider.chat/docs/config/options.html)، و[تكامل Git](https://aider.chat/docs/git.html).
- توثيق Ollama الرسمي عن [وضع التشغيل المحلي وتعطيل السحابة](https://docs.ollama.com/faq).

هذا إعداد تطوير محلي، وليس اعتمادًا على جودة نموذج معين أو إعلانًا عن جاهزية
Devobs للإنتاج أو SaaS. لم تُضف أي خدمة أو اعتماديات إلى CI، ولم يُنزّل نموذج
أو يُجرَ استدلال حي ضمن إعداد هذا الدليل.
