import re
from ingestion.interfaces import BaseNormalizer


class TextNormalizer(BaseNormalizer):
    """Normalize scientific text for embedding.

    Handles:
    - Normalize line endings (CRLF → LF)
    - Collapse multiple blank lines into one
    - Remove excessive whitespace within lines
    - Fix hyphenated line breaks common in PDF extraction
    - Remove control characters (except newlines)
    - Normalize unicode (optional — basic ASCII normalization)
    """

    def normalize(self, text: str) -> str:
        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Fix hyphenated line breaks: "experi-\nment" → "experiment"
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)

        # Remove control characters except newline
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # Collapse multiple spaces within a line
        text = re.sub(r"[ \t]+", " ", text)

        # Collapse 3+ consecutive newlines into 2 (preserve paragraph breaks)
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip leading/trailing whitespace per line, keep newlines
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        # Final trim
        return text.strip()
