"""Offline-only, fail-closed OpenArt MCP creative request contract.

This module never connects to MCP, authenticates, spends credits, uploads data,
approves requests, publishes content, or invokes generative models.
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

POLICY = "devobs-openart-request-v1"
PROJECT = "Devobs AI Intelligence"
ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{3,63}$")
DELIVERABLE_KEYS = {"id", "media_type", "aspect_ratio", "language", "prompt"}
ROOT_KEYS = {"schema_version", "job_id", "project", "state", "visibility", "deliverables"}
RATIOS = {"1:1", "16:9", "9:16"}
LANGUAGES = {"ar", "en"}


class InvalidMediaRequest(ValueError):
    pass


def reject(message):
    raise InvalidMediaRequest(message)


def nonempty(value, field, maximum):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        reject(f"{field}: invalid text")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        reject(f"{field}: control character")
    return value


def validate_media_request(value):
    if type(value) is not dict or set(value) != ROOT_KEYS:
        reject("request: unsupported or missing fields")
    if type(value["schema_version"]) is not int or value["schema_version"] != 1:
        reject("schema_version: expected 1")
    job_id = nonempty(value["job_id"], "job_id", 64)
    if not ID_PATTERN.fullmatch(job_id):
        reject("job_id: invalid identifier")
    if value["project"] != PROJECT:
        reject("project: unexpected project")
    if value["state"] != "DRAFT":
        reject("state: only DRAFT requests are accepted")
    if value["visibility"] != "private":
        reject("visibility: public publishing is not authorized")
    items = value["deliverables"]
    if type(items) is not list or not 1 <= len(items) <= 3:
        reject("deliverables: expected 1-3 items")
    seen = set()
    for i, item in enumerate(items):
        label = f"deliverables[{i}]"
        if type(item) is not dict:
            reject(f"{label}: expected object")
        keys = set(item)
        if keys not in (DELIVERABLE_KEYS, DELIVERABLE_KEYS | {"requested_duration_seconds"}):
            reject(f"{label}: unsupported or missing fields")
        ident = nonempty(item["id"], f"{label}.id", 64)
        if not ID_PATTERN.fullmatch(ident) or ident in seen:
            reject(f"{label}.id: invalid or duplicate")
        seen.add(ident)
        if item["media_type"] not in ("image", "video"):
            reject(f"{label}.media_type: expected image or video")
        if (type(item["aspect_ratio"]) is not str or item["aspect_ratio"] not in RATIOS
                or type(item["language"]) is not str or item["language"] not in LANGUAGES):
            reject(f"{label}: unsupported ratio or language")
        prompt = nonempty(item["prompt"], f"{label}.prompt", 2000)
        if len(prompt.strip()) < 40:
            reject(f"{label}.prompt: minimum 40 characters")
        duration = item.get("requested_duration_seconds")
        if "requested_duration_seconds" in item:
            if item["media_type"] != "video" or type(duration) is not int or not 1 <= duration <= 30:
                reject(f"{label}.requested_duration_seconds: video-only 1-30")
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "policy_version": POLICY,
        "job_id": job_id,
        "request_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "deliverable_count": len(items),
        "classification": "offline_draft_only",
        "approved": False,
        "credits_authorized": False,
        "generation_submitted": False,
        "required_next_step": "Operator quotes live OpenArt MCP cost and obtains explicit spending approval",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=pathlib.Path)
    args = parser.parse_args(argv)
    try:
        data = json.loads(args.input.read_text(encoding="utf-8"))
        result = validate_media_request(data)
    except (OSError, UnicodeError, json.JSONDecodeError, InvalidMediaRequest) as exc:
        print(f"OPENART_REQUEST_INVALID: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
