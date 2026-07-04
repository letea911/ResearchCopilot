"""DeepSeek LLM provider via OpenAI-compatible API."""
import os
import openai
from collections.abc import AsyncIterator
from config.model import LLMConfig
from models.message import ChatMessage
from providers.interfaces import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    """DeepSeek LLM provider using OpenAI-compatible API.

    Automatically sets the correct base_url for DeepSeek if not configured.
    Reads API key from LLM_API_KEY environment variable.
    """

    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

    def __init__(self, config: LLMConfig):
        self._config = config
        api_key = os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable is not set")
        base_url = config.base_url or self.DEFAULT_BASE_URL
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def chat(self, messages: list[ChatMessage], **kwargs) -> str:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)
        stream = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def _to_openai_format(self, messages: list[ChatMessage]) -> list[dict]:
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]
