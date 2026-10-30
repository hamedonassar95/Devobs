#!/usr/bin/env python3
"""Offline arithmetic diagnostic for AI-9 frozen synthetic window Precision.

Only counts from an already audited synthetic result are used. This does not
choose a detector, modify thresholds, predict retained recall or authorize GO.
"""
import argparse
import json
from pathlib import Path

# Support both package imports (unittest) and direct script invocation.
if __package__:
    from . import check_ai9_multimetric_evidence as evidence
else:
    import check_ai9_multimetric_evidence as evidence

GATES = evidence.GATES
InvalidAI9Evidence = evidence.InvalidAI9Evidence
MAX_BYTES = evidence.MAX_BYTES
audit = evidence.audit
natural = evidence.natural
record = evidence.record
unique_pairs = evidence.unique_pairs

VARIANT = "post_confirmation_layer"


def fixed_recall_fp_budget(tp, fp):
    """Exact integer arithmetic for the frozen Precision >= 4/5 requirement."""
    natural(tp, "true_positives")
    natural(fp, "false_positives")
    if GATES["precision"] != 0.8:
        raise InvalidAI9Evidence("unexpected frozen precision gate")
    maximum_fp = tp // 4
    required_removed = max(0, fp - maximum_fp)
    return {
        "true_positives": tp,
        "observed_false_positives": fp,
        "maximum_false_positives_at_fixed_tp": maximum_fp,
        "minimum_false_positives_to_remove_at_fixed_tp": required_removed,
    }


def analyze(document):
    integrity = audit(document)
    seeds = []
    for item in document["per_seed"]:
        counts = record(record(item[VARIANT], VARIANT)["window_metrics"], "window_metrics")
        gap = fixed_recall_fp_budget(counts["tp"], counts["fp"])
        seeds.append({"seed": item["seed"], **gap})

    tp_total = sum(row["true_positives"] for row in seeds)
    fp_total = sum(row["observed_false_positives"] for row in seeds)
    max_fp_total = sum(row["maximum_false_positives_at_fixed_tp"] for row in seeds)
    remove_total = sum(row["minimum_false_positives_to_remove_at_fixed_tp"] for row in seeds)
    if fp_total == 0:
        remove_fraction = 0.0
    else:
        remove_fraction = remove_total / fp_total
    return {
        "classification": "synthetic_development_only",
        "scope": "fixed_true_positives_arithmetic_not_a_detector_or_prediction",
        "variant": VARIANT,
        "frozen_precision_threshold": GATES["precision"],
        "verified_seed_count": integrity["verified_seed_count"],
        "total_true_positives": tp_total,
        "total_observed_false_positives": fp_total,
        "maximum_false_positives_at_fixed_tp_by_seed": max_fp_total,
        "minimum_false_positives_to_remove_at_fixed_tp": remove_total,
        "required_reduction_fraction_at_fixed_tp": remove_fraction,
        "per_seed": seeds,
        "synthetic_gate_status": integrity["synthetic_gate_status"],
        "production_decision": "NOT_AUTHORIZED",
        "p01_decision": "NO-GO / BLOCKED",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json")
    args = parser.parse_args(argv)
    try:
        with Path(args.file).open("rb") as handle:
            raw = handle.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise InvalidAI9Evidence("report exceeds size limit")
        result = analyze(json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs))
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidAI9Evidence,
            RecursionError, KeyError, TypeError) as exc:
        print(json.dumps({"evidence": "INVALID", "production_decision": "NOT_AUTHORIZED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["synthetic_gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
