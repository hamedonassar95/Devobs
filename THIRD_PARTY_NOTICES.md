# إشعارات مكونات الطرف الثالث

## AI DevKit skills

يحتوي `.agents/skills/` و`.claude/skills/` نسخًا من مهارات مشروع [AI DevKit](https://github.com/codeaholicguy/ai-devkit/tree/ff51a61c8718bb7f4ffde9e43d036d1e6623ab07)، من المستودع عند الالتزام `ff51a61c8718bb7f4ffde9e43d036d1e6623ab07`. يرخّص ملف [`LICENSE` في ذلك الالتزام](https://github.com/codeaholicguy/ai-devkit/blob/ff51a61c8718bb7f4ffde9e43d036d1e6623ab07/LICENSE) هذه النسخ بموجب Apache 2.0. كما أن ملفات القوالب `docs/ai/<phase>/README.md` مولدة من حزمة AI DevKit CLI الإصدار `0.70.1`، وتعلن بيانات الحزمة ترخيص Apache-2.0. أُرفقت نسخة الرخصة في [`licenses/AI-DevKit-Apache-2.0.txt`](licenses/AI-DevKit-Apache-2.0.txt).

راجع `.ai-devkit.json` لمعرفة قائمة المهارات المختارة. التعديلات المحلية على هذه النسخ يجب أن تُراجع وتُوثق بوضوح قبل تحديثها من المصدر.

## مذكرات التشغيل من DevOps AI Intelligence

أُعيد استخدام منطق التحقق من مذكرات التشغيل والأرشفة والاستعادة، مع تكييفه للوحة AI-7 المحلية، من الالتزام المحلي `37074be` على فرع `codex/runbook-notes-20261107` في مستودع [DevObs-ai-Intelligence-](https://github.com/hamedonassar95/DevObs-ai-Intelligence-). الرخصة المنشورة للمصدر عند `77125a809eed97a1722bd49885f56b07dfea08ac` هي MIT؛ أُرفقت نسخة في [`licenses/DEVOBS_AI_INTELLIGENCE_MIT.txt`](licenses/DEVOBS_AI_INTELLIGENCE_MIT.txt). المذكرات هنا تبقى محلية في المتصفح ولا تدخل أحداث AI-1 أو تغذية AI-6.

## OpenTelemetry Python SDK and OTLP/HTTP exporter

`requirements-api.txt` uses OpenTelemetry Python SDK/API and OTLP/HTTP exporter version `1.45.2` for the disabled-by-default local WSGI metrics path. The official [OpenTelemetry Python license](https://github.com/open-telemetry/opentelemetry-python/blob/v1.45.2/LICENSE) is Apache-2.0. Exact package artifacts are pinned by hashes in [`requirements-api.lock`](requirements-api.lock); transitive package licenses remain as published by their respective projects.
