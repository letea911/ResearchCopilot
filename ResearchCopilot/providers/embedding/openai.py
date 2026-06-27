import os
import openai
from config.model import EmbeddingConfig
from providers.interfaces import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider.

    Reads API key from EMBEDDING_API_KEY environment variable.
    """

    def __init__(self, config: EmbeddingConfig):
        self._config = config
        api_key = os.getenv("EMBEDDING_API_KEY", "")
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable is not set")
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url or None,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._config.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
