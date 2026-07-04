"""Local embedding provider using sentence-transformers."""
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

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load_model()
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
