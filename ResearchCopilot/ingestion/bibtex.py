import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class BibEntry:
    title: str
    authors: str | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    abstract: str | None = None


class BibTeXParser:
    """Lightweight BibTeX parser (stdlib only).

    Parses @type{key, field = {value}, ...} entries. Handles {..} and ".." values,
    and converts BibTeX author format 'Last, First and Last2, First2'
    -> 'Last F, Last2 F2'.
    """

    _ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.*?)\}\s*(?=@|\Z)", re.DOTALL)

    def parse_entries(self, path: Path) -> list[BibEntry]:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
        return self.parse_text(text)

    def parse_text(self, text: str) -> list[BibEntry]:
        entries = []
        for m in self._ENTRY_RE.finditer(text):
            entry_type = m.group(1).lower()
            if entry_type in ("comment", "string", "preamble"):
                continue
            body = m.group(3)
            fields = self._parse_fields(body)
            year = None
            if fields.get("year"):
                ym = re.search(r"\d{4}", fields["year"])
                if ym:
                    year = int(ym.group(0))
            entries.append(BibEntry(
                title=self._clean(fields.get("title", "")),
                authors=self._format_authors(fields.get("author", "")),
                year=year,
                journal=self._clean(fields.get("journal") or fields.get("booktitle") or "") or None,
                doi=fields.get("doi") or None,
                abstract=self._clean(fields.get("abstract", "")) or None,
            ))
        return entries

    def _parse_fields(self, body: str) -> dict:
        fields = {}
        # Match: fieldname = {value}  OR  fieldname = "value"  OR fieldname = value,
        field_re = re.compile(
            r'(\w+)\s*=\s*(?:\{(.*?)\}|"(.*?)"|([^,\n]+))\s*,?',
            re.DOTALL,
        )
        for fm in field_re.finditer(body):
            name = fm.group(1).lower()
            value = fm.group(2) or fm.group(3) or fm.group(4) or ""
            fields[name] = value.strip()
        return fields

    def _clean(self, value: str) -> str:
        # Remove braces and collapse whitespace
        value = value.replace("{", "").replace("}", "")
        value = re.sub(r"\s+", " ", value).strip()
        return value

    def _format_authors(self, raw: str) -> str | None:
        if not raw:
            return None
        raw = self._clean(raw)
        # BibTeX authors separated by ' and '
        parts = [p.strip() for p in re.split(r"\s+and\s+", raw) if p.strip()]
        formatted = []
        for p in parts:
            if "," in p:
                last, first = p.split(",", 1)
                last = last.strip()
                # First-name initials
                initials = "".join(w[0] for w in first.strip().split() if w)
                formatted.append(f"{last} {initials}".strip())
            else:
                formatted.append(p.strip())
        return ", ".join(formatted) if formatted else None
