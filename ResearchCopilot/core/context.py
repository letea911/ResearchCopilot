"""Shared application context — wires all dependencies.

Used by both the CLI (cli/main.py) and the desktop GUI (gui/) so the
dependency graph is defined in exactly one place.
"""


def build_context() -> dict:
    """Build the application context — all wired dependencies.

    Note: constructing LocalEmbeddingProvider is cheap, but the underlying
    sentence-transformers model loads lazily on first embed() call, which can
    take tens of seconds. Callers that care about startup latency should run
    this (and initialize_stores) off the UI thread / in a background task.
    """
    from config.loader import load_config
    from providers.llm.deepseek import DeepSeekProvider
    from providers.embedding.local import LocalEmbeddingProvider
    from storage.file_store import LocalFileStore
    from storage.sqlite_meta import SQLiteMetadataStore
    from storage.chroma_vector import ChromaVectorStore
    from ingestion.pipeline import IngestionPipeline
    from ingestion.parsers.pdf import PyMuPDFParser
    from ingestion.normalizer import TextNormalizer
    from ingestion.chunker import ScientificChunker
    from ingestion.metadata import LLMMetadataExtractor
    from retrieval.keyword import SQLiteFTS5Retriever
    from retrieval.vector import ChromaVectorRetriever
    from retrieval.hybrid import WeightedHybridRetriever
    from services.chat import ChatService
    from services.search import SearchService
    from services.summarize import SummarizeService

    llm_cfg, emb_cfg, chunk_cfg, storage_cfg = load_config()

    llm = DeepSeekProvider(llm_cfg)
    embedder = LocalEmbeddingProvider(emb_cfg)

    file_store = LocalFileStore(storage_cfg)
    meta_store = SQLiteMetadataStore(storage_cfg)
    vector_store = ChromaVectorStore(storage_cfg)

    keyword_retriever = SQLiteFTS5Retriever(storage_cfg)
    vector_retriever = ChromaVectorRetriever(vector_store, meta_store)
    hybrid_retriever = WeightedHybridRetriever(keyword_retriever, vector_retriever)

    pipeline = IngestionPipeline(
        parsers={".pdf": PyMuPDFParser()},
        normalizer=TextNormalizer(),
        chunker=ScientificChunker(chunk_cfg),
        metadata_extractor=LLMMetadataExtractor(llm),
        embedder=embedder,
        file_store=file_store,
        meta_store=meta_store,
        vector_store=vector_store,
    )

    chat = ChatService(llm, embedder, hybrid_retriever, meta_store, file_store)
    search = SearchService(embedder, hybrid_retriever)
    summarize = SummarizeService(llm, meta_store, file_store)

    return {
        "llm": llm, "embedder": embedder,
        "file_store": file_store, "meta_store": meta_store, "vector_store": vector_store,
        "pipeline": pipeline, "chat": chat, "search": search, "summarize": summarize,
    }


async def initialize_stores(ctx: dict) -> None:
    """Initialize stores (create tables, connect). Safe to await once."""
    await ctx["meta_store"].initialize()
    await ctx["vector_store"].initialize()
