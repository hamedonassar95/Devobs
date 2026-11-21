"""Behavioral contract tests for the xAI Grok adapter (no network, no credentials)."""
import json
import unittest
from decimal import Decimal
from unittest.mock import Mock

from urllib.error import HTTPError, URLError

from devobs.ai.providers import (
    XAI_BASE_URL,
    XaiAdapter,
    XaiAuthorization,
    XaiRequest,
    XaiState,
    create_xai_provider,
    load_xai_config,
)
from devobs.ai.providers.xai_adapter import _RedirectRejected

SECRET = "sk-proj-abcdefghijklmnopqrstuvwxyz123456"
PROMPT = "Summarize the redacted deployment log; keep the recommendation reversible."


def live_config(**overrides):
    env = {
        "XAI_ENABLED": "true",
        "XAI_DRY_RUN": "false",
        "XAI_MAX_REQUESTS_PER_RUN": "3",
        "XAI_MAX_COST_USD": "1.00",
        "DEVOBS_AI_BUDGET_APPROVED": "true",
    }
    env.update(overrides)
    return load_xai_config(env)


def auth(ceiling="1.00"):
    return XaiAuthorization(
        approved=True,
        approver="owner",
        max_cost_usd=Decimal(ceiling),
    )


def payload(text="Advisory text; no actions were taken.", ticks=1_000_000):
    return {
        "id": "resp-1",
        "object": "chat.completion",
        "created": 1,
        "model": "grok-4.7",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": text,
                "refusal": None,
                "tool_calls": None,
            },
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 32,
            "completion_tokens": 16,
            "total_tokens": 48,
            "prompt_tokens_details": {
                "text_tokens": 32, "cached_tokens": 0,
                "audio_tokens": 0, "image_tokens": 0,
            },
            "completion_tokens_details": {
                "reasoning_tokens": 4, "audio_tokens": 0,
                "accepted_prediction_tokens": 0, "rejected_prediction_tokens": 0,
            },
            "cost_in_usd_ticks": ticks,
        },
    }


def response(status=200, body=None, raw=None):
    result = Mock()
    result.status = status
    result.read.return_value = (
        raw if raw is not None else json.dumps(body or payload()).encode("utf-8")
    )
    result.__enter__ = Mock(return_value=result)
    result.__exit__ = Mock(return_value=False)
    return result


