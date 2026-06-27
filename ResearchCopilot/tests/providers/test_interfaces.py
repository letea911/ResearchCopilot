import pytest
from abc import ABC
from providers.interfaces import BaseLLMProvider, BaseEmbeddingProvider


def test_base_llm_provider_is_abstract():
    assert issubclass(BaseLLMProvider, ABC)
    with pytest.raises(TypeError):
        BaseLLMProvider()  # cannot instantiate ABC


def test_base_llm_provider_declares_chat_and_stream():
    assert hasattr(BaseLLMProvider, "chat")
    assert hasattr(BaseLLMProvider, "stream")


def test_base_embedding_provider_is_abstract():
    assert issubclass(BaseEmbeddingProvider, ABC)
    with pytest.raises(TypeError):
        BaseEmbeddingProvider()


def test_base_embedding_provider_declares_embed():
    assert hasattr(BaseEmbeddingProvider, "embed")


def test_minimal_implementation():
    """Verify a subclass with all methods instantiable."""

    class FakeLLM(BaseLLMProvider):
        async def chat(self, messages, **kwargs):
            return "ok"

        async def stream(self, messages, **kwargs):
            yield "ok"

    class FakeEmbed(BaseEmbeddingProvider):
        async def embed(self, texts):
            return [[0.0] * 3] * len(texts)

    llm = FakeLLM()
    embed = FakeEmbed()
    assert llm is not None
    assert embed is not None
