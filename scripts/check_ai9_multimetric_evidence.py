#!/usr/bin/env python3
"""Read-only integrity check of frozen synthetic AI-9 evidence; never production GO."""
import argparse
import json
import math
from pathlib import Path
import re

SEEDS = list(range(20270201, 20270221))
VARIANTS = (
    ("baseline", "baseline_summary"),
    ("current_candidate", "current_candidate_summary"),
    ("post_confirmation_layer", "post_confirmation_layer_summary"),
)
GATES = {"precision": 0.8, "recall": 0.8, "fpr": 0.05}
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES = 1024 * 1024


class InvalidAI9Evidence(ValueError):
    pass


def fail(message):
    raise InvalidAI9Evidence(message)


def record(value, description):
    if type(value) is not dict:
        fail(f"{description}: expected object")
    return value


def natural(value, description):
    if type(value) is not int or value < 0:
        fail(f"{description}: invalid count")
    return value


def close(left, right):
    return type(left) in (int, float) and math.isfinite(left) and math.isclose(
        left, right, rel_tol=0, abs_tol=1e-12,
    )


def audit(document):
    document = record(document, "report")
    if (document.get("classification") != "synthetic_development_only"
            or document.get("registration_id") != "ai9-multimetric-confirmation-v1"
            or document.get("seed_count") != 20
            or document.get("seeds") != SEEDS
            or document.get("frozen_gates") != GATES
            or document.get("aggregate_gate_decision") != "NOT_DEFINED_BY_PREREGISTRATION"):
        fail("report: frozen protocol mismatch")
    runs = document.get("per_seed")
    if type(runs) is not list or len(runs) != len(SEEDS):
        fail("report: missing or extra seed records")
    counts = {name: {key: 0 for key in (*GATES, "all_three")} for name, _ in VARIANTS}
    means = {name: {key: [] for key in GATES} for name, _ in VARIANTS}
    for expected_seed, item in zip(SEEDS, runs):
        item = record(item, "seed record")
        if (type(item.get("seed")) is not int or item["seed"] != expected_seed
                or type(item.get("input_canonical_sha256")) is not str
                or not SHA256.fullmatch(item["input_canonical_sha256"])):
            fail("seed record: id/order/digest mismatch")
        positive = natural(item.get("positive_windows"), "positive_windows")
        negative = natural(item.get("negative_windows"), "negative_windows")
        windows = natural(item.get("scored_windows"), "scored_windows")
        if (positive, negative, windows) != (90, 45150, 45240):
            fail("seed record: population mismatch")
        for name, _ in VARIANTS:
            metric = record(record(item.get(name), name).get("window_metrics"), "window metrics")
            tp, fp, fn, tn = [natural(metric.get(k), k) for k in ("tp", "fp", "fn", "tn")]
            if (tp + fn != positive or fp + tn != negative
                    or metric.get("windows") != windows):
                fail(f"{name}: inconsistent confusion matrix")
            values = {
                "precision": tp / (tp + fp) if tp + fp else None,
                "recall": tp / (tp + fn),
                "fpr": fp / (fp + tn),
            }
            statuses = record(metric.get("gate_status"), "gate_status")
            if set(statuses) != set(GATES):
                fail(f"{name}: invalid gate keys")
            for key, value in values.items():
                if value is None or not close(metric.get(key), value):
                    fail(f"{name}: invalid {key} metric")
                passed = (value <= GATES[key]) if key == "fpr" else (value >= GATES[key])
                if statuses[key] != ("PASS" if passed else "FAIL"):
                    fail(f"{name}: {key} gate inconsistent")
                counts[name][key] += int(passed)
                means[name][key].append(value * 100)
            counts[name]["all_three"] += int(all(value == "PASS" for value in statuses.values()))
    for name, summary_name in VARIANTS:
        summary = record(document.get(summary_name), summary_name)
        gate_counts = record(summary.get("gate_pass_counts"), "gate_pass_counts")
        if gate_counts != {**counts[name], "seed_count": 20}:
            fail(f"{summary_name}: summary gate counts mismatch")
        for key in GATES:
            reported = record(summary.get(key), f"{summary_name}.{key}").get("mean_percent")
            if not close(reported, sum(means[name][key]) / 20):
                fail(f"{summary_name}: {key} mean mismatch")
    return {
        "classification": "synthetic_development_only",
        "verified_seed_count": 20,
        "synthetic_gate_status": "PASS" if counts["post_confirmation_layer"]["all_three"] == 20 else "FAIL",
        "synthetic_gate_pass_counts": {**counts["post_confirmation_layer"], "seed_count": 20},
        "production_decision": "NOT_AUTHORIZED",
        "p01_decision": "NO-GO / BLOCKED",
    }


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("duplicate JSON key")
        result[key] = value
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", default="docs/AI9_MULTIMETRIC_CONFIRMATION_V1_RESULTS.json")
    args = parser.parse_args(argv)
    try:
        with Path(args.file).open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            fail("report exceeds size limit")
        result = audit(json.loads(data.decode("utf-8"), object_pairs_hook=unique_pairs))
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidAI9Evidence, RecursionError) as exc:
        print(json.dumps({"evidence": "INVALID", "production_decision": "NOT_AUTHORIZED", "reason": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["synthetic_gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
