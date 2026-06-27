import pytest
from unittest.mock import AsyncMock, patch
from models.message import ChatMessage, Role
from config.model import LLMConfig
from providers.llm.openai import OpenAILLMProvider


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Ensure LLM_API_KEY is set for all tests."""
    monkeypatch.setenv("LLM_API_KEY", "test-key")


@pytest.fixture
def llm_config():
    return LLMConfig(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/anthropic",
        temperature=0.1,
        max_tokens=4096,
    )


@pytest.fixture
def messages():
    return [
        ChatMessage(role=Role.SYSTEM, content="You are a research assistant."),
        ChatMessage(role=Role.USER, content="What is DFT?"),
    ]


@pytest.mark.asyncio
async def test_chat_returns_string(llm_config, messages):
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="DFT stands for Density Functional Theory."))
    ]

    mock_create = AsyncMock(return_value=mock_response)
    with patch("openai.resources.chat.completions.AsyncCompletions.create", mock_create):
        provider = OpenAILLMProvider(llm_config)
        result = await provider.chat(messages)

    assert isinstance(result, str)
    assert "Density Functional Theory" in result


@pytest.mark.asyncio
async def test_chat_converts_chatmessage_to_openai_format(llm_config, messages):
    """ChatMessage.role and .content map to OpenAI dict format."""
    captured = []

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="ok"))]

    async def capture_create(*, messages, model, temperature, max_tokens, **kwargs):
        captured.append({"messages": messages, "model": model})
        return mock_response

    with patch("openai.resources.chat.completions.AsyncCompletions.create", side_effect=capture_create):
        provider = OpenAILLMProvider(llm_config)
        await provider.chat(messages)

    assert len(captured) == 1
    sent_messages = captured[0]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[0]["content"] == "You are a research assistant."
    assert sent_messages[1]["role"] == "user"
    assert captured[0]["model"] == "deepseek-v4-pro"


@pytest.mark.asyncio
async def test_chat_passes_kwargs(llm_config, messages):
    captured = {}

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="ok"))]

    async def capture(*, messages, model, **kwargs):
        captured.update(kwargs)
        return mock_response

    with patch("openai.resources.chat.completions.AsyncCompletions.create", side_effect=capture):
        provider = OpenAILLMProvider(llm_config)
        await provider.chat(messages, temperature=0.5, max_tokens=100)

    assert captured["temperature"] == 0.5
    assert captured["max_tokens"] == 100


@pytest.mark.asyncio
async def test_stream_yields_tokens(llm_config, messages):
    class FakeStream:
        def __init__(self):
            self._chunks = [
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="Hello"))]),
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content=" world"))]),
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content=None))]),  # end
            ]
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._chunks):
                raise StopAsyncIteration
            chunk = self._chunks[self._idx]
            self._idx += 1
            return chunk

    mock_create = AsyncMock(return_value=FakeStream())
    with patch("openai.resources.chat.completions.AsyncCompletions.create", mock_create):
        provider = OpenAILLMProvider(llm_config)
        tokens = []
        async for token in provider.stream(messages):
            tokens.append(token)

    assert tokens == ["Hello", " world"]
