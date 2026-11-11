"""Behavior-based OpenArt MCP handoff tests; no network or credit spending."""
import copy
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from openart_media_request import InvalidMediaRequest, validate_media_request  # noqa: E402


class OpenArtMediaRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.example = json.loads((ROOT / "docs/examples/devobs_openart_brief.json").read_text(encoding="utf-8"))

    def setUp(self):
        self.data = copy.deepcopy(self.example)

    def test_draft_is_valid_but_never_approved_or_submitted(self):
        result = validate_media_request(self.data)
        self.assertEqual(len(result["request_sha256"]), 64)
        self.assertEqual(result["classification"], "offline_draft_only")
        self.assertIs(result["approved"], False)
        self.assertIs(result["credits_authorized"], False)
        self.assertIs(result["generation_submitted"], False)

    def test_hash_is_deterministic_and_detects_prompt_change(self):
        before = validate_media_request(self.data)["request_sha256"]
        reverse = dict(reversed(list(self.data.items())))
        self.assertEqual(before, validate_media_request(reverse)["request_sha256"])
        self.data["deliverables"][0]["prompt"] += " with no external provider logos"
        self.assertNotEqual(before, validate_media_request(self.data)["request_sha256"])

    def test_no_extra_fields_including_token_credentials(self):
        self.data["api_key"] = "sensitive-should-not-be-stored"
        with self.assertRaisesRegex(InvalidMediaRequest, "unsupported"):
            validate_media_request(self.data)

    def test_cannot_falsely_mark_owner_approval(self):
        self.data["state"] = "APPROVED"
        with self.assertRaisesRegex(InvalidMediaRequest, "DRAFT"):
            validate_media_request(self.data)

    def test_public_publishing_is_rejected(self):
        self.data["visibility"] = "public"
        with self.assertRaisesRegex(InvalidMediaRequest, "public"):
            validate_media_request(self.data)

    def test_duplicate_delivery_id_rejected(self):
        self.data["deliverables"].append(copy.deepcopy(self.data["deliverables"][0]))
        with self.assertRaisesRegex(InvalidMediaRequest, "duplicate"):
            validate_media_request(self.data)

    def test_video_duration_is_bounded_and_model_independent(self):
        item = self.data["deliverables"][0]
        item["media_type"] = "video"
        item["requested_duration_seconds"] = 8
        self.assertEqual(validate_media_request(self.data)["deliverable_count"], 1)
        item["requested_duration_seconds"] = 60
        with self.assertRaisesRegex(InvalidMediaRequest, "video-only"):
            validate_media_request(self.data)

    def test_wrong_typed_ratio_and_language_rejected(self):
        self.data["deliverables"][0]["aspect_ratio"] = ["16:9"]
        with self.assertRaisesRegex(InvalidMediaRequest, "unsupported"):
            validate_media_request(self.data)
        self.data["deliverables"][0]["aspect_ratio"] = "16:9"
        self.data["deliverables"][0]["language"] = {"code": "ar"}
        with self.assertRaisesRegex(InvalidMediaRequest, "unsupported"):
            validate_media_request(self.data)

    def test_image_rejects_duration(self):
        self.data["deliverables"][0]["requested_duration_seconds"] = 8
        with self.assertRaisesRegex(InvalidMediaRequest, "video-only"):
            validate_media_request(self.data)

    def test_empty_or_short_prompt_rejected(self):
        self.data["deliverables"][0]["prompt"] = "short"
        with self.assertRaisesRegex(InvalidMediaRequest, "minimum"):
            validate_media_request(self.data)

    def test_cli_good_and_malformed_json(self):
        script = ROOT / "scripts/openart_media_request.py"
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "brief.json"
            path.write_text(json.dumps(self.data), encoding="utf-8")
            self.data["deliverables"][0]["prompt"] = self.example["deliverables"][0]["prompt"]
            path.write_text(json.dumps(self.data), encoding="utf-8")
            ok = subprocess.run(
                [sys.executable, str(script), "--input", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertIs(json.loads(ok.stdout)["credits_authorized"], False)
            path.write_text('{"schema_version":', encoding="utf-8")
            bad = subprocess.run(
                [sys.executable, str(script), "--input", str(path)],
                capture_output=True, text=True, check=False,
            )
            self.assertEqual(bad.returncode, 2)
            self.assertIn("OPENART_REQUEST_INVALID", bad.stderr)


if __name__ == "__main__":
    unittest.main()
