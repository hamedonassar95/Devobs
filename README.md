# Devobs

## Firebase security and learning — Phase 1

[Firebase offline safety baseline and phased integration plan](docs/security/FIREBASE_PHASE1_BASELINE.md)
documents the difference between the canonical deny-all prototype and older
permissive Firestore rules, the offline test commands, and a beginner-friendly
integration roadmap. This does not enable cloud resources, AI usage or deployments.

[Firebase Phase 2 access-control inventory](docs/security/FIREBASE_PHASE2_ACCESS_INVENTORY.md)
maps the client operations, authentication boundaries, tenant and ownership gaps,
and the next offline emulator authorization-test task. It does not enable Firebase.

[Firebase Phase 5 hosted-rules audit](docs/security/FIREBASE_PHASE5_HOSTED_RULES_AUDIT.md)
records the read-only access blocker and separates verified repository evidence
from unknown hosted rules; no Firebase documents or hosted rules were read or changed.

Run from repository root: python3 scripts/check_firebase_rules_baseline.py
and python3 -m unittest discover -s tests -p 'test_firebase_rules_baseline.py' -v.

## Human-supervised multi-agent repository workflow

[AI Multi-Agent Repository Workflow](docs/AI_MULTI_AGENT_WORKFLOW.md) documents isolated Codex/OpenCode worktrees, non-overlapping file ownership, Draft PR review, verification evidence, and owner-only merge/deploy decisions. This is a documented operating policy, not an activated agent scheduler or automatic dispatch service.


## Optional Pulumi Delivery and Azure Catalyst readiness

[Pulumi Delivery assessment](docs/integrations/PULUMI_DELIVERY_READINESS.md),
[Azure Catalyst assessment](docs/integrations/AZURE_CATALYST_READINESS.md),
[vendor-neutral architecture](docs/architecture/MULTICLOUD_INTEGRATION_ARCHITECTURE.md)
and [execution plan](docs/roadmap/INTEGRATION_EXECUTION_PLAN.md) preserve the
existing GitHub Actions/GCP architecture. The offline, dependency-free checker
accepts only read-only `DRY_RUN` policy fixtures; PASS is design validation,
not authentication, human approval or permission to deploy. No provider is activated.

## P01 readiness: verified NO-GO evidence (2026-11-19)

**2026-11-23 read-only provider update:** [Current Render and Supabase checkpoint](docs/p01/P01_PROVIDER_CHECKPOINT_2026-11-23.md) confirms an unsuccessful hosted staging deploy, an INACTIVE Devobs Supabase project, and the Render Free PostgreSQL expiry on 2026-12-05. No production GO or retention action is authorized.

[Read the fixed-SHA P01 NO-GO owner decision and acceptance matrix](docs/p01/P01_NO_GO_DECISION_2026-11-19.md) for the reviewed `main` SHA `0f062c03dbefceebf8eaca79bdaf30c2483f99be`. This is source/read-only metadata evidence, **not** a provider hard-cap, hosted test or P01 approval. The existing P01 evidence sample and P01/AI-9/Codex gates are unchanged. A separate owner decision is needed before the existing Free PostgreSQL expiry on 2026-12-05.


