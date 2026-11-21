"""Cost model tests with explicit source, currency, timestamp, and thresholds."""
import unittest
from decimal import Decimal

from devobs.ai.providers import estimate_max_request_cost, load_xai_config, ticks_to_usd
from devobs.ai.providers.xai_cost import (
    PRICING_CATALOG,
    XaiCostError,
    pricing_for,
)


class XaiCostTests(unittest.TestCase):
    def test_pricing_is_source_linked_and_bounded(self):
        pricing = PRICING_CATALOG["grok-4.7"]
        self.assertEqual(pricing.source_url, "https://docs.x.ai/developers/models")
        self.assertTrue(pricing.source)
        self.assertEqual(pricing.observed_at, "2026-11-21")
        self.assertEqual(pricing.currency, "USD")
        self.assertEqual(pricing.context_window_tokens, 500_000)
        self.assertEqual(pricing.long_context_threshold_tokens, 200_000)
        self.assertEqual(pricing.short_context.input_per_1m, Decimal("2.00"))
        self.assertEqual(pricing.short_context.cached_input_per_1m, Decimal("0.50"))
        self.assertEqual(pricing.short_context.output_per_1m, Decimal("6.00"))
        self.assertEqual(pricing.long_context.input_per_1m, Decimal("4.00"))
        self.assertEqual(pricing.long_context.cached_input_per_1m, Decimal("1.00"))
        self.assertEqual(pricing.long_context.output_per_1m, Decimal("12.00"))
        self.assertEqual(pricing.to_dict()["source"], pricing.source)

    def test_short_context_estimate_includes_reasoning_allowance(self):
        config = load_xai_config({
            "XAI_MAX_INPUT_TOKENS": "100000",
            "XAI_MAX_OUTPUT_TOKENS": "2000",
            "XAI_MAX_REASONING_TOKENS": "1000",
        })
        estimate = estimate_max_request_cost(config)
        self.assertEqual(estimate.tier, "short_context")
        self.assertEqual(estimate.currency, "USD")
        self.assertEqual(estimate.prompt_tokens, 100_000)
        self.assertEqual(estimate.output_tokens, 2_000)
        self.assertEqual(estimate.reasoning_tokens, 1_000)
        # 100000 * 2/1M + 3000 * 6/1M = 0.2 + 0.018 = 0.218
        self.assertEqual(estimate.max_cost_usd, Decimal("0.218"))
        self.assertEqual(estimate.to_dict()["source_url"], pricing_for("grok-4.7").source_url)

    def test_long_context_threshold_uses_higher_rates_for_all_tokens(self):
        config = load_xai_config({
            "XAI_MAX_INPUT_TOKENS": "200000",
            "XAI_MAX_OUTPUT_TOKENS": "1000",
            "XAI_MAX_REASONING_TOKENS": "0",
        })
        estimate = estimate_max_request_cost(config)
        self.assertEqual(estimate.tier, "long_context")
        # 200000 * 4/1M + 1000 * 12/1M = 0.8 + 0.012 = 0.812
        self.assertEqual(estimate.max_cost_usd, Decimal("0.812"))

    def test_unknown_model_and_invalid_counts_fail_closed(self):
        with self.assertRaises(XaiCostError):
            pricing_for("grok-unknown")
        with self.assertRaises(XaiCostError):
            pricing_for("grok-4.7").tier_for_prompt(500_001)
        with self.assertRaises(XaiCostError):
            pricing_for("grok-4.7").tier_for_prompt(-1)

    def test_ticks_conversion_matches_official_denominator(self):
        self.assertEqual(ticks_to_usd(10_000_000_000), Decimal("1"))
        self.assertEqual(ticks_to_usd(37_756_000), Decimal("0.0037756"))
        for value in (-1, True, "1000", 10**19):
            with self.subTest(value=value), self.assertRaises(XaiCostError):
                ticks_to_usd(value)


if __name__ == "__main__":
    unittest.main()
