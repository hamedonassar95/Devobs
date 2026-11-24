# Firebase for Devobs — Phase 1: safety baseline and learning roadmap

**Checkpoint:** 2026-11-23. **State:** source-only verification; **hosted access unverified**. No cloud resources were modified. This is not P01 production acceptance.

## 1. Repository evidence

- Canonical repository: https://github.com/hamedonassar95/Devobs. Optional UI: apps/ai-intelligence-console/.
- VERIFIED: Firestore adapter loads only when VITE_FIREBASE_ENABLED=true. Firebase is disabled by default; do not activate it.
- VERIFIED: the canonical prototype source policy at apps/ai-intelligence-console/firestore.rules denies all client reads and writes.
- VERIFIED: the separate original source repository https://github.com/hamedonassar95/DevObs-ai-Intelligence-/blob/main/firestore.rules permits public reads of servers, incidents and deployments with an OR-true condition, and grants signed-in users broad writes without checking ownership. This does not prove which rules are deployed in Firebase.
- Owner-supplied Firebase Console screenshots show similar permissive rules for a database in project my-apps-hamedo. Whether those rules were published, what data they protect, and which app clients depend on them remain UNVERIFIED.
- An alert concerns a Firebase web API key in a public repository. Firebase client API keys are usually public identifiers, not sufficient access authorization. Review restrictions and Firestore rules without exposing the key. Do not close alerts without evidence.

## 2. Why the old rules are dangerous

An unconditional read clause allows anonymous clients to read matching documents. A catch-all deny rule does not override a separate allow, since overlapping allows are combined. Signing in does not prove tenant ownership or authorization to edit all records. Neither API-key restrictions nor App Check replace database authorization rules.

## 3. Implemented now: offline, fail-closed baseline

Commands from repository root:

    python3 scripts/check_firebase_rules_baseline.py
    python3 -m unittest discover -s tests -p 'test_firebase_rules_baseline.py' -v

The checker recognizes only the exact canonical deny-all source. PASS / exit 0 means local baseline unchanged; FAIL / exit 1 flags unconditional allow conditions; BLOCKED / exit 2 means missing, malformed or unfamiliar rules require independent review. It is NOT a rules-language parser, emulator, hosted security scan, or tenant-isolation proof. It reads no credentials, makes no network calls and does not deploy.

## 4. One step at a time: training and integration roadmap

| Phase | Learn | Next action | Approval gate |
| --- | --- | --- | --- |
| **1 — now** | Firebase vs DevOps; project, key, and Firestore rules | Verify prototype local deny-all with offline tests | Review this PR and exact-head CI |
| **2 — next** | Authentication and tenant ownership | Document which clients, users, databases and paths need access; confirm effective hosted policy without reading records | Owner reviews access/data classification |
| **3** | Emulators and negative authorization tests | Test anonymous, valid owner and another tenant against proposed narrow synthetic rules | Offline emulator evidence and separate PR; never deploy automatically |
| **4** | Safe app integration | Assess optional Auth/App Check and limited read-only use of a synthetic test project | Privacy, architecture, cost and production permission reviews |
| **5** | Useful features | Evaluate Crashlytics for Android, Analytics, Performance Monitoring, App Distribution, Hosting, FCM and AI Logic | Feature-specific need, plan pricing, consent and tests |

Do not duplicate existing Devobs CI, AI, observability or deployment capabilities. Do not activate paid inference, cloud resources, migrations, Firebase deployment, or Google Cloud key edits.

## 5. Owner action

Potentially non-public Firestore data may be readable anonymously if the screenshot's rules are actually active. Treat this as an urgent owner review, not a confirmed hosted breach. Preserve access where business-critical, inventory legitimate consumers, and require an independently reviewed, reversible containment plan for the exact database before changing live rules. Never delete records or publish a blanket denial without impact approval.

## Official references

- https://firebase.google.com/docs/firestore/security/rules-structure
- https://firebase.google.com/docs/firestore/security/rules-conditions
- https://firebase.google.com/docs/firestore/security/test-rules-emulator
- https://firebase.google.com/docs/projects/api-keys
- https://firebase.google.com/docs/projects/billing/firebase-pricing-plans

**Release gates unchanged:** P01 NO-GO/BLOCKED; AI-9 BLOCKED; Codex runtime OPEN. PENDING HUMAN APPROVAL.
