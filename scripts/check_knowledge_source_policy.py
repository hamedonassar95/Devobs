#!/usr/bin/env python3
"""Validate a local KI-0 policy envelope; this does not authorize data access."""

from __future__ import annotations

import argparse
from datetime import datetime
from functools import lru_cache
import json
from pathlib import Path
import re
import stat
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "knowledge-source-policy.schema.json"
MAX_INPUT_BYTES = 16_384
MAX_SCHEMA_BYTES = 16_384
SCHEMA_VERSION = 1

FIELDS = frozenset({
    "schema_version", "source_id", "source_type", "source_version",
    "source_uri", "content_sha256", "tenant_id", "repository_id", "owner_id",
    "classification", "license_status", "ingestion_authorized",
    "retention_policy", "deletion_policy", "provenance", "approval_status",
})
SOURCE_TYPES = frozenset({
    "synthetic_fixture", "public_document", "public_repository_file",
    "internal_document", "confidential_document", "restricted_document",
})
CLASSIFICATIONS = frozenset({"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"})
LICENSE_STATUSES = frozenset({
    "NOT_APPLICABLE", "PUBLIC_DOMAIN", "PERMISSIVE", "EXPLICIT_PERMISSION",
    "INTERNAL_USE_AUTHORIZED", "CONFIDENTIAL_SCOPE_APPROVED",
})
APPROVAL_STATUSES = frozenset({"APPROVED", "PENDING", "DENIED", "UNKNOWN"})
DELETION_POLICIES = frozenset({
    "DELETE_ON_COMPLETION", "DELETE_ON_REVOCATION",
    "DELETE_ON_REQUEST_AND_EXPIRY",
})
RETENTION_MODES = frozenset({"EPHEMERAL_TEST", "SOURCE_RIGHTS", "OWNER_APPROVED"})
SOURCE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
REPOSITORY_ID = re.compile(r"[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}\Z")
SOURCE_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:+-]{0,127}\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class PolicyValidationError(ValueError):
    """A fixed, non-sensitive validation code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _fail(code: str) -> None:
    raise PolicyValidationError(code)


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PolicyValidationError("duplicate_json_key")
        result[key] = value
    return result


def _reject_json_constant(_value: str) -> None:
    _fail("invalid_json_constant")


def _load_json_bytes(raw: bytes, size_limit: int) -> object:
    if len(raw) > size_limit:
        _fail("input_too_large")
    try:
        text = raw.decode("utf-8", errors="strict")
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except PolicyValidationError:
        raise
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail("malformed_json")


@lru_cache(maxsize=1)
def _verify_schema_contract() -> None:
    try:
        metadata = SCHEMA_PATH.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            _fail("schema_unavailable")
        if metadata.st_size > MAX_SCHEMA_BYTES:
            _fail("schema_invalid")
        with SCHEMA_PATH.open("rb") as stream:
            schema = _load_json_bytes(stream.read(MAX_SCHEMA_BYTES + 1), MAX_SCHEMA_BYTES)
    except PolicyValidationError:
        raise
    except OSError:
        _fail("schema_unavailable")

    if (type(schema) is not dict
            or set(schema) != {"$schema", "title", "type", "additionalProperties", "required", "properties"}
            or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
            or schema.get("title") != "Devobs Knowledge Source Policy v1"
            or schema.get("type") != "object"
            or schema.get("additionalProperties") is not False
            or type(schema.get("required")) is not list
            or any(type(field) is not str for field in schema["required"])
            or len(schema["required"]) != len(set(schema["required"]))
            or set(schema["required"]) != FIELDS
            or type(schema.get("properties")) is not dict
            or set(schema["properties"]) != FIELDS):
        _fail("schema_invalid")

    properties = schema["properties"]
    expected_enums = {
        "source_type": SOURCE_TYPES,
        "classification": CLASSIFICATIONS,
        "license_status": LICENSE_STATUSES,
        "approval_status": APPROVAL_STATUSES,
        "deletion_policy": DELETION_POLICIES,
    }
    for field, expected in expected_enums.items():
        definition = properties[field]
        if (type(definition) is not dict or set(definition) != {"type", "enum"}
                or type(definition.get("enum")) is not list
                or any(type(value) is not str for value in definition["enum"])
                or len(definition["enum"]) != len(set(definition["enum"]))
                or definition.get("type") != "string"
                or set(definition["enum"]) != expected):
            _fail("schema_invalid")
    version_definition = properties["schema_version"]
    if (type(version_definition) is not dict
            or type(version_definition.get("const")) is not int
            or version_definition["const"] != SCHEMA_VERSION):
        _fail("schema_invalid")
    expected_shapes = {
        "schema_version": {"const": SCHEMA_VERSION},
        "source_id": {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
        "source_version": {
            "type": "string", "minLength": 1, "maxLength": 128,
            "pattern": r"^[A-Za-z0-9][A-Za-z0-9._:+-]{0,127}$",
        },
        "source_uri": {"type": "string", "minLength": 1, "maxLength": 2048},
        "content_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "tenant_id": {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
        "repository_id": {
            "type": "string", "pattern": r"^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$",
        },
        "owner_id": {"type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$"},
        "ingestion_authorized": {"type": "boolean"},
    }
    if any(type(properties[field]) is not dict or properties[field] != shape
           for field, shape in expected_shapes.items()):
        _fail("schema_invalid")
    for field, numeric_fields in {
        "source_version": ("minLength", "maxLength"),
        "source_uri": ("minLength", "maxLength"),
    }.items():
        if any(type(properties[field][name]) is not int for name in numeric_fields):
            _fail("schema_invalid")
    retention = properties["retention_policy"]
    retention_properties = retention.get("properties") if type(retention) is dict else None
    mode = retention_properties.get("mode") if type(retention_properties) is dict else None
    mode_enum = mode.get("enum") if type(mode) is dict else None
    if (type(retention) is not dict or type(retention_properties) is not dict
            or set(retention) != {"type", "additionalProperties", "required", "properties"}
            or retention.get("type") != "object"
            or retention.get("required") != ["mode", "max_age_seconds"]
            or type(mode_enum) is not list
            or any(type(value) is not str for value in mode_enum)
            or len(mode_enum) != len(RETENTION_MODES)
            or type(mode) is not dict or set(mode) != {"type", "enum"}
            or mode.get("type") != "string"
            or set(mode_enum) != RETENTION_MODES
            or set(retention_properties) != {"mode", "max_age_seconds"}
            or retention_properties.get("max_age_seconds") != {
                "type": "integer", "minimum": 1, "maximum": 31_536_000,
            }
            or type(retention_properties.get("max_age_seconds", {}).get("minimum")) is not int
            or type(retention_properties.get("max_age_seconds", {}).get("maximum")) is not int
            or retention.get("additionalProperties") is not False):
        _fail("schema_invalid")
    provenance = properties["provenance"]
    provenance_properties = provenance.get("properties") if type(provenance) is dict else None
    if (type(provenance) is not dict
            or set(provenance) != {"type", "additionalProperties", "required", "properties"}
            or provenance.get("type") != "object"
            or provenance.get("additionalProperties") is not False
            or provenance.get("required") != ["recorded_at", "recorded_by", "approval_reference"]
            or type(provenance_properties) is not dict
            or set(provenance_properties) != {"recorded_at", "recorded_by", "approval_reference"}
            or provenance_properties.get("recorded_at") != {
                "type": "string", "format": "date-time", "maxLength": 35,
            }
            or provenance_properties.get("recorded_by") != {
                "type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
            }
            or provenance_properties.get("approval_reference") != {
                "type": "string", "pattern": r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$",
            }):
        _fail("schema_invalid")


def _safe_text(value: object, maximum: int) -> bool:
    return (type(value) is str and 1 <= len(value) <= maximum
            and value == value.strip()
            and not any(ord(character) < 32 or ord(character) == 127 for character in value))


def _validate_uri(policy: dict[str, object]) -> None:
    source_type = policy["source_type"]
    uri = policy["source_uri"]
    if not _safe_text(uri, 2048):
        _fail("invalid_source_uri")
    try:
        parsed = urlsplit(uri)
    except ValueError:
        _fail("invalid_source_uri")
    if parsed.query or parsed.fragment or parsed.username is not None or parsed.password is not None:
        _fail("invalid_source_uri")

    if source_type == "synthetic_fixture":
        if (parsed.scheme != "fixture" or parsed.netloc != policy["source_id"]
                or parsed.path or parsed.query or parsed.fragment):
            _fail("invalid_source_uri")
    elif source_type == "public_document":
        if parsed.scheme != "https" or not parsed.hostname or not parsed.path.startswith("/"):
            _fail("invalid_source_uri")
        try:
            _ = parsed.port
        except ValueError:
            _fail("invalid_source_uri")
    else:
        if (parsed.scheme != "repo" or parsed.netloc or not parsed.path.startswith("/")
                or any(segment in {"", ".", ".."} for segment in parsed.path.split("/")[1:])):
            _fail("invalid_source_uri")


_COMBINATIONS = {
    "synthetic_fixture": ("INTERNAL", {"NOT_APPLICABLE"}, "EPHEMERAL_TEST", "DELETE_ON_COMPLETION"),
    "public_document": ("PUBLIC", {"PUBLIC_DOMAIN", "PERMISSIVE", "EXPLICIT_PERMISSION"},
                        "SOURCE_RIGHTS", "DELETE_ON_REVOCATION"),
    "public_repository_file": ("PUBLIC", {"PUBLIC_DOMAIN", "PERMISSIVE", "EXPLICIT_PERMISSION"},
                               "SOURCE_RIGHTS", "DELETE_ON_REVOCATION"),
    "internal_document": ("INTERNAL", {"INTERNAL_USE_AUTHORIZED", "EXPLICIT_PERMISSION"},
                          "OWNER_APPROVED", "DELETE_ON_REQUEST_AND_EXPIRY"),
    "confidential_document": ("CONFIDENTIAL", {"CONFIDENTIAL_SCOPE_APPROVED", "EXPLICIT_PERMISSION"},
                              "OWNER_APPROVED", "DELETE_ON_REQUEST_AND_EXPIRY"),
    "restricted_document": ("RESTRICTED", {"EXPLICIT_PERMISSION"},
                            "OWNER_APPROVED", "DELETE_ON_REQUEST_AND_EXPIRY"),
}


def validate_policy(policy: object) -> dict[str, object]:
    """Validate only local policy structure and consistency, never authority."""
    _verify_schema_contract()
    if type(policy) is not dict or set(policy) != FIELDS:
        _fail("invalid_fields")
    if type(policy["schema_version"]) is not int or policy["schema_version"] != SCHEMA_VERSION:
        _fail("unsupported_schema")
    if type(policy["source_id"]) is not str or SOURCE_ID.fullmatch(policy["source_id"]) is None:
        _fail("invalid_source_id")
    if type(policy["source_type"]) is not str or policy["source_type"] not in SOURCE_TYPES:
        _fail("invalid_source_type")
    if (type(policy["source_version"]) is not str
            or SOURCE_VERSION.fullmatch(policy["source_version"]) is None):
        _fail("invalid_source_version")
    if type(policy["content_sha256"]) is not str or SHA256.fullmatch(policy["content_sha256"]) is None:
        _fail("invalid_content_sha256")
    if type(policy["tenant_id"]) is not str or SOURCE_ID.fullmatch(policy["tenant_id"]) is None:
        _fail("missing_or_invalid_tenant_scope")
    if (type(policy["repository_id"]) is not str
            or REPOSITORY_ID.fullmatch(policy["repository_id"]) is None
            or any(part in {".", ".."} for part in policy["repository_id"].split("/"))):
        _fail("missing_or_invalid_repository_scope")
    if type(policy["owner_id"]) is not str or SOURCE_ID.fullmatch(policy["owner_id"]) is None:
        _fail("invalid_owner_id")
    if (type(policy["classification"]) is not str
            or policy["classification"] not in CLASSIFICATIONS):
        _fail("invalid_classification")
    if policy["classification"] == "RESTRICTED":
        _fail("restricted_source_not_supported")
    if type(policy["license_status"]) is not str or policy["license_status"] not in LICENSE_STATUSES:
        _fail("invalid_license_status")
    if type(policy["ingestion_authorized"]) is not bool:
        _fail("invalid_ingestion_authorization")

    approval = policy["approval_status"]
    if type(approval) is not str or approval not in APPROVAL_STATUSES:
        _fail("invalid_approval_status")
    if approval == "UNKNOWN":
        _fail("authorization_unknown")
    if approval == "PENDING":
        _fail("authorization_pending")
    if approval == "DENIED":
        _fail("authorization_denied")
    if policy["ingestion_authorized"] is False:
        _fail("authorization_conflict")

    provenance = policy["provenance"]
    if type(provenance) is not dict or set(provenance) != {
        "recorded_at", "recorded_by", "approval_reference",
    }:
        _fail("invalid_provenance")
    if (not _safe_text(provenance["recorded_by"], 128)
            or SOURCE_ID.fullmatch(provenance["recorded_by"]) is None
            or not _safe_text(provenance["approval_reference"], 128)
            or SOURCE_ID.fullmatch(provenance["approval_reference"]) is None):
        _fail("invalid_provenance")
    recorded_at = provenance["recorded_at"]
    if not _safe_text(recorded_at, 35):
        _fail("invalid_provenance")
    try:
        parsed_time = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))
        if parsed_time.tzinfo is None or parsed_time.utcoffset() is None:
            raise ValueError
    except (ValueError, OverflowError):
        _fail("invalid_provenance")

    retention = policy["retention_policy"]
    if (type(retention) is not dict or set(retention) != {"mode", "max_age_seconds"}
            or type(retention.get("mode")) is not str
            or retention.get("mode") not in RETENTION_MODES
            or type(retention.get("max_age_seconds")) is not int
            or not 1 <= retention["max_age_seconds"] <= 31_536_000):
        _fail("invalid_retention_policy")

    if (type(policy["deletion_policy"]) is not str
            or policy["deletion_policy"] not in DELETION_POLICIES):
        _fail("invalid_deletion_policy")
    _validate_uri(policy)

    expected = _COMBINATIONS[policy["source_type"]]
    classification, licenses, retention_mode, deletion = expected
    if (policy["classification"] != classification
            or policy["license_status"] not in licenses
            or retention["mode"] != retention_mode
            or policy["deletion_policy"] != deletion):
        _fail("incompatible_policy_combination")
    age = retention["max_age_seconds"]
    maximum_age = {
        "synthetic_fixture": 86_400,
        "public_document": 31_536_000,
        "public_repository_file": 31_536_000,
        "internal_document": 2_592_000,
        "confidential_document": 604_800,
        "restricted_document": 0,
    }[policy["source_type"]]
    if age > maximum_age:
        _fail("invalid_retention_policy")
    if policy["source_type"] == "restricted_document":
        _fail("restricted_source_not_supported")

    return {
        "assurance": "STRUCTURE_ONLY",
        "decision": "PASS",
        "errors": [],
        "schema_version": SCHEMA_VERSION,
    }


def _read_policy(path: Path) -> object:
    try:
        metadata = path.lstat()
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            _fail("input_not_regular_file")
        if metadata.st_size > MAX_INPUT_BYTES:
            _fail("input_too_large")
        with path.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
    except PolicyValidationError:
        raise
    except OSError:
        _fail("input_unreadable")
    return _load_json_bytes(raw, MAX_INPUT_BYTES)


def load_and_validate(path: Path) -> dict[str, object]:
    return validate_policy(_read_policy(Path(path)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="local JSON source policy file")
    args = parser.parse_args(argv)
    try:
        report = load_and_validate(args.input)
    except PolicyValidationError as error:
        report = {
            "assurance": "STRUCTURE_ONLY",
            "decision": "FAIL",
            "errors": [error.code],
            "schema_version": SCHEMA_VERSION,
        }
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 1
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
