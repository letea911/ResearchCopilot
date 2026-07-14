"""Local embedding provider using sentence-transformers."""
import asyncio

from config.model import EmbeddingConfig
from providers.interfaces import BaseEmbeddingProvider


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """Local embedding using sentence-transformers (BGE, etc.). No API key needed."""

    def __init__(self, config: EmbeddingConfig):
        self._config = config
        self._model = None  # lazy load

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._config.model)
        return self._model

    def _embed_sync(self, texts: list[str]) -> list[list[float]]:
        # 同步 CPU 计算：首次会加载模型（几十秒）。放到线程池执行，避免阻塞事件循环。
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._embed_sync, texts)
