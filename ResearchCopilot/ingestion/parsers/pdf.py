import fitz  # PyMuPDF
from pathlib import Path
from ingestion.interfaces import BaseParser
from ingestion.models import ParsedDocument


class PyMuPDFParser(BaseParser):
    """Parse PDF files using PyMuPDF (fitz).

    Extracts full text from all pages and basic metadata
    (title, author) from the PDF info dictionary.
    """

    async def parse(self, source: Path) -> ParsedDocument:
        doc = fitz.open(str(source))
        try:
            full_text = []
            for page in doc:
                full_text.append(page.get_text())
            content = "\n\n".join(full_text)

            # Extract basic metadata
            metadata = dict(doc.metadata) if doc.metadata else {}
            raw_metadata = {
                "title": metadata.get("title", ""),
                "author": metadata.get("author", ""),
                "subject": metadata.get("subject", ""),
                "page_count": len(doc),
            }

            return ParsedDocument(
                source_path=str(source),
                content=content,
                source_type="pdf",
                raw_metadata=raw_metadata,
            )
        finally:
            doc.close()

    def supports(self, source: Path) -> bool:
        return source.suffix.lower() == ".pdf"
