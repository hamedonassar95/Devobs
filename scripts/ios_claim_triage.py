#!/usr/bin/env python3
"""Offline, defensive triage of public iOS exploit and compatibility claims.

This utility does not contact devices, fetch sources, or verify an exploit.
It emits rule-based review signals and never echoes or stores the supplied claim.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any

MAX_CLAIM_CHARS = 20_000
CHIP_PATTERN = re.compile(r"\bA\s*(\d{1,2})\s*(?:\+|plus)?\b", re.IGNORECASE)
IOS_VERSION_PATTERN = re.compile(r"\biOS\s*\d+(?:\.(?:\d+|x)){0,2}\b", re.IGNORECASE)
CHECKM8_PATTERN = re.compile(r"check\s*m8", re.IGNORECASE)
USBLITER8_PATTERN = re.compile(r"usb\s*liter\s*8", re.IGNORECASE)
ACTIVATION_LOCK_PATTERN = re.compile(
    r"activation\s*lock|icloud\s*lock|activation\s*bypass|bypass\s+activation|direct\s+activation|"
    r"قفل\s*التنشيط|قفل\s*icloud|تجاوز\s+التنشيط|تخطي\s+التنشيط|التنشيط\s+المباشر",
    re.IGNORECASE,
)
IDENTIFIER_PATTERN = re.compile(
    r"\becid\b|\bserial(?:\s+number)?\b|الرقم\s+التسلسلي|معرّف\s+الشريحة|معرف\s+الشريحة",
    re.IGNORECASE,
)

CHECKM8_SOURCE = {
    "title": "US-CERT VU#941987 — ثغرة SecureROM في أجهزة Apple",
    "url": "https://www.kb.cert.org/vuls/id/941987/",
}
APPLE_SECURITY_SOURCE = {
    "title": "تحديثات الأمان من Apple",
    "url": "https://support.apple.com/en-us/100100",
}
APPLE_ACTIVATION_SOURCE = {
    "title": "مساعدة Apple بشأن قفل التنشيط",
    "url": "https://support.apple.com/en-us/108934",
}


def _chip_number(value: str) -> int:
    match = re.fullmatch(r"\s*A\s*(\d{1,2})\s*(?:\+|plus)?\s*", value, re.IGNORECASE)
    if not match:
        raise argparse.ArgumentTypeError("اكتب جيل المعالج بصيغة مثل A11 أو A12.")
    return int(match.group(1))


def _ios_build(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"(?:\d{1,2}(?:\.\d{1,2}){0,2}|\d{2}[A-Za-z]\d{3,5})", normalized):
        raise argparse.ArgumentTypeError("اكتب إصدارًا مثل 17.0.1 أو رقم بناء مثل 22A3354.")
    return normalized


def triage_claim(claim: str, *, chip: int | None = None, ios_build: str | None = None) -> dict[str, Any]:
    """Return review signals without returning or persisting the raw claim."""
    findings: list[dict[str, Any]] = []
    assessment = "unverified"

    if CHECKM8_PATTERN.search(claim):
        if assessment == "unverified":
            assessment = "needs_review"
        findings.append({
            "rule_id": "CHECKM8_SCOPE",
            "signal": "source_required",
            "detail": (
                "المصدر العام لـ checkm8 يصف دعم أجهزة بمعالجات A5 إلى A11. وجود اسم الثغرة "
                "لا يثبت وحده توافق أداة بعينها أو إزالة قفل التنشيط."
            ),
            "sources": [CHECKM8_SOURCE],
        })
        # Keep chip matching within the statement that names checkm8. This
        # avoids mixing separate tools or columns in a comparison table.
        checkm8_contexts = [
            fragment
            for fragment in re.split(r"[\r\n.!?؟؛;]+", claim)
            if CHECKM8_PATTERN.search(fragment)
        ]
        checkm8_chips = {
            int(value)
            for fragment in checkm8_contexts
            for value in CHIP_PATTERN.findall(fragment)
        }
        if chip is not None:
            checkm8_chips.add(chip)
        if any(generation > 11 for generation in checkm8_chips):
            assessment = "potential_mismatch"
            findings.append({
                "rule_id": "CHECKM8_A12_PLUS_MISMATCH",
                "signal": "human_review_required",
                "detail": (
                    "الادعاء يجمع checkm8 مع جيل أعلى من A11. اعتبر التوافق متناقضًا مبدئيًا "
                    "إلى أن يقدم مصدر تقني مستقل دليلًا على آلية أخرى؛ قد يسيء فحص الكلمات فهم النفي."
                ),
                "sources": [CHECKM8_SOURCE],
            })
        if any(ACTIVATION_LOCK_PATTERN.search(context) for context in checkm8_contexts):
            findings.append({
                "rule_id": "BOOTROM_IS_NOT_ACTIVATION_PROOF",
                "signal": "claim_not_established",
                "detail": (
                    "استغلال BootROM لا يثبت بحد ذاته إزالة قفل التنشيط المرتبط بخوادم Apple. "
                    "تحقق من الادعاء عبر توثيق مستقل وقنوات استرداد الملكية الرسمية."
                ),
                "sources": [APPLE_ACTIVATION_SOURCE, CHECKM8_SOURCE],
            })

    if USBLITER8_PATTERN.search(claim):
        if assessment == "unverified":
            assessment = "needs_review"
        findings.append({
            "rule_id": "USBLITER8_SOURCE_REQUIRED",
            "signal": "unverified_name",
            "detail": (
                "اسم usbliter8 وحده لا يثبت وجود ثغرة أو نطاق توافق. اطلب بحثًا تقنيًا مستقلًا "
                "يحدد الشرائح وإصدارات البناء والأثر والإصلاح؛ لا تستنتج التوافق من إعلان الأداة."
            ),
            "sources": [],
        })

    if IDENTIFIER_PATTERN.search(claim):
        if assessment == "unverified":
            assessment = "needs_review"
        findings.append({
            "rule_id": "DEVICE_IDENTIFIER_PRIVACY",
            "signal": "privacy_caution",
            "detail": (
                "Serial وECID معرّفات للجهاز وليسا ثغرات. لا تضع قيمهما الخام في البلاغ أو السجلات؛ "
                "يكفي عادةً طراز الجهاز والمعالج وإصدار البناء."
            ),
            "sources": [],
        })

    if IOS_VERSION_PATTERN.search(claim):
        if assessment == "unverified":
            assessment = "needs_review"
        if ios_build:
            findings.append({
                "rule_id": "IOS_BUILD_NOT_VALIDATED",
                "signal": "source_required",
                "detail": (
                    "أُرفق رقم بناء للمراجعة، لكن الأداة غير متصلة بقاعدة Apple ولا تتحقق من الإصلاحات. "
                    "طابق الطراز والبناء مع نشرة أمان رسمية."
                ),
                "sources": [APPLE_SECURITY_SOURCE],
            })
        else:
            findings.append({
                "rule_id": "IOS_BUILD_REQUIRED",
                "signal": "missing_context",
                "detail": (
                    "ذكر إصدار iOS وحده لا يكفي للتحقق. اربط الادعاء بطراز الجهاز ورقم البناء "
                    "ومرجع أمني رسمي."
                ),
                "sources": [APPLE_SECURITY_SOURCE],
            })

    if not findings:
        findings.append({
            "rule_id": "NO_VERIFIABLE_SIGNAL",
            "signal": "unverified",
            "detail": "لم تطابق العبارة قاعدة معروفة في هذه الأداة؛ يلزم مصدر تقني مستقل ومراجعة بشرية.",
            "sources": [],
        })

    return {
        "schema_version": 1,
        "assessment": assessment,
        "method": "offline_heuristics_not_exploit_validation",
        "device_context": {
            "chip": f"A{chip}" if chip is not None else None,
            "ios_build": ios_build,
        },
        "claim_text_included": False,
        "raw_claim_stored": False,
        "findings": findings,
        "ai_handoff": {
            "allowed": ["summarize findings", "list missing evidence", "compare against cited sources"],
            "prohibited": [
                "execute commands or interact with a device",
                "provide activation-lock bypass steps",
                "treat vendor claims as verified without evidence",
                "request or expose raw Serial or ECID values",
            ],
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="فرز دفاعي وغير متصل لادعاءات توافق ثغرات iOS؛ لا يتحقق من استغلال جهاز."
    )
    parser.add_argument("--chip", help="جيل المعالج المستهدف، مثل A11 أو A12.")
    parser.add_argument("--ios-build", help="إصدار أو رقم بناء، مثل 17.0.1 أو 22A3354.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        chip = _chip_number(args.chip) if args.chip else None
        ios_build = _ios_build(args.ios_build) if args.ios_build else None
    except argparse.ArgumentTypeError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False))
        return 2
    claim = sys.stdin.read(MAX_CLAIM_CHARS + 1)
    if len(claim) > MAX_CLAIM_CHARS:
        print(json.dumps({"error": "النص أطول من الحد المسموح (20,000 حرف)."}, ensure_ascii=False))
        return 2
    report = triage_claim(claim, chip=chip, ios_build=ios_build)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
