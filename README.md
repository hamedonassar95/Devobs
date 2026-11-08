# Devobs

[![CI](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml)

مشروع عملي لتعلّم DevOps وCI/CD باستخدام GitHub Actions وGitHub Pages. تتضمن المستودع أتمتة إضافية موثقة؛ الصفحة المنشورة حاليًا صفحة HTML ثابتة ولا تحتاج خادم تطبيق أو قاعدة بيانات.

## DevOps AI Intelligence — مصدر موحّد

هذا المستودع `Devobs` هو المصدر الأساسي للمشروعين. مراحل الذكاء التشغيلي المحلية AI-1 إلى AI-7 ولوحة AI-7 مدمجة هنا بالفعل؛ نضيف فقط ما يسد فجوة واضحة بدل نسخ مكونات مكررة. المحركات الحالية محلية وحتمية/إحصائية ولا تستدعي نموذجًا لغويًا.

```text
بيانات تشغيل اصطناعية محلية
  → AI-1 استقبال وتحقق
  → AI-2 كشف شذوذ → AI-3 تحليل → AI-4 توصيات runbook
  → AI-5 اتجاهات → AI-6 تغذية راجعة اختيارية → AI-7 لوحة/API للقراءة فقط
  → GitHub Actions: اختبارات وفحوص أمنية ومراجعة PR اختيارية
```

إضافة PR-Agent اختيارية ومطفأة افتراضيًا، وتعمل كمراجع بديل عن مراجعة Codex حتى لا يتكرر الاستدلال. إعدادا Ollama وLocalAI المحليان موثقان في [`models/docker-compose.yml`](models/docker-compose.yml)، ولا يعملان تلقائيًا ولا يتضمنان أوزان نماذج. يمكن اختيار أحدهما يدويًا لتشخيص السجلات عبر API staging بعد الموافقات الصريحة، لكنهما لا يتصلان تلقائيًا بسلسلة AI-1 إلى AI-7. أمثلة K8sGPT وHolmesGPT اختيارية ومحدودة للقراءة في [`k8s/`](k8s/README.md)، ولا تثبّت الأدوات ولا تطبق إعدادات على عنقود. يظل MLflow مرشحًا لمراجعة منفصلة.

| المكوّن الخارجي المضاف أو الموثق | الإصدار/البصمة | الرخصة | النطاق |
| --- | --- | --- | --- |
| [PR-Agent](https://github.com/The-PR-Agent/pr-agent) | v0.49.0؛ صورة مثبتة على digest موثق في [دليل التكامل](docs/PR_AGENT_INTEGRATION.md) | [MIT](https://github.com/The-PR-Agent/pr-agent/blob/v0.49.0/LICENSE) | مراجعة PR اختيارية؛ غير مفعّلة ما لم تُستوفَ بوابات الاختيار والميزانية والتحقق من المصدر والاعتماد الموجود |
| [Ollama](https://github.com/ollama/ollama) | v0.40.15؛ digest موثق في [دليل النماذج](models/README.md) | [MIT](https://github.com/ollama/ollama/blob/v0.40.15/LICENSE) | خادم CPU محلي اختياري؛ لا ينزل نموذجًا تلقائيًا؛ اختيار يدوي ممكن لـAPI التشخيص فقط |
| [LocalAI](https://github.com/mudler/LocalAI) | v4.12.1؛ digest موثق في [دليل النماذج](models/README.md) | [MIT](https://github.com/mudler/LocalAI/blob/v4.12.1/LICENSE) | CPU اختياري خلف profile؛ لا ينزل نموذجًا تلقائيًا؛ اختيار يدوي ممكن لـAPI التشخيص فقط |
| [K8sGPT](https://github.com/k8sgpt-ai/k8sgpt) | v0.4.41؛ أمثلة CLI فقط | [Apache-2.0](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/LICENSE) | فحص يدوي محدود بالـnamespace؛ أمر المثال لا يطلب شرحًا من نموذج |
| [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) | 0.46.0؛ أمثلة إعداد فقط | [Apache-2.0](https://github.com/HolmesGPT/holmesgpt/blob/0.46.0/LICENSE) | إعداد toolset وصلاحيات قراءة فقط؛ لا تثبيت أو استدلال تلقائي |

مجلدات `agents/` و`workflows/` و`models/` و`mlops/` هي فهارس توثيقية لهذه المرحلة؛ ملفات التشغيل الفعلية تبقى في مواقعها الحالية. راجع [خريطة الوكلاء](agents/README.md)، [خريطة سير العمل](workflows/README.md)، [خريطة النماذج](models/README.md)، [أمثلة Kubernetes الاختيارية](k8s/README.md)، [تكامل PR-Agent](docs/PR_AGENT_INTEGRATION.md)، [خريطة المراقبة](monitoring/README.md)، و[خريطة MLOps](mlops/README.md).

## مركز الأتمتة

- **ابدأ من هنا:** [مركز الأتمتة وسير التشغيل الموحد](docs/AUTOMATION_HUB.md)
- **سجل الإنجازات والبوابات:** [Milestone Ledger](docs/MILESTONE_LEDGER.md) — فحص دون شبكة يربط كل إنجاز موثق برقم PR وSHA ودليل CI، ويعرض النواقص دون تغيير حالة جاهزيتها.
- **تكامل OpenArt الاختياري:** [حوكمة طلبات الصور والفيديو عبر MCP](docs/OPENART_MCP_INTEGRATION.md) — صيغة طلب خاصة آمنة دون شبكة أو كلفة، مع موافقة منفصلة قبل أي توليد.
- [Devobs AI DevOps Control Room](docs/AI_DEVOPS_CONTROL_ROOM.md): توثيق مسارات AI وCI وحالة التحقق من المصدر مقابل التشغيل.
- [استقبال أحداث AI-1 محليًا](docs/AI_EVENT_INGESTION.md): صيغة موحّدة وملف JSONL محلي؛ بلا اتصالات أو خدمات خارجية.
- [كشف الشذوذ AI-2 محليًا](docs/AI_ANOMALY_DETECTION.md): مؤشرات إحصائية قابلة للتفسير على أحداث مقاييس محلية اصطناعية.
- [تحليل الحوادث AI-3 محليًا](docs/AI_INCIDENT_ANALYSIS.md): تجميع سجلات اصطناعية وفرضيات أسباب محتملة وسياق CI فقط.
- [توصيات AI-4 المحلية](docs/AI_RECOMMENDATIONS.md): مطابقة فرضيات AI-3 مع runbooks ثابتة، بوضع الاقتراح فقط.
- [تقارير الاتجاه AI-5 محليًا](docs/AI_TREND_REPORTS.md): ملخص يومي/أسبوعي واستقراء أولي لمقاييس سجل محلي دون اتصال خارجي.
- [تغذية راجعة للتوصيات AI-6](docs/AI_FEEDBACK_LEARNING.md): تسجيل قبول/رفض محلي اختياري يؤثر في ترتيب المراجعة بعد حد أدنى من القرارات.
- [لوحة وAPI الذكاء التشغيلي AI-7](docs/AI_LOCAL_DASHBOARD.md): لقطة محلية للقراءة فقط؛ لا تُنشر مع الموقع ولا تعرض السجلات الخام.
- [تدقيق حوكمة main الحالي](docs/DEVOBS_MAIN_GOVERNANCE_AUDIT.md): القواعد الفعالة وفحوص PR وحالة الموافقات وفق GitHub API.
- [P00 release gate evidence](docs/P00_RELEASE_GATE_EVIDENCE.md): current branch rules, exact-main CI evidence, release safeguards and owner exit checklist.
- [P00 unsigned owner decision packet](docs/P00_OWNER_DECISION.md): immutable evidence baseline and blank GO/NO-GO fields for the human owner.
- [P00 PR #253 image-scan gap review](docs/P00_PR253_GAP_REVIEW.md): overlap with merged Trivy CI, unique scan-report gaps, and recommended rework.
- CI stages and validates `_site`; the main Pages release downloads the same run-scoped artifact across partial retries and revalidates it before publication. Rollback and Vercel remain separate paths; see [CI details](docs/CI.md).
- **Container security in CI:** the existing scan job builds `devobs-web:<checked-out SHA>` and Trivy 0.76.1 scans only that local Docker image. The fail-closed JSON policy requires the report's `container_image` type and exact `ArtifactName`; scanner/image/report errors or HIGH/CRITICAL findings (including unfixed) fail the required `validate` gate. The JSON report is retained for seven days and no image is published. Validate changes with `python3 -m unittest discover -s tests -p 'test_trivy_report_policy.py' -v` and `python3 scripts/check_action_pins.py`; see [CI details](docs/CI.md).
- [قرار P00 بشأن PR #262](docs/P00_PR262_DISPOSITION.md): سجل دليل الإحلال وحالة تعليق الإغلاق بانتظار حسم مراجعة PR.
- [تقرير جاهزية Devobs الحالي](docs/DEVOBS_READINESS_CURRENT.md): حالة موثقة بالأدلة على SHA الحالي، مع فصل النشر الثابت عن جاهزية API وSaaS غير المثبتة.
- [Offline staging acceptance](docs/STAGING_ACCEPTANCE.md): synthetic coverage and verified limits for the read-only tenant-isolation smoke check.
- [P01 managed-staging activation decision](docs/P01_ACTIVATION_READINESS.md): default NO-GO owner checklist; see the [region/budget decision](docs/P01_REGION_BUDGET_SECURITY.md) and [Render + Supabase proposal](docs/RENDER_SUPABASE_STAGING.md).
- [Devobs Production Execution Roadmap](docs/plans/2026-10-26-devobs-production-execution-roadmap.md): sequential P00–P12 gates, current evidence, blockers, and owner signoffs.

## التثبيت والتشغيل محليًا

المتطلبات: Git، وPython 3.10 أو أحدث لفحوص الموقع والاختبارات، وNode.js لاختبارات حارس الحوادث ومراحل AI-1 إلى AI-7 المحلية. لا توجد حزم تطبيق أو عملية build مطلوبة.

```sh
git clone https://github.com/hamedonassar95/Devobs.git
cd Devobs
python3 -m http.server 8000 --bind 127.0.0.1
```

افتح <http://127.0.0.1:8000> في المتصفح. لإيقاف الخادم اضغط `Ctrl+C`. على Windows استخدم `py -3 -m http.server 8000 --bind 127.0.0.1` بدلًا من `python3`.

## الاختبارات والفحوص

من جذر المستودع:

```sh
python3 -m compileall -q scripts tests
python3 -m unittest discover -s tests -v
node --test tests/incident_guard.test.cjs tests/ai_event_ingest.test.mjs tests/ai_anomaly_detector.test.mjs tests/ai_incident_analysis.test.mjs tests/ai_recommendations.test.mjs tests/ai_trend_forecast.test.mjs tests/ai_feedback_learning.test.mjs tests/ai_dashboard_api.test.mjs
python3 scripts/check_site.py
```

لتجربة استقبال محلي ببيانات اصطناعية، اتبع [دليل AI-1](docs/AI_EVENT_INGESTION.md). لا يقرأ الأمر سجلات GitHub أو الخوادم تلقائيًا.

لتشغيل كشف AI-2 على السجل الاصطناعي نفسه دون تغيير الملف، اتبع [دليل كشف الشذوذ](docs/AI_ANOMALY_DETECTION.md). المخرجات مرشحات إحصائية وليست تشخيصًا أو تنبيهًا مؤكدًا.

لتجميع السجلات وربط سياق CI محليًا، اتبع [دليل AI-3](docs/AI_INCIDENT_ANALYSIS.md). لا يثبت ذلك سببًا جذريًا ولا يدعم ربط أحداث النشر في مخطط AI-1 الحالي.

لتوليد اقتراحات محلية من runbooks ثابتة دون تنفيذ، اتبع [دليل AI-4](docs/AI_RECOMMENDATIONS.md). يلزم اعتماد بشري منفصل لأي تغيير؛ المخرجات احتمالية ولا تتصل بخدمات خارجية.

لإنتاج ملخص يومي/أسبوعي واستقراء أولي للمقاييس من ملف JSONL محلي، شغّل `node scripts/ai_intelligence/trend_report.mjs --store <local-jsonl-file>` واتبع [دليل AI-5](docs/AI_TREND_REPORTS.md). لا يكتب الأمر في الملف أو يتصل بالشبكة، ولا ينتج قيمة تنبؤ عند نقص ستة أيام UTC متصلة.

لتسجيل قبول/رفض توصية بموافقة المشغّل وترتيب الاقتراحات وفق سجل محلي اختياري، اتبع [دليل AI-6](docs/AI_FEEDBACK_LEARNING.md). لا تُجمع ملاحظات نصية، ولا يتصل النظام بالشبكة؛ المعدل إشارة تفضيل محدودة وليس قياسًا لدقة الأسباب.

لتشغيل لوحة AI-7 محليًا مع API للقراءة فقط، اتبع [دليل اللوحة المحلية](docs/AI_LOCAL_DASHBOARD.md). تدعم اللوحة أيضًا مذكرات مشغّل محلية في تخزين المتصفح مع البحث والتثبيت والأرشفة والاستعادة المؤكدة؛ لا تُرسل المذكرات إلى الخادم أو AI-6. لا تنشر اللوحة أو تعرضها عبر نفق؛ الموقع المنشور يبقى صفحة ثابتة بلا API.

يفحص CI شيفرة Python باستخدام Bandit، والاعتماديات باستخدام `pip-audit`. لتشغيل الفحوص محليًا:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m bandit -r scripts -x scripts/check_site.py
pip-audit --requirement requirements-dev.txt
```

يفحص GitHub Actions الأسرار باستخدام Gitleaks، ويتحقق من تثبيت الإجراءات الخارجية على SHA كامل. راجع [نطاق وضوابط DevSecOps](docs/DEVSECOPS.md). لا يحتاج تشغيل الموقع أو الاختبارات إلى مفاتيح أو حسابات خدمات خارجية.

## الإعداد والأسرار

المشروع لا يقرأ ملفات `.env` ولا يستخدم متغيرات بيئة محلية لتشغيل الصفحة. أُنشئ [.env.example](.env.example) كمرجع لأسماء أسرار الأتمتة الاختيارية فقط؛ لا تنسخه إلى ملف إعدادات ولا تضع فيه قيمًا حقيقية.

تُضاف أسرار الأتمتة المطلوبة من **Settings → Secrets and variables → Actions → Secrets** في GitHub، لا في ملفات المستودع أو سجلات CI:

- `COPILOT_GITHUB_TOKEN`: اختياري لتشغيل مسارات التحقيق المدعومة بـCopilot. راجع [إعداد محقق Copilot](docs/PHASE7_COPILOT_INVESTIGATOR.md) للصلاحيات المطلوبة.
- `GH_AW_CI_TRIGGER_TOKEN`: اختياري إذا احتاجت أتمتة إنشاء PR إلى تشغيل CI؛ استخدم اعتمادًا محدود الصلاحيات.
- `GH_AW_GITHUB_TOKEN` و`GH_AW_GITHUB_MCP_SERVER_TOKEN`: اختياريان لعمليات GitHub التي تتطلب صلاحيات إضافية؛ تستخدم التدفقات `GITHUB_TOKEN` المدمج كخيار احتياطي عند ملاءمته.
- `GH_AW_DEFAULT_OTLP_HEADERS`: اختياري إذا أُعدّ إرسال بيانات الرصد إلى OTLP.

يصدر GitHub Actions قيمة `GITHUB_TOKEN` تلقائيًا لكل تشغيل؛ لا تنشئها يدويًا. إعداد Vertex AI يستخدم اتحاد هوية GitHub Actions مع Google Cloud ولا يحتاج مفتاح حساب خدمة. تُحفظ معرفات مشروع Google ومزوّد الهوية وحساب الخدمة كـ **Variables** غير سرية. راجع [إعداد Vertex AI](docs/VERTEX_AI_FALLBACK.md). يمكن إضافة متغيرات إعداد gh-aw غير الحساسة من صفحة **Variables** نفسها.

لا تضع اعتمادًا حقيقيًا في `.env.example` أو المستندات أو الشيفرة. إذا سبق كشف اعتماد، أبطله ودوّره قبل متابعة استخدامه.

## المراقبة المحلية الاختيارية

يتضمن المستودع إعدادًا محليًا لـPrometheus وGrafana وAlertmanager. Node Exporter اختياري لمضيف Linux، والموقع الثابت لا يوفّر مقاييس تطبيق.

```sh
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f monitoring/compose.yml up --detach
```

الواجهات المحلية: Prometheus <http://127.0.0.1:9090>، Grafana <http://127.0.0.1:3000>، Alertmanager <http://127.0.0.1:9093>. لإضافة مقاييس Linux:

```sh
docker compose --profile linux-host -f monitoring/compose.yml up --detach
```

على Docker Desktop في Windows أو macOS يقيس Node Exporter آلة Docker الافتراضية. لا يرسل Alertmanager تنبيهات لخدمات خارجية. راجع [دليل المراقبة](docs/MONITORING.md) للتفاصيل والقيود والتراخيص.

لإيقاف جميع المكونات وتنظيف متغير كلمة المرور:

```sh
docker compose --profile linux-host -f monitoring/compose.yml down
unset GRAFANA_ADMIN_PASSWORD
```

## النشر

النشر الحالي إلى GitHub Pages:

1. في إعدادات المستودع افتح **Settings → Pages** واختر **GitHub Actions** كمصدر للنشر.
2. ادفع التغيير إلى فرع، وافتح Pull Request إلى `main`.
3. انتظر نجاح فحص `validate` وراجع المعاينة القابلة للتنزيل في ملخص CI.
4. بعد مراجعة ودمج Pull Request، ينشر سير العمل الصفحة من `main` بعد نجاح CI.
5. راجع رابط النشر ونتيجة فحص الصحة في GitHub Actions.

لا يحتاج نشر Pages الحالي إلى أسرار نشر؛ صلاحيات النشر وإثبات الهوية تُدار عبر GitHub Actions وOIDC. راجع [دليل المعاينة والنشر والرجوع](docs/DEPLOYMENT.md) و[دليل CI](docs/CI.md) للتفاصيل.

## التشغيل والتوثيق

- [CI documentation](docs/CI.md)
- [DevSecOps controls and scope](docs/DEVSECOPS.md)
- [Repository policy audit setup](docs/REPOSITORY_POLICY_AUDIT.md)
- [GitHub Pages DevOps roadmap](docs/GITHUB_PAGES_DEVOPS_ROADMAP.md)
- [AI model strategy](docs/AI_MODEL_STRATEGY.md)
- [AI provider resilience design](docs/AI_PROVIDER_RESILIENCE.md)
- [AI code review setup and limits](docs/AI_CODE_REVIEW.md)
- [Optional local coding-agent tool review](docs/FREE_CLAUDE_CODE_EVALUATION.md)
- [AI investigation acceptance and measured results](docs/INVESTIGATOR_ACCEPTANCE.md)
- [GitHub AI Scan setup and billing](docs/GITHUB_AI_SCAN.md)
- [AI and Agentic Workflow cost controls](docs/GITHUB_CODE_QUALITY_COSTS.md)
- [مرجع إصدار Neovim الليلي وأصوله](docs/NEOVIM_NIGHTLY.md)
- [iOS exploit claim triage](docs/IOS_EXPLOIT_CLAIM_TRIAGE.md)
- [Release & rollback runbook](docs/RELEASE_ROLLBACK.md)
- [النشر والرجوع](docs/DEPLOYMENT.md)
- [الاستجابة للحوادث](docs/INCIDENT_RESPONSE.md)
- [الأمان والإبلاغ عن الثغرات](SECURITY.md)
- [Stable baseline: v1.0.0](https://github.com/hamedonassar95/Devobs/releases/tag/v1.0.0)

إعداد AI DevKit للمساهمين ومراحل العمل موثق في [دليل AI DevKit](docs/AI_DEVKIT.md). هذا الإعداد منفصل عن تشغيل CI/CD؛ مركز وحدات الأتمتة القابلة لإعادة الاستخدام موجود في [مركز الأتمتة](docs/AUTOMATION_HUB.md).

- [Manual P01 evidence completeness gate](docs/P01_ACTIVATION_READINESS.md#p01-offline-evidence-gate-review-only): fails closed on missing or stale launch evidence, but cannot approve P01, launch SaaS, or access provider accounts.