[![CI](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/hamedonassar95/Devobs/actions/workflows/ci.yml)

## Read-only PR readiness gate

[The PR Readiness Gate](docs/agents/PR_READINESS_GATE.md) is a read-only CLI that combines GitHub
PR metadata, Actions checks, branch protection, review state, unresolved review requests, and
mergeability into `VERIFIED_READY`, `BLOCKED`, or `UNVERIFIED`. Missing evidence never counts as
success, local test output is never treated as GitHub CI, and `VERIFIED_READY` is not human
approval and does not authorize a merge.

```sh
python scripts/pr_readiness_gate.py --pr 123 --repo OWNER/REPO
python -m unittest discover -s tests -p "test_pr_readiness_gate.py" -v
```

**Read-only Render Free checkpoint refreshed (2026-11-19):** [Free PostgreSQL inventory, fixed 2026-12-05 expiry, and offline fail-closed preflight](docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md). This is not a hosted API test, backup, paid activation or P01 GO; separate owner retention/retirement authorization remains required.

**Retirement planning approved (no deletion, 2026-11-19):** [Owner-gated Render Free PostgreSQL retirement plan](docs/plans/2026-11-19-render-free-postgres-retirement-plan.md). The plan documents dependencies, rollback limits and separate execution approval; it makes no hosted changes and P01 remains NO-GO.

**Expiry decision pending (2026-11-24):** [Render Free database decision matrix](docs/p01/RENDER_FREE_DB_EXPIRY_DECISION_2026-11-24.md). No preservation or retirement path is authorized; the 2026-12-05 deadline is not an instruction to delete or upgrade.

## Offline Graphify repository intelligence (local, opt-in)

A pinned, offline Graphify CLI can build one local graph index per authorized
repository from a single installation, with no source upload, hosted service or
repository permission change. The allowlist, privacy controls, measured
per-repository results and current blockers are in
[the Graphify integration design](docs/architecture/graphify-integration.md);
the reusable module layout and native-versus-Devobs feature split are in
[repository intelligence](docs/architecture/repository-intelligence.md).
This is local evidence only and does not change P01, AI-9 or Codex runtime gates.

## Two-agent offline task coordination (manual; no agents started)

[The offline task contract](docs/agents/TWO_AGENT_COORDINATION.md) defines `CODEX`
and `OPENCODE` as separate worker roles driven by a local JSON manifest. The
checker validates unique task IDs, status transitions, concurrent file/branch
ownership, unresolved dependencies and completion evidence. It starts no agent,
makes no network call and does not grant merge, deploy, billing or production
approval. Arabic guidance is included in the same document.

```sh
python scripts/check_two_agent_tasks.py --help
python scripts/check_two_agent_tasks.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_two_agent_tasks.py" -v
```

`PASS` (0), `BLOCKED` (1) and `FAIL` (2) are advisory; P01 stays NO-GO, AI-9 stays
BLOCKED and Codex runtime acceptance stays OPEN.

A local [agent dispatch preflight guide](docs/agents/AGENT_DISPATCH_OPERATING_GUIDE.md)
now builds on that validator. It reuses the same contract, detects whether the
`codex` and `opencode` CLIs are present without invoking them, writes separate
per-worker instruction files, and lists the exact human-approval actions. Its
default and only mode is `DRY_RUN`; it starts no agent and grants no approval.

```sh
python scripts/agent_dispatch_preflight.py --manifest /path/to/tasks.json
python -m unittest discover -s tests -p "test_agent_dispatch_preflight.py" -v
```

A local [agent task-status report](docs/agents/AGENT_TASK_STATUS_REPORT.md) now
reuses the same manifest contract to print required task fields, blocked tasks,
PR references and evidence states. It is advisory local data only: it never
executes stored commands, fetches GitHub data, starts agents or treats a
manifest `PASS` as verification or approval. Arabic usage is included.

```sh
python tools/agent_task_status_report.py --manifest /path/to/tasks.json
python tools/agent_task_status_report.py --manifest /path/to/tasks.json --json-only
python -m unittest discover -s tests -p "test_agent_task_status_report.py" -v
```

A local [AI quality and agent coordination gate](docs/ai-quality-gate.md) now
composes those deterministic controls into one `DRY_RUN`, read-only JSON
decision with audit events and advisory remediation notes. It detects
conflicting task ownership, dependency cycles, blocked tasks, duplicate
verification claims and evidence-classified CI failures. It grants no merge,
deploy, billing or production authority and makes no network call.

```sh
python -m devobs.ai_quality_gate --input examples/ai_quality_gate/snapshot.json
python -m unittest discover -s tests/ai_quality_gate -p "test_*.py" -v
```

## AI Provider Evaluation (offline harness)

[AI Provider Evaluation](docs/ai/AI_PROVIDER_EVALUATION.md) is a deterministic,
offline-first harness for comparing advisory AI providers on quality proxies,
reliability, safety and estimated cost. It uses seeded in-memory mocks for
success, timeout, retry-after-rate-limit, malformed response, authentication
failure, cost ceiling, unsafe requested action, provider outage and redirect
refusal. No network call, credential, paid inference or live provider request
is possible; unverified prices are reported as `UNKNOWN`, never zero.

```sh
python -m devobs.ai_evaluation.cli \
  --fixtures examples/ai_evaluation/provider_cases.json \
  --pricing examples/ai_evaluation/pricing.json
python -m devobs.ai_evaluation.cli \
  --fixtures examples/ai_evaluation/provider_cases.json \
  --pricing examples/ai_evaluation/pricing.json --gate
python -m unittest discover -s tests/ai_evaluation -p "test_*.py" -v
```

`--gate` is a deterministic, offline quality gate over the pinned fixtures: it
checks outcome/status expectations, offline authority, cost truthfulness, safety
and reliability, requires a pinned fingerprint and a composite score of at least
`0.90`, and exits `0` (`PASS`), `1` (`BLOCKED`) or `2` (`INVALID`). It runs as one
step of the existing CI `security` job. Any fixture/pricing change must update
the fingerprint pin in the same reviewed commit.

This harness and its gate are advisory only. They do not change P01 (NO-GO),
AI-9 (BLOCKED) or Codex runtime acceptance (OPEN), and they do not authorize a
provider switch, merge, deployment or spend.

## Root-cause audit and remediation roadmap (2026-11-20)

An evidence-driven audit of `origin/main` `4299a9d` confirmed one P1 root cause:
Python code under `tools/` was excluded from CI change selection, compilation
and Bandit scanning. The fix and its regression evidence are in
[the root-cause audit](docs/audits/DEVOBS_ROOT_CAUSE_AUDIT.md),
[the remediation roadmap](docs/roadmap/REMEDIATION_ROADMAP.md), and
[the rollback runbook](docs/runbooks/REMEDIATION_ROLLBACK.md). P01 remains
NO-GO/BLOCKED, AI-9 remains BLOCKED, and Codex runtime acceptance remains OPEN.

A subsequent recovery assessment of `origin/main` `cecae6c` verified that fix on
`main`, selected the remaining P1 Graphify canonicalization ambiguity for a
bounded repair, and documented all other blockers. See
[the recovery audit](docs/audits/DEVOBS_RECOVERY_AUDIT.md),
[the recovery roadmap](docs/roadmap/DEVOBS_RECOVERY_ROADMAP.md),
[the recovery rollback runbook](docs/runbooks/RECOVERY_AND_ROLLBACK.md), and
[the Graphify consolidation plan](docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md).
No release gate was promoted by this work.

## CI Failure Intelligence (read-only)

[CI Failure Intelligence](docs/agents/CI_FAILURE_INTELLIGENCE.md) provides deterministic, evidence-based diagnostics for failed GitHub Actions runs. It classifies failures (code/infrastructure/ambiguous), detects repeated signatures, correlates commit evidence, redacts secrets, labels findings `VERIFIED/INFERRED/UNVERIFIED`, and supports optional injectable AI summaries with rule-based fallback. Read-only: no code changes, reruns, merges, or deploys.

## AI Incident Intelligence (offline library)

[AI Incident Intelligence](docs/agents/AI_INCIDENT_INTELLIGENCE.md) builds on CI Failure Intelligence with evidence-linked hypotheses, explicit `HIGH`/`MEDIUM`/`LOW` confidence, advisory remediation steps, and human-readable summaries. It classifies dependency, configuration, timeout, test, CI failure, infrastructure, and unknown failures from sanitized logs, and maps bounded existing adviser signals to CI/infrastructure categories with schema-validated JSON reports. The raw project reference and source SHA stay inside the strict envelope boundary. AI providers are disabled by default; no automatic fixes, external API calls, merges, or deployments are performed.

## Incident Intelligence Engine (offline orchestration)

[Incident Intelligence Engine](docs/architecture/INCIDENT_INTELLIGENCE_ENGINE.md) adds a thin `devobs/incidents/` layer over the merged analyzer and CI redaction primitives. It ingests sanitized CI/operational evidence, maps findings to eight bounded categories, detects repeated signatures and recurrence, reports insufficient evidence, and emits schema-validated JSON/Markdown with explicit approval states. Local structured events are available through an adapter; there is no network call, provider by default, or remediation executor. See the [offline triage runbook](docs/runbooks/INCIDENT_TRIAGE.md).

## Offline Integration Control Plane (advisory only)

[Integration Control Plane](docs/architecture/INTEGRATION_CONTROL_PLANE.md) combines the existing PR readiness gate and two-agent task validator into one deterministic, offline decision with duplicate-evidence rejection, secret redaction, branch-change detection, and separate passed/failed/skipped checks. It runs no network call or agent and never authorizes a merge; `PROCEED_TO_HUMAN_REVIEW` still requires normal human approval. See the [offline runbook](docs/runbooks/INTEGRATION_CONTROL.md) and `python -m devobs.integration_control --help`.

[Integration Control Hardening](docs/architecture/INTEGRATION_CONTROL_HARDENING.md) adds opt-in approval-evidence diagnostics, explicit prohibited-action and unsafe-retry findings, and an optional local event adapter without changing the report schema or granting authority. See the [hardening runbook](docs/runbooks/INTEGRATION_CONTROL_HARDENING.md).

```sh
python -m unittest discover -s tests/integration_control -p "test_*.py" -v
```

## مراجعة خطط Codex والكود بصريًا — Plannotator (اختياري)

أضفنا [دليل تكامل Plannotator مع Codex](docs/integrations/PLANNOTATOR_CODEX_REVIEW.md) لإجراء مراجعات بصرية يدوية للخطط والـ diff على جهاز موثوق، دون تفعيل Hooks أو تشغيل خدمات أو إضافة تبعيات داخل المستودع. **الحالة: موثّق فقط / التشغيل غير متحقق.** يحتاج استخدام الأداة إلى تثبيت اختياري يراجعه المالك على جهازه؛ دعم ChatGPT على iPhone أو Codex السحابي غير مثبت. تستمر موافقات الإنسان وحماية `main` وفحوص CI وبوابات P01/AI-9 دون تغيير.


### فحص Plannotator على Windows — قراءة فقط

بعد تنزيل المستودع على جهاز Windows موثوق، يمكن تشغيل فحص المتطلبات دون استهلاك رصيد Codex أو تثبيت أداة أو تفعيل Hooks:

```powershell
$env:PLANNOTATOR_SHARE = "disabled"
$env:PLANNOTATOR_REMOTE = "0"
py -3 scripts/check_plannotator_windows_preflight.py --json
```

راجع [دليل Windows الآمن](docs/integrations/PLANNOTATOR_CODEX_REVIEW.md#windows-powershell-read-only-prerequisite-check-no-codex-credits). النتيجة `PREREQUISITES_PRESENT_RUNTIME_UNVERIFIED` لا تثبت أن Plannotator يعمل، أما `BLOCKED` فتتطلب مراجعة السبب قبل أي تثبيت يدوي. الأداة لا تتصل بخدمة خارجية ولا تعدل إعدادات المستودع أو Codex.

## تنبيه أمني مغلق — سحب تقرير picomatch (`GHSA-fc5q-39xc-vjpf`)

سُحب التقرير الأمني `GHSA-fc5q-39xc-vjpf` / `CVE-2026-112366` الخاص بحزمة `picomatch` من قاعدة بيانات GitHub Advisory في **2026-11-18T15:38:56Z**، بعد أن كان يغطي الإصدارات `<= 4.0.7` دون إصدار مُصلح. يعتمد هذا المستودع على `picomatch@4.0.7` عبر `vite@8.3.8` و`vite → tinyglobby → fdir`، وأعاد تشغيل `npm audit --audit-level=high` داخل `apps/ai-intelligence-console` عند **2026-11-18T20:39:02Z** النتيجة `found 0 vulnerabilities` مع رمز خروج `0`.

**لم يُغيَّر أي اعتماد أو ملف قفل أو فحص CI أو كود مصدر.** سحب التقرير ليس إصلاحًا برمجيًا، ولا يجوز الاستشهاد بهذا السجل لاحقًا كدليل على معالجة ثغرة. يظل التنبيهان الشقيقان `CVE-2026-33671` و`CVE-2026-33672` نشطين ومُصلحين في `4.0.4`؛ ولأن الإصدار المستخدم `4.0.7` فإنه خارج نطاقهما — لا تُخفِّض الإصدار ولا تُثبِّته تحت `4.0.4` ولا تُضِف `overrides` ولا تُعطِّل التدقيق ولا تشغّل `npm audit fix --force`.

الأدلة الكاملة وتحليل قابلية الوصول وشروط إعادة الفتح في [سجل السحب](docs/security/PICOMATCH_GHSA_FC5Q_39XC_VJPF.md). لا يغيّر هذا السجل بوابات P01 (**NO-GO**) أو AI-9 (**BLOCKED**) أو قبول تشغيل Codex (**OPEN**)، ولا ينفّذ أي مزامنة مع GitLab.

## GitLab Free CI — تحضير يدوي فقط (لم يُشغَّل)

أُضيف نموذج `.gitlab-ci.yml` لتجهيز فحص مجاني **مستقبلي** لسجل الإنجازات، ويشترط إجراءين منفصلين من المستخدم: إنشاء Pipeline يدويًا عبر واجهة GitLab على الفرع الافتراضي، ثم بدء وظيفة `free_offline_smoke` يدويًا. لا تنشأ Pipelines عند push أو merge request أو schedule أو API، ولا يُستهلك رصيد GitLab بسبب إنشاء الملف على GitHub.

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_free_ci_pilot.py' -v
python3 scripts/milestone_ledger.py --summary
```

هذا **تحضير في GitHub فقط**؛ نسخة GitLab الحالية قديمة ولم تحدث مزامنة أو تشغيل. لا تشغّل وظيفة GitLab قبل التأكد من تجدد حصتها المجانية والحصول على موافقة محددة لنقل نفس مصدر GitHub ومراجعته، مع الحفاظ على حماية `main` وقرارات P01/AI-9. التفاصيل: [دليل GitLab Free CI التجريبي](docs/GITLAB_FREE_CI_PILOT.md).

مشروع عملي لتعلّم DevOps وCI/CD باستخدام GitHub Actions وGitHub Pages. تتضمن المستودع أتمتة إضافية موثقة؛ الصفحة المنشورة حاليًا صفحة HTML ثابتة ولا تحتاج خادم تطبيق أو قاعدة بيانات.


## فحص تطابق نسخة Devobs على GitLab — يدوي وبدون رموز

يمكنك مقارنة التزام `main` العام بين GitHub وGitLab دون مصادقة أو تعديل أي مستودع:

```sh
python3 scripts/check_gitlab_replica_parity.py --json
python3 -m unittest discover -s tests -p 'test_gitlab_replica_parity.py' -v
```

تعني `MATCH` تطابق SHA وقت القراءة فقط (`exit 0`)، و`DRIFT` اختلافهما (`exit 1`)، و`UNKNOWN` تعذر التحقق (`exit 2`). لا ينشئ هذا الفحص مزامنة أو نسخة احتياطية أو Pipeline أو خدمة مدفوعة؛ راجع [حدود فحص GitLab](docs/GITLAB_REPLICA_PARITY.md) قبل اعتماد النتيجة.

## تحضير تحديث GitLab بتقدم آمن فقط (Fast-forward)

أضفنا فحصًا يدويًا باستخدام `git ls-remote` و`git merge-base` للتحقق من إمكانية نقل الالتزامات من GitHub إلى GitLab بدون تغيير التاريخ. الأداة **لا ترفع أي التزام ولا تستخدم مفاتيح**:

```sh
python3 scripts/gitlab_fast_forward_preflight.py --repo . --json
python3 -m unittest discover -s tests -p 'test_gitlab_fast_forward_preflight.py' -v
```

تعني `ALREADY_MATCHED` أن الالتزامين متطابقان عند القراءة، و`FAST_FORWARD_CANDIDATE` أن النقل ممكن نظريًا ويتطلب موافقة المالك وفحص صلاحيات GitLab، و`BLOCKED` ضرورة التوقف. راجع [دليل الفحص الآمن](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md)؛ هذه ليست مزامنة تلقائية أو نسخة احتياطية مثبتة.

## فحص GitLab من GitHub Actions العام — يدوي بالكامل

أُعدّ **فحصان مستقلان** يستخدمان **GitHub Actions العام المجاني** بدل احتياج جهاز Windows المتصل أو رصيد GitLab CI. كلاهما لا يبدأ إلا يدويًا (`workflow_dispatch`) ومقيّد بـ`refs/heads/main`، ولا يعمل تلقائيًا عند الدفع أو طلبات الدمج أو الجدولة:

- [GitLab Replica Read-only Preflight](https://github.com/hamedonassar95/Devobs/actions/workflows/gitlab-replica-preflight-manual.yml): يقارن آخر التزامات GitHub/GitLab باستخدام `git ls-remote` و`git merge-base`، دون نسخ الكود إلى GitLab أو استخدام أسرار أو تشغيل أي Pipeline هناك.
- [GitLab MR Policy Audit](https://github.com/hamedonassar95/Devobs/actions/workflows/gitlab-mr-policy-audit-manual.yml): يقرأ `merge_method` الخاص بسياسة طلبات الدمج فقط، مستقلًا تمامًا عن فحص الأنساب.

نجاح أحدهما لا يعني نجاح الآخر ولا يجيز أي مزامنة. **نجاح فحص الأنساب يُصنَّف `ALREADY_MATCHED` أو `REVIEW_REQUIRED`، ولا تُصدر أي أداة نتيجة باسم `SYNC_APPROVED`.** كلا الفحصين يستخدم `contents: read` فقط، وأكشنات مثبتة بـSHA كامل، و`persist-credentials: false`، ولا يدفع أو يكتب إلى أي مستودع.

يمكن التحقق محليًا من منطق النتائج دون حسابات أو شبكة:

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_hosted_preflight.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_fast_forward_preflight.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_preflight_workflow_contract.py' -v
```

النتائج: `ALREADY_MATCHED` تعني أن SHA متطابق وقت القراءة، و`REVIEW_REQUIRED` تعني فقط أن تحديث Fast-forward ممكن نظريًا ويتطلب موافقة مستقلة قبل أي كتابة، و`BLOCKED` تعني التوقف. **نجاح فحص GitHub ليس موافقة على مزامنة GitLab أو جاهزية SaaS.** هذه الخطوة لا تفتح بوابتي P01 وAI-9 ولا تشغّل خدمة مدفوعة. التفاصيل: [الفحص والاستثناءات](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md).

## فحص طريقة دمج GitLab — للمراجعة فقط

يقرأ فحص `GitLab MR Policy Audit` المستقل إعداد دمج Merge Requests في مشروع GitLab دون مفاتيح أو كتابة، ولا يعمل داخل مهمة الأنساب. عند `merge` أو `rebase_merge` يُظهر `mr_path=MR_ADDS_COMMIT`؛ أي إن **دمج Merge Request العادي** سيُنشئ التزامًا إضافيًا ولن يحافظ على SHA الخاص بـGitHub. عند `ff` يُظهر `mr_path=FF_MR_POLICY_ONLY`.

**مهم:** هذا الإعداد لا يمنع بحد ذاته `git push` العادي بطريقة Fast-forward، لأن صلاحية الدفع إلى الفرع المحمي تُدار بشكل مستقل. لذلك يحتفظ الفحص بالنتيجة `direct_git_push=NOT_EVALUATED`. انتهاء الفحص بنجاح يعني اكتمال القراءة فقط، **ولا يجيز أي مزامنة أو دمج**. تغيير GitLab أو الدفع إلى `main` يتطلب موافقة منفصلة ومراجعة أحدث SHA.

**تشخيص جذر المشكلة (19 نوفمبر 2026):** فشلت خطوة سياسة الدمج في التشغيل اليدوي [44399119755](https://github.com/hamedonassar95/Devobs/actions/runs/44399119755) بسبب سبب عام `unverified_project_metadata`. أظهر الفحص المحلي أن الحقل `merge_method` **غير موجود** في الاستجابة العامة للمشروع عند الطلب بلا مصادقة، بينما تطابق `id` و`path_with_namespace` و`default_branch` و`visibility`؛ وتوثّق GitLab أن الحقول المُعادة تختلف حسب صلاحيات المستخدم ([Projects API](https://docs.gitlab.com/api/projects/)). يعرض الفحص الآن سببًا دقيقًا مثل `missing_field:merge_method` أو `mismatched_field:<name>` أو `wrong_type:<name>` دون إظهار أي قيمة من المزوّد.

يبقى رمز الخروج `2` والنتيجة `BLOCKED` كما هما، ولا يُفسَّر غياب الحقل كقيمة افتراضية `merge` أو `ff`؛ فسياسة الدمج تظل **`UNVERIFIED`** إلى أن يقوم المالك بقراءة موثّقة بإذن أو بتسجيل الإعداد من واجهة GitLab. لا يُغيِّر هذا إعدادات GitLab أو حماية الفروع أو المزامنة أو بوابات الإصدار، ولا يخفف أي فحص أمني.

```sh
python3 -m unittest discover -s tests -p 'test_gitlab_merge_policy.py' -v
python3 -m unittest discover -s tests -p 'test_gitlab_preflight_workflow_contract.py' -v
python3 -m py_compile scripts/gitlab_merge_policy.py
```

التوثيق: [الفرق بين Merge Request وGit Fast-forward](docs/GITLAB_FAST_FORWARD_PREFLIGHT.md). لا خدمات مدفوعة، ولا GitLab CI، ولا نقل تلقائي للكود.

## خطة تعافي Render OIDC بعد قرار البيانات التجريبية

**قرار المالك (18 نوفمبر 2026):** بيانات قاعدة Render التجريبية الحالية لا تحتاج إلى حفظ؛ هذا لا يجيز حذف القاعدة أو تعطيل الخدمة، ولا يُسقط متطلبات النسخ الاحتياطي عندما توجد بيانات حقيقية. موعد انتهاء قاعدة Render Free الحالية: **5 ديسمبر 2026**.

**العائق المثبت:** نشر Render الأخير فشل في مرحلة `oidc` بخطأ `invalid_staging_config`، لكن اسم الإعداد غير الصالح لم يُحدَّد. نستخدم أداة [P01 Startup Triage](docs/P01_STARTUP_TRIAGE.md) الموجودة أصلًا لفحص **وجود أسماء المتغيرات فقط**؛ وحتى إذا كانت جميع الأسماء موجودة، تعيد الأداة رمز الخروج `5` بدل `0` لأن القيم ما زالت غير متحققة. بعدها نراجع صحة قيم OIDC سرًّا لدى المشغّل قبل أي نشر جديد. لا تُرسل مفاتيح أو بيانات اتصال أو صورًا لقيم المتغيرات، ولا تعطّل المصادقة لتجاوز المشكلة. التفاصيل والخطوات: [خطة تعافي Render الآمنة](docs/RENDER_OPENAI_STAGING_RUNBOOK.md#2026-11-18-owner-checkpoint--disposable-data-and-oidc-recovery). بوابة P01 لا تزال `BLOCKED / NO-GO` وAI-9 لا تزال `BLOCKED`.

## بوابة تطابق إصدار Render مع GitHub — قراءة محلية فقط

تستخدم أداة الجاهزية الموجودة `scripts/check_free_staging_health.py` لقطة بيانات **schema_version=3** تحتوي `render.canonical_main_commit` (آخر SHA متحقق منه من GitHub) و`render.web_last_deploy_commit` (SHA آخر نشر متحقق منه من Render). إذا اختلفا، تعرض `RENDER_DEPLOY_SOURCE_OUTDATED` ضمن أسباب استمرار `REVIEW_REQUIRED`، **حتى عندما يُصنّف النشر `live`**. وجود SHA متطابق لا يثبت نجاح الدخول أو عزل المستأجرين أو جاهزية الإنتاج؛ وتاريخ اللقطة يخضع لفحص التقادم. هذا فحص محلي مجاني لا يجلب إعدادات سرية ولا يشغّل نشرًا أو pipeline.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

راجع [خطة تعافي Render](docs/RENDER_OPENAI_STAGING_RUNBOOK.md#render-source-commit-drift-preflight--2026-11-18). لا تغيّر إعدادات OIDC ولا تنشر على Render استنادًا إلى اختلاف SHA وحده.

## فحص جاهزية موارد Devobs المجانية — Render + Supabase

تقرير محلي للقراءة فقط يجمع حالة موارد **Devobs** المجانية من لقطة مزودين محدودة دون مفاتيح أو اتصالات مباشرة، ويرفض إعلان جاهزية الإنتاج عند وجود أدلة ناقصة أو قديمة. لا يستخدم موارد مشروع صيانة الهواتف.

```sh
python3 scripts/check_free_staging_health.py --json
python3 -m unittest discover -s tests -p 'test_free_staging_health.py' -v
```

يتحقق الإصدار الثاني من الجرد أيضًا من **آخر حالة نشر فعلية** على Render والالتزام الأصلي لها؛ إذ انتهت أحدث محاولة بـ`update_failed`، فيظهر مانع `RENDER_LATEST_DEPLOY_NOT_LIVE`. `live` وحدها لا تكفي للموافقة على الإنتاج، ولا يجري هذا الفحص أي اتصال خارجي أو نشر.

النتيجة المقصودة هي `REVIEW_REQUIRED` (رمز 1) أو `INVALID_SNAPSHOT` (رمز 2) وليس الموافقة على النشر. قاعدة Render المجانية تنتهي في **2026-12-05** حسب آخر جرد، وSupabase الخاص بـDevobs غير نشط؛ راجع [التقرير والأدلة وحدود التكاليف](docs/P01_FREE_STAGING_PROVIDER_GATE_2026-11-17.md). لا تنفذ الأداة نشرًا أو مزامنة أو ترقية مدفوعة.

## فحص انتهاء PostgreSQL المجانية (دون اتصال أو تكلفة)

تتحقق [أداة فحص موعد انتهاء Render Free](scripts/check_render_free_expiry.py) من تاريخ انتهاء قاعدة البيانات وفق [لقطة جرد محدودة](docs/p01/render-free-expiry-snapshot.json) بتاريخ 2026-11-15. لا تقرأ الأداة بيانات القاعدة أو الاتصال بالمزود أو أسرارًا، ولا تنشر أو ترقّي أو تحذف شيئًا.

```sh
python3 scripts/check_render_free_expiry.py --json
python3 -m unittest discover -s tests -p 'test_render_free_expiry.py' -v
```

**رموز الخروج:** `0` يعني أن الموعد ليس قريبًا حسب لقطة حديثة فقط (ليس موافقة تشغيل)، و`1` يعني مراجعة بشرية لازمة أو انتهاء/تعذر الوصول أو تقادم اللقطة لأكثر من 7 أيام، و`2` يعني أن ملف الجرد غير صالح. **المتوقع حاليًا هو `REVIEW_REQUIRED` ورمز `1`** حتى يُتخذ قرار الاحتفاظ أو الإنهاء؛ وبعد تقادم اللقطة، لا يمكن اعتبارها حالة حية. موعد انتهاء القاعدة المسجل: **2026-12-05 10:33 UTC**، وليس تاريخًا يجيز الحذف أو الترقية. راجع [حدود الدليل وخيارات القرار](docs/P01_RENDER_FREE_RESOURCE_CHECKPOINT_2026-11-15.md). بوابة P01 تبقى `NO-GO`.

## قارئ CI لمحفظة المشاريع العامة (يدوي ومن دون مفاتيح)

أصبح بالإمكان فحص نتائج GitHub CI العامة لأربعة مشاريع مستقلة من تشغيل محلي واحد، مع مطابقة نتائج كل تشغيل لالتزام `main` الخاص بالمشروع، ودون مراقبة مستودعات خاصة أو نقل أكوادها أو أسرارها:

```sh
node scripts/portfolio_public_ci.mjs
node --test tests/portfolio_public_ci.test.mjs
```

يمكنك كذلك فتح [قارئ CI عبر المتصفح](https://hamedonassar95.github.io/Devobs/assets/public-ci/) واختيار زر **فحص المشاريع الأربعة** لعرض الحالات العامة، يدويًا ودون مفاتيح أو مراقبة تلقائية.

بعد فحص المستودعات الأربعة في [القارئ العام](https://hamedonassar95.github.io/Devobs/assets/public-ci/)، يمكنك تنزيل أحداث CI المؤهلة بصيغة CloudEvents وتحليلها من جهازك باستخدام **محرك AI-7 الموجود بالفعل** (قراءة فقط، دون تشغيل خادم أو استنتاج سبب جذري من حالة CI وحدها):

```sh
node scripts/portfolio_ci_ai7.mjs --input /path/to/devobs-portfolio-ci.cloudevents.jsonl
```

**جديد — فحص وتحليل CI العامة مباشرة بأمر واحد عند الطلب** (من دون تنزيل الملف أو حفظه، ودون مفاتيح أو تنفيذ إصلاحات):

```sh
node scripts/portfolio_ci_ai7_live.mjs
```

الأمر يعرض نتيجة كل مشروع ويشغّل AI-7 فقط للأحداث المكتملة التي تحققت شروطها. إذا كانت النتائج ناقصة يُظهر حالة جزئية ويخرج برمز فشل، حتى لا يعتبر التشغيل ناجحًا بالخطأ.

**للتشغيل من GitHub دون كمبيوتر:** بعد دمج التغيير يمكنك فتح [Portfolio AI-7 Public CI Observation](https://github.com/hamedonassar95/Devobs/actions/workflows/portfolio-ai7-manual.yml) واختيار **Run workflow** على `main`. يقرأ أربعة مستودعات عامة، ويضع ملخصًا عربيًا/إنجليزيًا محدودًا وملف JSON منقّى للمراجعة داخل Actions، دون مفاتيح أو نشر أو جدولة. إذا كانت الأدلة ناقصة يتوقف بنتيجة فشل واضحة، ولا يعتبر هذا بحد ذاته عطلًا في كود Devobs.

التفاصيل ومصادر GitHub والتحذيرات: [Portfolio Public CI](docs/integrations/PORTFOLIO_PUBLIC_CI.md). هذه قراءة عامة عند الطلب فقط، لا تثبت التشغيل التجاري ولا تفعّل خدمات مدفوعة أو ترسل أحداثًا تلقائيًا.

## تقرير موحّد للموارد المجانية — محلي فقط

يمكن الآن جمع نتائج أدوات الفحص **الموجودة أصلًا** في أمر واحد دون حسابات خارجية أو مفاتيح أو إنشاء خدمات:

```sh
python3 scripts/free_readiness_one_command.py --json
python3 -m unittest discover -s tests -p 'test_free_readiness_one_command.py' -v
```

يعيد الأمر استخدام فحص دفتر الإنجازات، وجرد الموارد المجانية، ومرشحي التكامل، ولقطة Render/Supabase، وتاريخ انتهاء Render Free. النتيجة المعتادة `REVIEW_REQUIRED` (exit 1) وليست نجاح إنتاجي، و`INVALID_CHECKS` (exit 2) عند أي فحص ناقص أو نتيجة غير متوقعة. لا يتصل الأمر بمزود أو مستودع آخر ولا ينقل أسرارًا أو يحدّث إعدادات. قد تكون مؤشرات الموارد قديمة؛ **نجاح الفحص لا يثبت جاهزية الخدمات الحية أو يجيز الدمج والنشر**.

## فحص الموارد المجانية (دون تفعيل خدمات جديدة)

أُضيف [فحص جاهزية الموارد المجانية](docs/strategy/DEVOBS_FREE_RESOURCE_PLAN_2026.md) لفحص 12 ملفًا موجودًا في المستودع وتأكيد بقاء السياسة دون تشغيل خارجي أو دفع. شغّل `python3 scripts/check_free_resource_plan.py --json` لإظهار تقرير محدود للملفات فقط؛ لا يثبت ذلك جاهزية الخدمات المستضافة أو مجانية الفاتورة الفعلية.

للتحضير المنفصل لمشاريعنا، راجع [خريطة تكامل الموارد المجانية المرشحة](docs/portfolio/PORTFOLIO_FREE_READINESS.md) وشغّل `python3 scripts/portfolio_free_readiness.py --json`. هذا تقرير تخطيط محلي؛ لا يثبت اتصال أي مستودع آخر ولا يسمح بنقل بياناته.

## تكامل محلي جديد: واجهة AI Intelligence Console مع محرك AI-7

تتيح [الواجهة الحالية](apps/ai-intelligence-console/README.md) في قسم Overview قراءة ملخصات **محرك AI-7 الحقيقي محليًا** عند الضغط يدويًا على «قراءة المحرك المحلي»؛ عرض الأعداد وحالات المراحل السبع فقط، دون سجلات خام أو صلاحيات تنفيذ. المسار معطّل افتراضيًا ولا يتصل إلا بعنوان loopback ثابت على نفس الجهاز عند التفعيل الصريح. هو تطوير منتج برمجي تجريبي وليس ربطًا بخوادم الإنتاج أو إطلاق SaaS؛ راجع [التشغيل والاختبارات وحدود الأمان](apps/ai-intelligence-console/README.md#ai-7-local-snapshot-integration-optional-read-only).

## DevOps AI Intelligence — مصدر موحّد

هذا المستودع `Devobs` هو المصدر الأساسي للمشروعين. مراحل الذكاء التشغيلي المحلية AI-1 إلى AI-7 ولوحة AI-7 مدمجة هنا بالفعل؛ نضيف فقط ما يسد فجوة واضحة بدل نسخ مكونات مكررة. المحركات الحالية محلية وحتمية/إحصائية ولا تستدعي نموذجًا لغويًا.

### تطبيق DevOps AI Intelligence المحفوظ

نُقلت واجهة React/TypeScript من مستودع `DevObs-ai-Intelligence-` إلى [`apps/ai-intelligence-console/`](apps/ai-intelligence-console/)، مع الاحتفاظ بتاريخ المصدر ورخصة MIT. تضم لوحة الخوادم والحوادث والنشر، واجهة GitHub، مساحة Google Workspace، Gemini، وعرض غرفة الخوادم ثلاثي الأبعاد. هي نموذج أولي منفصل عن محركات AI-1 إلى AI-7 الموجودة في الجذر؛ سجلاتها تجريبية ولا تتحكم بخوادم أو عمليات نشر حقيقية. Firebase وGoogle وGemini متوقفة افتراضيًا، وقواعد Firestore تمنع الوصول، والتطبيق غير مشمول بنشر GitHub Pages. راجع [حالة التطبيق وتشغيله محليًا](apps/ai-intelligence-console/README.md).

للاطلاع على علاقة مستودعات `ops` وAI Intelligence و`devobs-saas` ومصادر قواعد بياناتها وحدود الدمج الآمن، راجع [خط أساس توحيد المستودعات وقواعد البيانات](docs/architecture/REPOSITORY_DATABASE_CONSOLIDATION.md) و[الخريطة الآلية](docs/architecture/repository_database_map.json). الخريطة تميّز روابط المصدر عن الاتصالات الحية، ولا تفعّل Firebase أو تدمج قواعد بيانات.

لتمييز الموجود والمتحقق من التجريبي والمحجوب قبل أي إضافة، راجع [مواءمة أبحاث Devobs AI لعام 2026](docs/strategy/DEVOBS_AI_RESEARCH_ALIGNMENT_2026.md)، و[مراجعة منظومة DevOps والذكاء الاصطناعي](docs/AI_DEVOPS_ECOSYSTEM_REVIEW_2026-11-11.md)، و[خارطة التنفيذ المرحلية](docs/strategy/DEVOBS_AI_ROADMAP_2026.md). هذه المستندات تخطط للعمل ولا تفتح AI-9 أو P01 أو تجيز نشرًا.

لتسجيل متطلبات أي تقييم مستقل مستقبلي لحوادث AI-9 الطبيعية، راجع [بروتوكول التسجيل المسبق](docs/AI9_REAL_INCIDENT_PREREGISTRATION.md). هذا تصميم فقط؛ لا توجد مجموعة مؤهلة معتمدة، ولا يفتح البوابة أو يجيز التقييم.

```text
بيانات تشغيل اصطناعية محلية
  → AI-1 استقبال وتحقق
  → AI-2 كشف شذوذ → AI-3 تحليل → AI-4 توصيات runbook
  → AI-5 اتجاهات → AI-6 تغذية راجعة اختيارية → AI-7 لوحة/API للقراءة فقط
  → GitHub Actions: اختبارات وفحوص أمنية ومراجعة PR اختيارية
```

لرؤية مسار AI-1 إلى AI-7 يعمل محليًا على بيانات اصطناعية، شغّل `node scripts/local_advisory_acceptance.mjs` من جذر المستودع. [دليل القبول المحلي وحدوده](docs/LOCAL_ADVISORY_V01_ACCEPTANCE.md) يشرح النتيجة والاختبارات؛ هذا العرض لا يثبت جاهزية AI-9 أو الاستضافة أو الإنتاج.

إضافة PR-Agent اختيارية ومطفأة افتراضيًا، وتعمل كمراجع بديل عن مراجعة Codex حتى لا يتكرر الاستدلال. إعدادا Ollama وLocalAI المحليان موثقان في [`models/docker-compose.yml`](models/docker-compose.yml)، ولا يعملان تلقائيًا ولا يتضمنان أوزان نماذج. يمكن اختيار أحدهما يدويًا لتشخيص السجلات عبر API staging بعد الموافقات الصريحة، لكنهما لا يتصلان تلقائيًا بسلسلة AI-1 إلى AI-7. يوجد أيضًا [مساعد برمجة محلي اختياري باستخدام Aider وOllama](docs/LOCAL_AI_CODE_ASSISTANT.md)، لا يحتاج مفتاح API ويعطّل الالتزام التلقائي. أمثلة K8sGPT وHolmesGPT اختيارية ومحدودة للقراءة في [`k8s/`](k8s/README.md)، ولا تثبّت الأدوات ولا تطبق إعدادات على عنقود. يظل MLflow مرشحًا لمراجعة منفصلة.

| المكوّن الخارجي المضاف أو الموثق | الإصدار/البصمة | الرخصة | النطاق |
| --- | --- | --- | --- |
| [PR-Agent](https://github.com/The-PR-Agent/pr-agent) | v0.49.0؛ صورة مثبتة على digest موثق في [دليل التكامل](docs/PR_AGENT_INTEGRATION.md) | [MIT](https://github.com/The-PR-Agent/pr-agent/blob/v0.49.0/LICENSE) | مراجعة PR اختيارية؛ غير مفعّلة ما لم تُستوفَ بوابات الاختيار والميزانية والتحقق من المصدر والاعتماد الموجود |
| [Ollama](https://github.com/ollama/ollama) | v0.40.15؛ digest موثق في [دليل النماذج](models/README.md) | [MIT](https://github.com/ollama/ollama/blob/v0.40.15/LICENSE) | خادم CPU محلي اختياري؛ لا ينزل نموذجًا تلقائيًا؛ يشغّل تشخيص staging ومساعد البرمجة المحلي بعد الإعداد |
| [Aider](https://github.com/Aider-AI/aider) | v0.86.2؛ استخدام اختياري موثق | [Apache-2.0](https://github.com/Aider-AI/aider/blob/v0.86.2/LICENSE.txt) | مساعد برمجة تفاعلي محلي عبر Ollama؛ ليس ضمن CI ولا يعمل تلقائيًا |
| [LocalAI](https://github.com/mudler/LocalAI) | v4.12.1؛ digest موثق في [دليل النماذج](models/README.md) | [MIT](https://github.com/mudler/LocalAI/blob/v4.12.1/LICENSE) | CPU اختياري خلف profile؛ لا ينزل نموذجًا تلقائيًا؛ اختيار يدوي ممكن لـAPI التشخيص فقط |
| [GitHub MCP Server](https://github.com/github/github-mcp-server/tree/v2.1.0) | v2.1.0؛ المصدر `4bcdcdf8d7beee98c9448e73e257308280924cc4` وصورة OCI مثبتة على `sha256:f6056fc10bfffcc8c81a6417a2e9ca12808647e8dd6049642a4feaadee0e0f8a` | [MIT](https://github.com/github/github-mcp-server/blob/v2.1.0/LICENSE) | خادم محلي اختياري لـCodex، أدوات GitHub للقراءة فقط ولمستودعات عامة؛ لا يدخل في CI أو تشغيل التطبيق، ولا يُفعّل تلقائيًا |
| [Grafana MCP](https://github.com/grafana/mcp-grafana/tree/v2.3.0) | v2.3.0؛ المصدر `c8cafb67854c45e79f8f9b5fca7d9b3a403f1771`؛ بصمة حزمة Windows x64 في [الدليل](docs/GRAFANA_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/grafana/mcp-grafana/blob/v2.3.0/LICENSE) | خادم Codex محلي اختياري؛ لوحات Grafana وPrometheus فقط، مع حجب الكتابة وAPI؛ غير مفعّل افتراضيًا |
| [Kubernetes MCP Server](https://github.com/containers/kubernetes-mcp-server/tree/v0.1.2) | v0.1.2؛ المصدر `66553fed5c16454e5814b41e331b4357f15806d8`؛ بصمة Windows x64 في [الدليل](docs/KUBERNETES_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/containers/kubernetes-mcp-server/blob/v0.1.2/LICENSE) | Codex محلي اختياري؛ أحداث namespace محدد فقط مع `read_only` وRBAC فعلي؛ لا سجلات أو أسرار أو تعديل |
| [Argo CD MCP](https://github.com/argoproj-labs/mcp-for-argocd/tree/v0.9.0) | v0.9.0؛ المصدر `28d15ca69b0c31387cc6ec73d201fd13c5d22b6a`؛ صورة مثبتة على digest مع بيان بناء في [الدليل](docs/ARGOCD_MCP_INTEGRATION.md) | [Apache-2.0](https://github.com/argoproj-labs/mcp-for-argocd/blob/v0.9.0/LICENSE) | Codex محلي اختياري؛ أداة `list_applications` فقط مع موافقة وRBAC مقيد؛ بلا كتابة أو موارد أو سجلات |
| [K8sGPT](https://github.com/k8sgpt-ai/k8sgpt) | v0.4.41؛ أمثلة CLI فقط | [Apache-2.0](https://github.com/k8sgpt-ai/k8sgpt/blob/v0.4.41/LICENSE) | فحص يدوي محدود بالـnamespace؛ أمر المثال لا يطلب شرحًا من نموذج |
| [HolmesGPT](https://github.com/HolmesGPT/holmesgpt) | 0.46.0؛ أمثلة إعداد فقط | [Apache-2.0](https://github.com/HolmesGPT/holmesgpt/blob/0.46.0/LICENSE) | إعداد toolset وصلاحيات قراءة فقط؛ لا تثبيت أو استدلال تلقائي |

مجلدات `agents/` و`workflows/` و`models/` و`mlops/` هي فهارس توثيقية لهذه المرحلة؛ ملفات التشغيل الفعلية تبقى في مواقعها الحالية. راجع [خريطة الوكلاء](agents/README.md)، [خريطة سير العمل](workflows/README.md)، [خريطة النماذج](models/README.md)، [أمثلة Kubernetes الاختيارية](k8s/README.md)، [تكامل PR-Agent](docs/PR_AGENT_INTEGRATION.md)، [خريطة المراقبة](monitoring/README.md)، و[خريطة MLOps](mlops/README.md).

لتسجيل نتيجة CI من مستودع LiveOps دون إرسال محتوى التطبيق أو بيانات Gemini، راجع [جسر LiveOps الاختياري](docs/LIVEOPS_CI_INTEGRATION.md). يسجل الجسر بيانات تشغيل فقط ولا يفعّل استدلالًا أو إصلاحًا تلقائيًا.

## مركز الأتمتة

- **تشخيص أمن CI / Gitleaks:** [دليل مراجعة تاريخ Git في GitBook](docs/gitbook-sync-prep/GITLEAKS_HISTORY_DIAGNOSTICS.md) — فصلٌ بين عطل تحقق Git وبين تسريب مؤكّد، دون تعطيل المسح أو نشر أسرار.

- **ابدأ من هنا:** [مركز الأتمتة وسير التشغيل الموحد](docs/AUTOMATION_HUB.md)
- **CineForge-AI CI review-only handoff:** [فحص محدود لنتائج CI دون نقل الكود أو تشغيل خدمات](docs/CINEFORGE_CI_REVIEW_HANDOFF.md) — بوابة مراجعة محلية فقط، ليست تكاملًا حيًا ولا إصلاحًا لخلل GitHub Runner.
- **Cross-project Runner evidence triage (offline):** [تشخيص محدود لأدلة GitHub Actions لمشروعي CineForge وPhone Repair Assistant](docs/integrations/CINEFORGE_RUNNER_TRIAGE.md) — يفصل بين المعلومات المفقودة (`null`) وقيم Runner الفعلية، ويسمح فقط بأسماء المشاريع والوظائف المحددة؛ لا يجلب سجلات خاصة ولا ينفّذ عمليات أو يدّعي سببًا جذريًا.
- **جاهزية إصدارات المشاريع:** [Portfolio v1 release-readiness tracker](docs/portfolio/PORTFOLIO_V1_READINESS.md) — لقطة موثقة بالأدلة لمستودعات المالك الخمسة؛ تميّز نجاح CI عن النشر والتشغيل الفعلي، ولا تغيّر حالة أي بوابة.
- **سجل الإنجازات والبوابات:** [Milestone Ledger](docs/MILESTONE_LEDGER.md) — فحص دون شبكة يربط كل إنجاز موثق برقم PR وSHA ودليل CI، ويعرض النواقص دون تغيير حالة جاهزيتها.
- **تكامل OpenArt الاختياري:** [حوكمة طلبات الصور والفيديو عبر MCP](docs/OPENART_MCP_INTEGRATION.md) — صيغة طلب خاصة آمنة دون شبكة أو كلفة، مع موافقة منفصلة قبل أي توليد.
- **GitHub MCP للمطورين:** [إعداد اختياري محلي للقراءة فقط](docs/GITHUB_MCP_INTEGRATION.md) — يستعمل الخادم الرسمي من صورة مثبتة؛ لا تُحفظ أسرار في المستودع ولا يعمل تلقائيًا.
- **Grafana MCP للمطورين:** [إعداد اختياري محلي للقراءة فقط](docs/GRAFANA_MCP_INTEGRATION.md) — يقتصر على لوحات Grafana ومقاييس Prometheus؛ لا يُفعّل في إعداد المستودع.
- **Kubernetes MCP للمطورين:** [إعداد اختياري لأحداث namespace واحد](docs/KUBERNETES_MCP_INTEGRATION.md) — أداة أحداث فقط، مع صلاحية Kubernetes `list` الفعلية؛ لا يُفعّل في إعداد المستودع.
- **Argo CD MCP للمطورين:** [قراءة حالة التطبيقات](docs/ARGOCD_MCP_INTEGRATION.md) — أداة `list_applications` فقط، مع موافقة Codex ورمز Argo CD مخصص للقراءة؛ غير مفعّل افتراضيًا.
- [Devobs AI DevOps Control Room](docs/AI_DEVOPS_CONTROL_ROOM.md): توثيق مسارات AI وCI وحالة التحقق من المصدر مقابل التشغيل.
- [Devobs بالموارد المجانية الحالية](docs/FREE_DEVOBS_MODE.md): معاينة منشورة لمسار AI-1 إلى AI-7 بعينة اصطناعية، ومذكرات في المتصفح، وتشغيل محلي دون مفاتيح أو رسوم استضافة جديدة.
- [استقبال أحداث AI-1 محليًا](docs/AI_EVENT_INGESTION.md): صيغة موحّدة وملف JSONL محلي؛ بلا اتصالات أو خدمات خارجية.
- [جسر CloudEvents لنتائج CI](docs/integrations/CLOUDEVENTS_CI_BRIDGE.md): محوّل محلي غير موثّق المصدر إلى مخطط AI-1 القائم، ويشمل CineForge-AI بحدث اصطناعي فقط دون مرسل حي أو نقل بيانات؛ بوابة `REVIEW_ONLY` مستقلة.
- [جسر OpenTelemetry OTLP لمقياس الخطأ](docs/integrations/OTLP_ERROR_RATE_BRIDGE.md): محوّل اصطناعي محلي لمقياس `error_rate_pct` إلى AI-1؛ بلا اتصالات أو بيانات عملاء أو خدمات مدفوعة.
- [كشف الشذوذ AI-2 محليًا](docs/AI_ANOMALY_DETECTION.md): مؤشرات إحصائية قابلة للتفسير على أحداث مقاييس محلية اصطناعية.
- [تحليل الحوادث AI-3 محليًا](docs/AI_INCIDENT_ANALYSIS.md): تجميع سجلات اصطناعية وفرضيات أسباب محتملة وسياق CI فقط.
- [توصيات AI-4 المحلية](docs/AI_RECOMMENDATIONS.md): مطابقة فرضيات AI-3 مع runbooks ثابتة، بوضع الاقتراح فقط.
- [تقارير الاتجاه AI-5 محليًا](docs/AI_TREND_REPORTS.md): ملخص يومي/أسبوعي واستقراء أولي لمقاييس سجل محلي دون اتصال خارجي.
- [تغذية راجعة للتوصيات AI-6](docs/AI_FEEDBACK_LEARNING.md): تسجيل قبول/رفض محلي اختياري يؤثر في ترتيب المراجعة بعد حد أدنى من القرارات.
- [لوحة وAPI الذكاء التشغيلي AI-7](docs/AI_LOCAL_DASHBOARD.md): لقطة محلية للقراءة فقط؛ لا تُنشر مع الموقع ولا تعرض السجلات الخام. تتضمن تصديرًا اختياريًا لملخصات مجمعة إلى Google Docs، وجدولة موعد متابعة في تقويم Google ثانوي بعد موافقة المستخدم؛ كلاهما معطّل افتراضيًا.
- [تدقيق حوكمة main الحالي](docs/DEVOBS_MAIN_GOVERNANCE_AUDIT.md): القواعد الفعالة وفحوص PR وحالة الموافقات وفق GitHub API.
- [P00 release gate evidence](docs/P00_RELEASE_GATE_EVIDENCE.md): current branch rules, exact-main CI evidence, release safeguards and owner exit checklist.
- [P00 unsigned owner decision packet](docs/P00_OWNER_DECISION.md): immutable evidence baseline and blank GO/NO-GO fields for the human owner.
- [P00 PR #253 image-scan gap review](docs/P00_PR253_GAP_REVIEW.md): overlap with merged Trivy CI, unique scan-report gaps, and recommended rework.
- CI stages and validates `_site`; the main Pages release downloads the same run-scoped artifact across partial retries and revalidates it before publication. Rollback and Vercel remain separate paths; see [CI details](docs/CI.md).
- **Container security in CI:** the existing scan job builds `devobs-web:<checked-out SHA>` and Trivy 0.76.1 scans only that local Docker image. The fail-closed JSON policy requires the report's `container_image` type and exact `ArtifactName`; scanner/image/report errors or HIGH/CRITICAL findings (including unfixed) fail the required `validate` gate. The JSON report is retained for seven days and no image is published. Validate changes with `python3 -m unittest discover -s tests -p 'test_trivy_report_policy.py' -v` and `python3 scripts/check_action_pins.py`; see [CI details](docs/CI.md).
- [قرار P00 بشأن PR #262](docs/P00_PR262_DISPOSITION.md): سجل دليل الإحلال وحالة تعليق الإغلاق بانتظار حسم مراجعة PR.
- [تقرير جاهزية Devobs الحالي](docs/DEVOBS_READINESS_CURRENT.md): حالة موثقة بالأدلة على SHA الحالي، مع فصل النشر الثابت عن جاهزية API وSaaS غير المثبتة.
- [Staging acceptance evidence](docs/STAGING_ACCEPTANCE.md): separates the mocked HTTP smoke contract from the full `build_app()` and tenant-read integration against disposable PostgreSQL 17 in CI; neither proves Render readiness or changes P01 **NO-GO / BLOCKED**.
- [P01 startup configuration triage](docs/P01_STARTUP_TRIAGE.md): an offline, presence-only inventory checker for required staging names; it never reads values and cannot prove hosted readiness or approve P01. New source-side startup diagnostics distinguish missing required configuration from an invalid setting through fixed reason codes without exposing values; [staging runbook](docs/RENDER_OPENAI_STAGING_RUNBOOK.md). Actual Render startup remains unverified.
- [P01 managed-staging activation decision](docs/P01_ACTIVATION_READINESS.md): default NO-GO owner checklist. `/readyz` coalesces PostgreSQL probes with a 250 ms per-process result cache, and concurrent followers now fail closed after a bounded 4-second wait if a DB probe stalls. This is **not** a hosted rate limiter, successful Render DB connection, or approval for live staging; see [staging RLS and readiness details](docs/POSTGRES_RLS_STAGING.md). See the [region/budget decision](docs/P01_REGION_BUDGET_SECURITY.md) and [Render + Supabase proposal](docs/RENDER_SUPABASE_STAGING.md).
- [Devobs Production Execution Roadmap](docs/plans/2026-10-26-devobs-production-execution-roadmap.md): sequential P00–P12 gates, current evidence, blockers, and owner signoffs.

## التثبيت والتشغيل محليًا

المتطلبات: Git، وPython 3.10 أو أحدث لفحوص الموقع والاختبارات، وNode.js لاختبارات الحوادث ومراحل AI-1 إلى AI-7 المحلية. صفحة الموقع ولوحة AI-7 المحلية لا تتطلبان حزم واجهة أمامية. تطبيق React الاختياري داخل `apps/ai-intelligence-console/` يتطلب Node.js 22.12 أو أحدث (يوصى بـ24) ويُشغّل من دليله وفق تعليماته؛ لا يدخل في نشر Pages.

```sh
git clone https://github.com/hamedonassar95/Devobs.git
cd Devobs
python3 -m http.server 8000 --bind 127.0.0.1
```

افتح <http://127.0.0.1:8000> في المتصفح. لإيقاف الخادم اضغط `Ctrl+C`. على Windows استخدم `py -3 -m http.server 8000 --bind 127.0.0.1` بدلًا من `python3`.

## الاختبارات والفحوص

من جذر المستودع:

لتشغيل مجموعة اختبارات Python كاملة في بيئة محلية جديدة، ثبّت الاعتماديات المقفلة في بيئة افتراضية. بعض اختبارات عقود YAML تستخدم PyYAML، أو Ruby/Psych إذا كان متاحًا:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --disable-pip-version-check --require-hashes -r requirements-api.lock -r requirements-dev.lock
```

بعدها شغّل الأوامر التالية. اختبارات PostgreSQL تتخطى نفسها ما لم تُضبط قواعد بيانات اختبار معزولة عبر متغيرات DSN الموثقة في CI.

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

لتشغيل لوحة AI-7 محليًا مع API للقراءة فقط، اتبع [دليل اللوحة المحلية](docs/AI_LOCAL_DASHBOARD.md). تدعم اللوحة أيضًا مذكرات مشغّل محلية في تخزين المتصفح مع البحث والتثبيت والأرشفة والاستعادة المؤكدة؛ لا تُرسل المذكرات إلى الخادم أو AI-6. يمكن تفعيل حفظ ملخص مجمّع في Google Docs أو جدولة موعد متابعة في تقويم Google ثانوي اختياريًا بعد إعداد OAuth Client ID. لا تنشر اللوحة أو تعرضها عبر نفق؛ الموقع المنشور يبقى صفحة ثابتة بلا API.

يفحص CI شيفرة Python باستخدام Bandit، والاعتماديات باستخدام `pip-audit`. لتشغيل الفحوص محليًا:

```sh
python3 -m pip install -r requirements-dev.txt
python3 -m bandit -r scripts -x scripts/check_site.py
pip-audit --requirement requirements-dev.txt
```

يفحص GitHub Actions الأسرار باستخدام Gitleaks CLI مثبت الإصدار والبصمة، ويتحقق من أن نطاق Git وفروقات commits الدمج يطابقان حدث CI وSHA المصدر. يضيف الملخص دليل النطاق والعدّادات دون طباعة الأسرار أو رفع تقرير النتائج. راجع [تفاصيل نطاق Gitleaks وحدوده](docs/CI.md) و[نطاق وضوابط DevSecOps](docs/DEVSECOPS.md). لا يحتاج تشغيل الموقع أو الاختبارات إلى مفاتيح أو حسابات خدمات خارجية.

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

يتضمن المستودع إعدادًا محليًا لـPrometheus وGrafana وAlertmanager. Node Exporter اختياري لمضيف Linux، كما تتوفر إضافة OpenTelemetry Collector محلية اختيارية لتحويل مجموعة ضيقة من مقاييس OTLP إلى Prometheus الموجود. خدمة WSGI يمكنها إرسال Histogram واحد لزمن الطلب محليًا بعد تفعيل صريح؛ القياس معطّل افتراضيًا وبلا تسميات للطلب. الموقع الثابت لا يوفّر نقطة `/metrics`. راجع [دليل OpenTelemetry](docs/integrations/opentelemetry.md) قبل تشغيل ملف تعريف `otel`.

```sh
export GRAFANA_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose -f monitoring/compose.yml up --detach
```

الواجهات المحلية: Prometheus <http://127.0.0.1:9090>، Grafana <http://127.0.0.1:3000>، Alertmanager <http://127.0.0.1:9093>. تهيئة OpenTelemetry TLS ورمز الوصول المحلي وبدء الملف الاختياري موضحة في [الدليل](docs/integrations/opentelemetry.md). لإضافة مقاييس Linux:

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
4. بعد الدمج، لا ينشر `push` إلى `main` تلقائيًا. يراجع المالك SHA وآثار النشر، ثم يشغّل **CI** يدويًا من `main` ويختار `confirm_release=true`؛ القيمة الافتراضية `false`، والنشر مشروط بنجاح `validate` وArtifact الموقع في التشغيل نفسه.
5. راجع إعداد مراجعي بيئة `github-pages` منفصلًا؛ فاسم البيئة لا يضمن وجود مراجعين. لا تدمج PR يغير ضوابط الإصدار قبل مراجعة المالك لآثار النشر.
6. راجع رابط النشر ونتيجة فحص الصحة في GitHub Actions.

فحص صحة النشر يقرأ `deployment.json` ويطابق SHA الكامل للمصدر. عند عطل نقل مؤقت يعيد المحاولة 3 مرات كحد أقصى فقط (مهلة اتصال 5 ثوانٍ ومهلة إجمالية 20 ثانية لكل محاولة، بتأخير ثانية ثم ثانيتين)، ولا يعيد المحاولة عند أخطاء HTTP أو عند عدم تطابق SHA أو عند بيان غير صالح، ولا يعطّل التحقق من TLS أبدًا. الحدود والمخاطر المتبقية موثقة في [دليل CI](docs/CI.md).

لا يحتاج نشر Pages الحالي إلى أسرار نشر؛ صلاحيات النشر وإثبات الهوية تُدار عبر GitHub Actions وOIDC. راجع [دليل المعاينة والنشر والرجوع](docs/DEPLOYMENT.md) و[دليل CI](docs/CI.md) للتفاصيل.

تعطّل [إعدادات Vercel Git](vercel.json) النشر التلقائي الناتج عن commits على جميع الفروع عبر `git.deploymentEnabled: false` وفق [وثائق Vercel الرسمية](https://vercel.com/docs/project-configuration/git-configuration). هذه قاعدة لأحداث Git فقط، ولا تمنع CLI أو API أو Deploy Hooks أو تكاملًا خارجيًا؛ يجب على المالك مراجعة هذه المسارات من إعدادات Vercel. سير عمل `Vercel staging test` يدوي ومقيّد إلى `main`، وينشر Preview إلى مشروع staging فقط.

تفاصيل البوابات، المراجعة البشرية، النشر اليدوي والرجوع في [دليل المعاينة والنشر والرجوع](docs/DEPLOYMENT.md).

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
- [Security and code-quality review — 2026-11-16](docs/security/DEVOBS_SECURITY_REVIEW_2026-11-16.md)
- [Stable baseline: v1.0.0](https://github.com/hamedonassar95/Devobs/releases/tag/v1.0.0)

إعداد AI DevKit للمساهمين ومراحل العمل موثق في [دليل AI DevKit](docs/AI_DEVKIT.md). هذا الإعداد منفصل عن تشغيل CI/CD؛ مركز وحدات الأتمتة القابلة لإعادة الاستخدام موجود في [مركز الأتمتة](docs/AUTOMATION_HUB.md).

- [Manual P01 evidence completeness gate](docs/P01_ACTIVATION_READINESS.md#p01-offline-evidence-gate-review-only): fails closed on missing or stale launch evidence, but cannot approve P01, launch SaaS, or access provider accounts.
- [Keycloak OIDC profile and local-only discovery/JWKS preflight](docs/P01_KEYCLOAK_OIDC_PROFILE.md): a disposable Keycloak 26.8.2 Compose fixture pinned by official Quay digest, loopback-only and without a bootstrap admin. Local HTTP results do not satisfy Devobs's HTTPS issuer policy or establish token compatibility/readiness.
- [P01 Keycloak Docker smoke evidence](docs/P01_KEYCLOAK_DOCKER_SMOKE_EVIDENCE.md): real localhost-only runtime evidence for the pinned Keycloak 26.8.2 image, with the realm imported and the discovery/JWKS preflight passing. Local HTTP still does not establish production issuer readiness.
- [P01 Keycloak HTTPS discovery and JWKS preflight](docs/P01_KEYCLOAK_HTTPS_PREFLIGHT.md): the offline checker targets the exact `https://localhost` issuer on standard port 443; the fixture binds `127.0.0.1:443` to Keycloak's internal HTTPS port 8443 and reuses the strict OIDC metadata verifier. The narrow exception recorded by merged PR #608 is effective only after this reconciliation PR is merged. Until this reconciliation PR is merged, the general secret-handling prohibition remains binding and no Keycloak runtime may start. After activation, every runtime test requires separate explicit owner approval for that run naming the full reviewed source SHA (40-character SHA), a unique Docker Compose project name, and exact test scope. It permits only automatic generation and internal use of disposable realm signing material for synthetic identities, using the pinned image and a local Unix socket Docker context; `ssh://`, `tcp://`, named-pipe, cloud, and remote endpoints are BLOCKED. No private-key inspection/export, credential or token logging, or raw secret-bearing logs are allowed. Live TLS and signed-token acceptance remain NOT_TESTED.

## Graphify integrations (offline, opt-in)

**Canonical:** `tools/graphify` pinned to `graphifyy` 0.9.113, with CLI entry
points `scripts/graphify/multi_repo.py` and
`scripts/graphify/repository_intelligence.py`. Use it for new work:

```sh
python3 scripts/graphify/multi_repo.py validate --manifest assets/graphify/multi_repo_manifest.json
python3 scripts/graphify/repository_intelligence.py verify-wheel --wheel <local-wheel>
python3 -m unittest discover -s tests/graphify -v
```

Privacy controls, provenance and measured local evidence are in
[the Graphify integration design](docs/architecture/graphify-integration.md) and
[repository intelligence](docs/architecture/repository-intelligence.md).

**Legacy:** `scripts/integrations/graphify_portfolio.py` is a backward-compatible
adapter for the earlier 0.9.112 review-only CLI. It contains no orchestration or
subprocess implementation: the behavior lives in `tools/graphify/portfolio.py`
and `tools/graphify/portfolio_execution.py`. It still prints a `DEPRECATED`
notice and identifies the canonical stack in JSON reports. Its historical
provenance and blocked rollout evidence are recorded in
[docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md](docs/integrations/GRAPHIFY_PORTFOLIO_ROLLOUT.md).
Migration rules are in
[the consolidation plan](docs/architecture/GRAPHIFY_CONSOLIDATION_PLAN.md).

```sh
python3 scripts/integrations/graphify_portfolio.py --json
python3 -m unittest discover -s tests -p 'test_graphify_portfolio.py' -v
```
- [Disposable Keycloak public OAuth client](docs/P01_KEYCLOAK_OIDC_PROFILE.md#disposable-local-public-oauth-client): one offline-validated Authorization Code + PKCE S256 client configuration with exact loopback redirects and an opt-in `devobs.read` scope. Live runtime remains NOT_TESTED and requires the reconciliation PR to be merged plus separate per-run owner approval. The exception does not authorize credential or token creation, hosted identity, production changes, paid AI inference, or deployment; P01 remains NO-GO and AI-9 remains BLOCKED.

## Firebase security — Phase 3 emulator authorization tests

[Offline Firestore Emulator authorization tests](docs/security/FIREBASE_PHASE3_EMULATOR_TESTS.md)
exercise anonymous denial, synthetic tenant and owner isolation, and an explicitly
experimental owner policy. The suite runs only against a demo project on localhost;
the production Firestore rules remain deny-all.
