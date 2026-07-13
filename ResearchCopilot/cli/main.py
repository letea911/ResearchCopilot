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


_app_ctx = None

def _get_context():
    """Lazy-init the application context — build once, reuse."""
    global _app_ctx
    if _app_ctx is None:
        _app_ctx = _build_context()
    return _app_ctx


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
    # Only build context once (lazy init on first command)
    # We defer _build_context to the actual commands to avoid
    # loading models/connecting to DB at CLI startup
    pass


@cli.command()
@click.argument("path", type=click.Path(exists=True))
def ingest(path):
    """Ingest a PDF paper into the knowledge base."""
    ctx = _get_context()
    _init_stores(ctx)

    async def _run():
        doc_id = await ctx["pipeline"].ingest(Path(path))
        console.print(f"[green]✓[/green] Ingested: [bold]{path}[/bold]")
        console.print(f"  Document ID: [dim]{doc_id}[/dim]")

    asyncio.run(_run())


@cli.command()
@click.argument("dir_path", type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option("--pattern", default="*.pdf", help="File pattern to match (default: *.pdf)")
def ingest_dir(dir_path, pattern):
    """Batch ingest all PDFs in a directory."""
    ctx = _get_context()
    _init_stores(ctx)
    pipeline = ctx["pipeline"]
    meta_store = ctx["meta_store"]

    import glob as glob_mod
    files = sorted(Path(dir_path).glob(pattern))
    # Filter to only files (not subdirectories)
    pdf_files = [f for f in files if f.is_file()]

    if not pdf_files:
        console.print(f"[yellow]No files matching '{pattern}' found in {dir_path}[/yellow]")
        return

    console.print(f"Found [bold]{len(pdf_files)}[/bold] files. Starting import...\n")

    async def _run():
        ok, fail, skip = 0, 0, 0
        for i, pdf in enumerate(pdf_files):
            try:
                doc_id = await pipeline.ingest(pdf)
                if doc_id and len(doc_id) > 0:
                    ok += 1
                    console.print(f"[{i+1}/{len(pdf_files)}] [green]OK[/green] {pdf.name[:60]}")
            except Exception as e:
                err = str(e)
                if "already imported" in err.lower() or "skip" in err.lower():
                    skip += 1
                    console.print(f"[{i+1}/{len(pdf_files)}] [dim]SKIP[/dim] {pdf.name[:60]}")
                else:
                    fail += 1
                    console.print(f"[{i+1}/{len(pdf_files)}] [red]FAIL[/red] {pdf.name[:60]} — {err[:50]}")

        docs = await meta_store.list_documents(limit=10000)
        console.print(f"\n[bold]Done.[/bold] OK: {ok}, Failed: {fail}, Skipped: {skip}")
        console.print(f"Total documents: {len(docs)}")

    asyncio.run(_run())


@cli.command()
@click.argument("question")
@click.option("--top-k", default=10, help="Number of chunks to retrieve")
@click.option("--stream/--no-stream", default=True, help="Stream the response")
def ask(question, top_k, stream):
    """Ask a research question."""
    ctx = _get_context()
    _init_stores(ctx)
    chat = ctx["chat"]

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
                console.print("\n[bold]📚 References:[/bold]")
                for i, c in enumerate(result.citations):
                    # Build citation line with full metadata
                    parts = [f"[bold][{i+1}][/bold] {c.title}"]
                    if c.authors:
                        parts.append(f"[dim]{c.authors}[/dim]")
                    if c.journal:
                        parts.append(f"[italic]{c.journal}[/italic]")
                    if c.year:
                        parts.append(str(c.year))
                    if c.page_number:
                        parts.append(f"p.{c.page_number}")
                    line = ", ".join(parts)
                    console.print(f"  {line}")
                    # Clickable PDF link
                    if c.file_path:
                        file_url = f"file:///{c.file_path.replace(chr(92), '/')}"
                        console.print(f"    [link={file_url}]📄 Open PDF[/link]")

    asyncio.run(_run())


@cli.command()
@click.argument("query")
@click.option("--top-k", default=20, help="Number of results")
@click.option("--type", "doc_type", default=None, help="Filter by document type")
def search_cmd(query, top_k, doc_type):
    """Search the knowledge base without LLM."""
    ctx = _get_context()
    _init_stores(ctx)
    svc = ctx["search"]

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
def summarize(document_id, focus):
    """Summarize a document by ID."""
    ctx = _get_context()
    _init_stores(ctx)
    svc = ctx["summarize"]

    async def _run():
        result = await svc.summarize(document_id, focus=focus)
        console.print(Markdown(result.answer))
        if result.citations:
            c = result.citations[0]
            parts = [f"[dim]Source:[/dim] {c.title}"]
            if c.authors:
                parts.append(f"[dim]{c.authors}[/dim]")
            if c.journal:
                parts.append(f"[italic]{c.journal}[/italic]")
            if c.year:
                parts.append(str(c.year))
            line = ", ".join(parts)
            console.print(f"\n{line}")
            if c.file_path:
                file_url = f"file:///{c.file_path.replace(chr(92), '/')}"
                console.print(f"  [link={file_url}]📄 Open PDF[/link]")

    asyncio.run(_run())


@cli.command()
@click.option("--doc-type", default=None, help="Filter by document type")
@click.option("--limit", default=20, help="Number of documents to list")
def list_docs(doc_type, limit):
    """List documents in the knowledge base."""
    ctx = _get_context()
    _init_stores(ctx)
    meta = ctx["meta_store"]

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
def status():
    """Show knowledge base status."""
    ctx = _get_context()
    _init_stores(ctx)
    meta = ctx["meta_store"]
    vec = ctx["vector_store"]
    file_store = ctx["file_store"]

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
