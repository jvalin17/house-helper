"""Tests for LLM provider abstraction — base protocol and factory."""

import pytest

from shared.llm.base import LLMProviderBase, NotSupportedError
from shared.llm.factory import create_provider, list_available_providers


class FakeProvider(LLMProviderBase):
    """A test provider that returns a canned response."""

    def __init__(self, response: str = "fake response"):
        self._response = response

    def complete(self, prompt: str, system: str | None = None) -> str:
        return self._response

    def provider_name(self) -> str:
        return "fake"

    def model_name(self) -> str:
        return "fake-model"


class TestLLMProviderBaseClass:
    """Verify the base class contract works."""

    def test_fake_provider_completes(self):
        provider = FakeProvider("hello world")
        result = provider.complete("say hello")
        assert result == "hello world"

    def test_fake_provider_name(self):
        provider = FakeProvider()
        assert provider.provider_name() == "fake"

    def test_fake_provider_model_name(self):
        provider = FakeProvider()
        assert provider.model_name() == "fake-model"

    def test_system_prompt_accepted(self):
        provider = FakeProvider("with system")
        result = provider.complete("hello", system="be helpful")
        assert result == "with system"

    def test_streaming_fallback_yields_complete_response(self):
        provider = FakeProvider("full response")
        chunks = list(provider.complete_stream("test prompt"))
        assert chunks == ["full response"]

    def test_vision_raises_not_supported_by_default(self):
        provider = FakeProvider()
        with pytest.raises(NotSupportedError, match="vision"):
            provider.complete_with_images("describe this", [{"url": "http://example.com/img.jpg"}])

    def test_supports_vision_false_by_default(self):
        provider = FakeProvider()
        assert provider.supports_vision is False

    def test_supports_streaming_true_by_default(self):
        provider = FakeProvider()
        assert provider.supports_streaming is True


class TestFactory:
    """Provider factory creates the right provider from config."""

    def test_none_provider_returns_none(self):
        provider = create_provider({"provider": None})
        assert provider is None

    def test_empty_config_returns_none(self):
        provider = create_provider({})
        assert provider is None

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_provider({"provider": "nonexistent_llm"})

    def test_list_available_providers(self):
        providers = list_available_providers()
        assert isinstance(providers, list)
        assert "claude" in providers
        assert "openai" in providers
        assert "ollama" in providers