class XaiAdapterTests(unittest.TestCase):
    def test_default_config_is_offline_disabled_and_cost_free(self):
        config = load_xai_config({})
        self.assertFalse(config.enabled)
        self.assertTrue(config.dry_run)
        self.assertEqual(config.model, "grok-4.7")
        self.assertEqual(config.max_output_tokens, 2048)
        self.assertEqual(config.max_requests_per_run, 0)
        self.assertEqual(config.max_cost_usd, Decimal("0"))
        provider = create_xai_provider(config)
        result = provider.complete(XaiRequest(PROMPT))
        self.assertEqual(result.state, XaiState.CONFIGURATION_BLOCKED)

    def test_dry_run_is_deterministic_and_never_real(self):
        config = load_xai_config({"XAI_ENABLED": "true"})
        provider = create_xai_provider(config)
        first = provider.complete(XaiRequest(PROMPT))
        second = provider.complete(XaiRequest(PROMPT))
        self.assertEqual(first.state, XaiState.MOCK_SUCCESS)
        self.assertEqual(first.text, second.text)
        self.assertTrue(first.is_mock)
        self.assertEqual(first.source, "xai_offline_mock")
        self.assertNotEqual(first.state, XaiState.VERIFIED_RESPONSE)
        self.assertIn("MOCK RESPONSE", first.text)
        self.assertIn("NOT a real Grok response", first.text)

    def test_live_success_uses_exact_contract_without_tools(self):
        opener = Mock()
        opener.open.return_value = response()
        adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=opener)
        result = adapter.complete(XaiRequest(PROMPT, request_id="req-1"), auth())

        self.assertEqual(result.state, XaiState.VERIFIED_RESPONSE)
        self.assertFalse(result.is_mock)
        self.assertEqual(result.text, "Advisory text; no actions were taken.")
        self.assertEqual(result.cost_usd, Decimal("0.0001"))
        args, kwargs = opener.open.call_args
        request = args[0]
        sent = json.loads(request.data)
        self.assertEqual(request.full_url, XAI_BASE_URL + "/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer synthetic-key")
        self.assertEqual(kwargs["timeout"], 20)
        self.assertEqual(sent["model"], "grok-4.7")
        self.assertEqual(sent["max_completion_tokens"], 2048)
        self.assertEqual(sent["reasoning_effort"], "low")
        self.assertEqual(sent["messages"][1]["content"], PROMPT)
        for forbidden in ("tools", "tool_choice", "search_parameters",
                          "web_search_options", "deferred", "stream"):
            self.assertNotIn(forbidden, sent) if forbidden != "stream" else self.assertIs(sent["stream"], False)
        self.assertEqual(opener.open.call_count, 1)

    def test_authentication_failures_return_explicit_state(self):
        for status in (401, 403):
            with self.subTest(status=status):
                opener = Mock()
                opener.open.side_effect = HTTPError(
                    "https://api.x.ai/v1/chat/completions", status, "denied", {}, None)
                adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=opener)
                result = adapter.complete(XaiRequest(PROMPT), auth())
                self.assertEqual(result.state, XaiState.AUTHENTICATION_REQUIRED)
                self.assertEqual(result.reason, "http_%d" % status)

    def test_missing_key_is_authentication_required(self):
        adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=Mock())
        adapter._api_key = ""
        result = adapter.complete(XaiRequest(PROMPT), auth())
        self.assertEqual(result.state, XaiState.AUTHENTICATION_REQUIRED)
        self.assertEqual(result.reason, "missing_api_key")

    def test_rate_limit_retry_is_bounded(self):
        opener = Mock()
        opener.open.side_effect = [
            response(status=429, raw=b"rate limited"),
            response(),
        ]
        sleeper = Mock()
        config = live_config(XAI_MAX_RETRIES="2")
        adapter = XaiAdapter(config, api_key="synthetic-key",
                             opener=opener, sleeper=sleeper)
        result = adapter.complete(XaiRequest(PROMPT), auth())
        self.assertEqual(result.state, XaiState.VERIFIED_RESPONSE)
        self.assertEqual(opener.open.call_count, 2)
        self.assertEqual(sleeper.call_count, 1)

    def test_persistent_server_error_is_bounded_and_safe(self):
        opener = Mock()
        opener.open.side_effect = HTTPError(
            "https://api.x.ai/v1/chat/completions", 503, "unavailable", {}, None)
        sleeper = Mock()
        adapter = XaiAdapter(live_config(XAI_MAX_RETRIES="2"),
                             api_key="synthetic-key", opener=opener, sleeper=sleeper)
        result = adapter.complete(XaiRequest(PROMPT), auth())
        self.assertEqual(result.state, XaiState.PROVIDER_UNAVAILABLE)
        self.assertEqual(result.reason, "retryable")
        self.assertEqual(opener.open.call_count, 3)
        self.assertEqual(sleeper.call_count, 2)

    def test_transport_redirect_and_malformed_responses_fail_closed(self):
        cases = []
        transport = Mock()
        transport.open.side_effect = URLError("network down")
        cases.append(("transport", transport))

        redirect = Mock()
        redirect.open.side_effect = _RedirectRejected()
        cases.append(("redirect", redirect))

        malformed = Mock()
        malformed.open.return_value = response(raw=b"{not json")
        cases.append(("malformed", malformed))

        tools = Mock()
        bad = payload()
        bad["choices"][0]["message"]["tool_calls"] = [{"type": "function"}]
        tools.open.return_value = response(body=bad)
        cases.append(("tools", tools))

        duplicate = Mock()
        duplicate.open.return_value = response(
            raw=b'{"object":"chat.completion","object":"chat.completion"}')
        cases.append(("duplicate", duplicate))

        for name, opener in cases:
            with self.subTest(case=name):
                adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=opener)
                result = adapter.complete(XaiRequest(PROMPT), auth())
                self.assertEqual(result.state, XaiState.PROVIDER_UNAVAILABLE)
                self.assertNotIn("network down", str(result.to_dict()))

    def test_budget_and_authorization_gates(self):
        scenarios = (
            ({}, None, "authorization_required"),
            ({"XAI_MAX_REQUESTS_PER_RUN": "0"}, auth(), "request_limit_zero"),
            ({"DEVOBS_AI_BUDGET_APPROVED": "false"}, auth(), "paid_calls_not_approved"),
        )
        for overrides, supplied, expected in scenarios:
            with self.subTest(reason=expected):
                opener = Mock()
                adapter = XaiAdapter(live_config(**overrides),
                                     api_key="synthetic-key", opener=opener)
                result = adapter.complete(XaiRequest(PROMPT), supplied)
                self.assertEqual(result.state, XaiState.BUDGET_BLOCKED)
                self.assertEqual(result.reason, expected)
                opener.open.assert_not_called()

        adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=Mock())
        result = adapter.complete(XaiRequest(PROMPT), auth("0.01"))
        self.assertEqual(result.state, XaiState.BUDGET_BLOCKED)
        self.assertEqual(result.reason, "authorized_cost_ceiling_exceeded")

    def test_actual_cost_overage_blocks_and_logs_safely(self):
        opener = Mock()
        opener.open.return_value = response(body=payload(ticks=2 * 10**10))
        adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=opener)
        result = adapter.complete(XaiRequest(PROMPT), auth())
        self.assertEqual(result.state, XaiState.BUDGET_BLOCKED)
        self.assertEqual(result.reason, "actual_cost_exceeded")
        self.assertNotIn("synthetic-key", json.dumps(result.to_dict()))

    def test_secret_is_redacted_before_send_and_never_logged(self):
        opener = Mock()
        opener.open.return_value = response()
        adapter = XaiAdapter(live_config(), api_key="synthetic-key", opener=opener)
        result = adapter.complete(
            XaiRequest(f"api_key={SECRET}; summarize safely"), auth())
        args, _ = opener.open.call_args
        sent = json.loads(args[0].data)
        self.assertNotIn(SECRET, sent["messages"][1]["content"])
        self.assertIn("[REDACTED]", sent["messages"][1]["content"])
        serialized = json.dumps(result.to_dict())
        self.assertNotIn(SECRET, serialized)
        self.assertNotIn("synthetic-key", serialized)
        for entry in result.logs:
            for forbidden in ("prompt", "text", "api_key", "authorization"):
                self.assertNotIn(forbidden, entry)


if __name__ == "__main__":
    unittest.main()
