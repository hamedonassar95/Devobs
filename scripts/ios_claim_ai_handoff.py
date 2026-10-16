#!/usr/bin/env python3
"""Build a privacy-minimized AI review prompt from an iOS triage JSON report.

This tool is offline. It accepts only the structured output of
ios_claim_triage.py, drops free-form text, and never contacts an AI service.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any

MAX_REPORT_CHARS = 64_000
ASSESSMENTS = {"unverified", "needs_review", "potential_mismatch"}
SIGNALS = {
    "source_required", "human_review_required", "claim_not_established",
    "unverified_name", "privacy_caution", "missing_context", "unverified",
}
RULES = {
    "CHECKM8_SCOPE", "CHECKM8_A12_PLUS_MISMATCH",
    "BOOTROM_IS_NOT_ACTIVATION_PROOF", "USBLITER8_SOURCE_REQUIRED",
    "DEVICE_IDENTIFIER_PRIVACY", "IOS_BUILD_NOT_VALIDATED",
    "IOS_BUILD_REQUIRED", "NO_VERIFIABLE_SIGNAL",
}
SOURCE_URLS = {
    "https://www.kb.cert.org/vuls/id/941987/",
    "https://support.apple.com/en-us/100100",
    "https://support.apple.com/en-us/108934",
}
CHIP_RE = re.compile(r"A(?:[1-9]|1[0-9])\Z")
BUILD_RE = re.compile(r"(?:\d{1,2}(?:\.\d{1,2}){0,2}|\d{2}[A-Za-z]\d{3,5})\Z")


def safe_projection(report: dict[str, Any]) -> dict[str, Any]:
    """Validate provenance and return a small allowlisted report projection."""
    if report.get("schema_version") != 1 or report.get("method") != "offline_heuristics_not_exploit_validation":
        raise ValueError("هذا ليس تقرير فرز معروفًا من ios_claim_triage.py.")
    if report.get("claim_text_included") is not False or report.get("raw_claim_stored") is not False:
        raise ValueError("ارفض التقرير: يجب ألا يتضمن نص الادعاء أو يخزنه.")
    assessment = report.get("assessment")
    if assessment not in ASSESSMENTS:
        raise ValueError("قيمة assessment غير معروفة.")

    device = report.get("device_context")
    if not isinstance(device, dict):
        raise ValueError("device_context مفقود أو غير صالح.")
    chip, build = device.get("chip"), device.get("ios_build")
    if chip is not None and (not isinstance(chip, str) or not CHIP_RE.fullmatch(chip)):
        raise ValueError("صيغة المعالج غير صالحة.")
    if build is not None and (not isinstance(build, str) or not BUILD_RE.fullmatch(build)):
        raise ValueError("صيغة إصدار النظام أو رقم البناء غير صالحة.")

    findings = report.get("findings")
    if not isinstance(findings, list) or not 1 <= len(findings) <= 20:
        raise ValueError("قائمة findings غير صالحة.")
    safe_findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("عنصر finding غير صالح.")
        rule_id, signal = finding.get("rule_id"), finding.get("signal")
        if (not isinstance(rule_id, str) or rule_id not in RULES or
                not isinstance(signal, str) or signal not in SIGNALS):
            raise ValueError("يحتوي التقرير على قاعدة أو إشارة غير معروفة.")
        sources = finding.get("sources", [])
        if not isinstance(sources, list) or len(sources) > 5:
            raise ValueError("قائمة المصادر غير صالحة.")
        urls = []
        for source in sources:
            url = source.get("url") if isinstance(source, dict) else None
            if not isinstance(url, str) or url not in SOURCE_URLS:
                raise ValueError("مصدر غير معتمد في تقرير الفرز.")
            urls.append(url)
        safe_findings.append({"rule_id": rule_id, "signal": signal, "sources": urls})

    return {
        "assessment": assessment,
        "device_context": {"chip": chip, "ios_build": build},
        "findings": safe_findings,
    }


def build_prompt(report: dict[str, Any]) -> str:
    projection = safe_projection(report)
    evidence = json.dumps(projection, ensure_ascii=False, indent=2)
    return f"""أنت مساعد لمراجعة ادعاءات التوافق الأمني لأجهزة Apple. حلّل بيانات الفرز المنظمة أدناه فقط.

قواعد المراجعة:
- هذه إشارات قواعد محلية وليست إثباتًا لوجود ثغرة أو توافق أداة.
- لا تستنتج توافقًا أو نجاحًا من اسم أداة أو ثغرة وحده.
- لا تخترع مصادر أو تفاصيل تقنية غير موجودة في البيانات. اذكر ما يلزم التحقق منه لدى Apple أو مصدر أمني مستقل.
- لا تقدم خطوات لتجاوز قفل التنشيط، أو استغلال جهاز، أو تنفيذ أوامر عليه.
- لا تطلب Serial أو ECID، ولا تحاول استنتاجهما.
- أخرج ملخصًا عربيًا موجزًا بهذه العناوين: «النتيجة الأولية»، «ما تدعمه البيانات»، «ما يزال غير مثبت»، «خطوات تحقق آمنة»، «المصادر».
- اذكر أن القرار النهائي يتطلب مراجعة بشرية ومصادر مستقلة.

بيانات الفرز المسموح استخدامها:
```json
{evidence}
```"""


def main() -> int:
    raw = sys.stdin.read(MAX_REPORT_CHARS + 1)
    if len(raw) > MAX_REPORT_CHARS:
        print("حجم التقرير يتجاوز الحد المسموح.", file=sys.stderr)
        return 2
    try:
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError("يجب أن يكون جذر JSON كائنًا.")
        print(build_prompt(report))
    except (json.JSONDecodeError, ValueError) as error:
        print(f"تعذر إنشاء التسليم الآمن: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
