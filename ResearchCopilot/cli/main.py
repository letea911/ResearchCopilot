"""ResearchCopilot CLI — research literature assistant."""
import sys
import asyncio
import click
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()


def _build_context():
    """Build the application context — all wired dependencies."""
    from config.loader import load_config
    from providers.llm.openai import OpenAILLMProvider
    from providers.embedding.openai import OpenAIEmbeddingProvider
    from storage.file_store import LocalFileStore
    from storage.sqlite_meta import SQLiteMetadataStore
    from storage.chroma_vector import ChromaVectorStore
    from ingestion.pipeline import IngestionPipeline
    from ingestion.parsers.pdf import PyMuPDFParser
    from ingestion.normalizer import TextNormalizer
    from ingestion.chunker import ScientificChunker
    from ingestion.metadata import RuleBasedMetadataExtractor
    from retrieval.keyword import SQLiteFTS5Retriever
    from retrieval.vector import ChromaVectorRetriever
    from retrieval.hybrid import WeightedHybridRetriever
    from services.chat import ChatService
    from services.search import SearchService
    from services.summarize import SummarizeService

    llm_cfg, emb_cfg, chunk_cfg, storage_cfg = load_config()

    llm = OpenAILLMProvider(llm_cfg)
    embedder = OpenAIEmbeddingProvider(emb_cfg)

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
        metadata_extractor=RuleBasedMetadataExtractor(),
        embedder=embedder,
        file_store=file_store,
        meta_store=meta_store,
        vector_store=vector_store,
    )

    chat = ChatService(llm, embedder, hybrid_retriever)
    search = SearchService(embedder, hybrid_retriever)
    summarize = SummarizeService(llm, meta_store)

    return {
        "llm": llm, "embedder": embedder,
        "file_store": file_store, "meta_store": meta_store, "vector_store": vector_store,
        "pipeline": pipeline, "chat": chat, "search": search, "summarize": summarize,
    }


def _init_stores(ctx):
    """Initialize stores (create tables, connect)."""
    async def _init():
        await ctx["meta_store"].initialize()
        await ctx["vector_store"].initialize()
    asyncio.run(_init())


@click.group()
@click.pass_context
def cli(ctx):
    """ResearchCopilot — AI-powered research literature assistant."""
    ctx.ensure_object(dict)
    console.print(Panel.fit(
        "[bold blue]ResearchCopilot[/bold blue] — AI Research Assistant",
        subtitle="Computational Chemistry / Materials Science / Catalysis"
    ))


@cli.command()
@click.argument("path", type=click.Path(exists=True))
@click.pass_context
def ingest(ctx, path):
    """Ingest a PDF paper into the knowledge base."""
    _init_stores(ctx.obj)

    async def _run():
        doc_id = await ctx.obj["pipeline"].ingest(Path(path))
        console.print(f"[green]✓[/green] Ingested: [bold]{path}[/bold]")
        console.print(f"  Document ID: [dim]{doc_id}[/dim]")

    asyncio.run(_run())


@cli.command()
@click.argument("question")
@click.option("--top-k", default=10, help="Number of chunks to retrieve")
@click.option("--stream/--no-stream", default=True, help="Stream the response")
@click.pass_context
def ask(ctx, question, top_k, stream):
    """Ask a research question."""
    _init_stores(ctx.obj)
    chat = ctx.obj["chat"]

    async def _run():
        if stream:
            console.print("[dim]Thinking...[/dim]\n")
            async for token in chat.ask_stream(question, top_k=top_k):
                console.print(token, end="")
            console.print("\n")
        else:
            result = await chat.ask(question, top_k=top_k)
            console.print(Markdown(result.answer))
            if result.citations:
                console.print("\n[bold]Citations:[/bold]")
                for i, c in enumerate(result.citations):
                    console.print(f"  [{i+1}] {c.title} ({c.authors}, {c.year})")

    asyncio.run(_run())


@cli.command()
@click.argument("query")
@click.option("--top-k", default=20, help="Number of results")
@click.option("--type", "doc_type", default=None, help="Filter by document type")
@click.pass_context
def search(ctx, query, top_k, doc_type):
    """Search the knowledge base without LLM."""
    _init_stores(ctx.obj)
    svc = ctx.obj["search"]

    async def _run():
        result = await svc.search(query, top_k=top_k, document_type=doc_type)
        table = Table(title=f"Results for: {query}")
        table.add_column("#", style="dim")
        table.add_column("Title")
        table.add_column("Authors")
        table.add_column("Year")
        table.add_column("Score", justify="right")

        for i, r in enumerate(result.results):
            table.add_row(
                str(i + 1),
                r.metadata.get("title", "Unknown")[:60],
                r.metadata.get("authors", "")[:30],
                str(r.metadata.get("year", "")),
                f"{r.score:.3f}",
            )
        console.print(table)
        console.print(f"[dim]{result.total_hits} results[/dim]")

    asyncio.run(_run())


@cli.command()
@click.argument("document_id")
@click.option("--focus", default=None, help="Focus: methods, results, conclusion")
@click.pass_context
def summarize(ctx, document_id, focus):
    """Summarize a document by ID."""
    _init_stores(ctx.obj)
    svc = ctx.obj["summarize"]

    async def _run():
        result = await svc.summarize(document_id, focus=focus)
        console.print(Markdown(result.answer))
        if result.citations:
            c = result.citations[0]
            console.print(f"\n[dim]Source: {c.title} ({c.authors}, {c.year})[/dim]")

    asyncio.run(_run())


@cli.command()
@click.option("--doc-type", default=None, help="Filter by document type")
@click.option("--limit", default=20, help="Number of documents to list")
@click.pass_context
def list_docs(ctx, doc_type, limit):
    """List documents in the knowledge base."""
    _init_stores(ctx.obj)
    meta = ctx.obj["meta_store"]

    async def _run():
        docs = await meta.list_documents(document_type=doc_type, limit=limit)
        if not docs:
            console.print("[yellow]No documents found.[/yellow]")
            return
        table = Table(title="Documents")
        table.add_column("ID", style="dim")
        table.add_column("Title")
        table.add_column("Authors")
        table.add_column("Year")
        table.add_column("Type")

        for d in docs:
            table.add_row(
                d.id[:8],
                d.title[:60],
                (d.authors or "")[:25],
                str(d.year or ""),
                d.document_type,
            )
        console.print(table)
        console.print(f"[dim]{len(docs)} document(s)[/dim]")

    asyncio.run(_run())


@cli.command()
@click.pass_context
def status(ctx):
    """Show knowledge base status."""
    _init_stores(ctx.obj)
    meta = ctx.obj["meta_store"]
    vec = ctx.obj["vector_store"]
    file_store = ctx.obj["file_store"]

    async def _run():
        docs = await meta.list_documents(limit=1000)
        vec_count = await vec.count()

        console.print(f"[bold]Documents:[/bold] {len(docs)}")
        console.print(f"[bold]Vectors:[/bold] {vec_count}")
        console.print(f"[bold]Papers on disk:[/bold] {len(file_store.list('papers'))}")

        if docs:
            types = {}
            for d in docs:
                types[d.document_type] = types.get(d.document_type, 0) + 1
            console.print("\n[bold]By type:[/bold]")
            for t, c in types.items():
                console.print(f"  {t}: {c}")

    asyncio.run(_run())


if __name__ == "__main__":
    cli()
