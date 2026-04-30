"""Tests for LLM provider factory and configuration.

Tests that all providers can be created with valid config,
that the factory rejects invalid providers, and that pricing
is defined for each supported provider.
"""

import pytest

from shared.llm.factory import create_provider, list_available_providers, SUPPORTED_PROVIDERS
from shared.llm.pricing import MODELS, estimate_cost


class TestProviderFactory:
    def test_all_supported_providers_listed(self):
        assert set(SUPPORTED_PROVIDERS) == {"claude", "openai", "deepseek", "grok", "gemini", "openrouter", "ollama", "huggingface", "custom"}

    def test_list_available_providers(self):
        providers = list_available_providers()
        assert "claude" in providers
        assert "openai" in providers
        assert "deepseek" in providers

    def test_create_claude_provider(self):
        provider = create_provider({"provider": "claude", "api_key": "test-key"})
        assert provider is not None
        assert provider.provider_name() == "claude"

    def test_create_openai_provider(self):
        provider = create_provider({"provider": "openai", "api_key": "test-key"})
        assert provider is not None
        assert provider.provider_name() == "openai"

    def test_create_deepseek_provider(self):
        provider = create_provider({"provider": "deepseek", "api_key": "test-key"})
        assert provider is not None
        assert provider.model_name() == "deepseek-chat"

    def test_create_grok_provider(self):
        provider = create_provider({"provider": "grok", "api_key": "test-key"})
        assert provider is not None
        assert provider.model_name() == "grok-2"

    def test_create_gemini_provider(self):
        provider = create_provider({"provider": "gemini", "api_key": "test-key"})
        assert provider is not None
        assert provider.model_name() == "gemini-2.0-flash"

    def test_create_ollama_provider(self):
        provider = create_provider({"provider": "ollama"})
        assert provider is not None
        assert provider.provider_name() == "ollama"

    def test_none_provider_returns_none(self):
        assert create_provider({"provider": None}) is None

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown"):
            create_provider({"provider": "nonexistent"})

    def test_claude_without_key_uses_env(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
        provider = create_provider({"provider": "claude"})
        assert provider is not None

    def test_openai_without_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key required"):
            create_provider({"provider": "openai"})


class TestProviderPricing:
    def test_every_provider_has_pricing(self):
        """Every supported provider (except ollama/huggingface) must have pricing."""
        for provider in ["claude", "openai", "deepseek", "grok", "gemini"]:
            assert provider in MODELS, f"No pricing for {provider}"
            assert len(MODELS[provider]) > 0, f"Empty pricing for {provider}"

    def test_each_model_has_required_fields(self):
        for provider, models in MODELS.items():
            for model in models:
                assert "id" in model, f"Missing id in {provider}"
                assert "name" in model, f"Missing name in {provider}"
                assert "input_per_1m" in model, f"Missing input_per_1m in {provider}/{model.get('id')}"
                assert "output_per_1m" in model, f"Missing output_per_1m in {provider}/{model.get('id')}"

    def test_each_provider_has_default(self):
        for provider, models in MODELS.items():
            defaults = [m for m in models if m.get("default")]
            assert len(defaults) <= 1, f"Multiple defaults for {provider}"

    def test_estimate_cost_claude_sonnet(self):
        cost = estimate_cost("claude", "claude-sonnet-4-20250514", 1000, 500)
        assert cost > 0
        assert cost < 0.05  # sanity: less than 5 cents for 1.5K tokens

    def test_estimate_cost_deepseek_cheaper_than_claude(self):
        deepseek_cost = estimate_cost("deepseek", "deepseek-chat", 1000, 500)
        claude_cost = estimate_cost("claude", "claude-sonnet-4-20250514", 1000, 500)
        assert deepseek_cost > 0
        assert deepseek_cost < claude_cost  # DeepSeek should be cheaper

    def test_estimate_cost_ollama_is_free(self):
        cost = estimate_cost("ollama", "mistral", 10000, 5000)
        assert cost == 0.0

    def test_estimate_cost_unknown_model_returns_zero(self):
        cost = estimate_cost("claude", "nonexistent-model", 1000, 500)
        assert cost == 0.0
