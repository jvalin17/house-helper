"""Tests for LLM provider abstraction — base protocol and factory."""

import pytest

from shared.llm.base import LLMProvider
from shared.llm.factory import create_provider, list_available_providers


class FakeProvider(LLMProvider):
    """A test provider that returns a canned response."""

    def __init__(self, response: str = "fake response"):
        self._response = response

    async def complete(self, prompt: str, system: str | None = None) -> str:
        return self._response

    def provider_name(self) -> str:
        return "fake"

    def model_name(self) -> str:
        return "fake-model"


class TestLLMProviderProtocol:
    """Verify the protocol contract works."""

    async def test_fake_provider_completes(self):
        provider = FakeProvider("hello world")
        result = await provider.complete("say hello")
        assert result == "hello world"

    async def test_fake_provider_name(self):
        provider = FakeProvider()
        assert provider.provider_name() == "fake"

    async def test_fake_provider_model_name(self):
        provider = FakeProvider()
        assert provider.model_name() == "fake-model"

    async def test_system_prompt_accepted(self):
        provider = FakeProvider("with system")
        result = await provider.complete("hello", system="be helpful")
        assert result == "with system"


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
