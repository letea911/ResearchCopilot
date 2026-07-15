"""AI-powered literature classifier — extracts keywords, abstract, and
suggests which library (collection) a paper belongs to."""
import json

from models.message import ChatMessage, Role
from providers.interfaces import BaseLLMProvider
from services.interfaces import BaseClassifierService
from services.models import ClassifyResult
from storage.interfaces import BaseMetadataStore


CLASSIFY_SYSTEM = (
    "You are a scientific paper classifier specializing in computational "
    "chemistry, materials science, and catalysis. Analyze the paper and "
    "return ONLY valid JSON, no other text."
)

CLASSIFY_USER_TEMPLATE = """Paper title: {title}
Authors: {authors}
Library hierarchy (parent → sub-library):
{collections}

Full text:
{chunks_text}

Return a JSON object with these keys:
- "keywords": list of 3-5 relevant scientific keywords
- "abstract": concise 2-3 sentence summary of the paper
- "suggested_parent": best-matching root library name (e.g. "电催化"), or "" if none fit
- "suggested_collection": best-matching sub-library name (e.g. "高熵"), or "" if none fit
- "new_parent": suggested new root library name if no existing parent fits, or ""
- "new_collection": suggested new sub-library name (under parent or standalone), or ""
- "confidence": number between 0.0 and 1.0

Rules:
- Prefer placing papers in EXISTING sub-libraries when possible (fill suggested_parent + suggested_collection)
- If the paper fits under an existing parent but needs a NEW sub-library, set suggested_parent="" and fill new_parent + new_collection
- If no existing library fits at all, fill new_parent + new_collection
- Leave new_* fields empty when existing libraries suffice
- Prefer specific sub-libraries over generic ones"""


class ClassifierService(BaseClassifierService):
    """AI classifier that reads full text and returns structured metadata."""

    def __init__(self, llm: BaseLLMProvider, meta_store: BaseMetadataStore):
        self._llm = llm
        self._meta_store = meta_store

    async def classify_single(self, document_id: str) -> ClassifyResult:
        doc = await self._meta_store.get_document(document_id)
        if doc is None:
            return ClassifyResult(
                document_id=document_id,
                keywords=[],
                abstract="",
                suggested_collection="",
                new_collection="",
                confidence=0.0,
            )

        chunks = await self._meta_store.get_chunks_by_document(document_id)
        # Take first ~4000 chars (roughly 1000 tokens) so the LLM has enough
        # context without exceeding reasonable limits.
        chunks_text = "\n\n---\n\n".join(c.content for c in chunks)
        if len(chunks_text) > 6000:
            chunks_text = chunks_text[:6000]

        tree = await self._meta_store.get_collection_tree()
        # Format hierarchy for the prompt: "电催化 → 高熵\n电催化 → OER\n默认库"
        lines = []
        for node in tree:
            if node["children"]:
                for child in node["children"]:
                    lines.append(f"  {node['name']} → {child}")
            else:
                lines.append(f"  {node['name']}")
        collections_display = "\n".join(lines) if lines else "  默认库"

        prompt = CLASSIFY_USER_TEMPLATE.format(
            title=doc.title or "Unknown",
            authors=doc.authors or "Unknown",
            collections=collections_display,
            chunks_text=chunks_text,
        )

        messages = [
            ChatMessage(role=Role.SYSTEM, content=CLASSIFY_SYSTEM),
            ChatMessage(role=Role.USER, content=prompt),
        ]

        response = await self._llm.chat(messages, temperature=0.0, max_tokens=400)

        parsed = self._parse_json(response)
        return ClassifyResult(
            document_id=document_id,
            keywords=list(parsed.get("keywords", []) or []),
            abstract=str(parsed.get("abstract", "") or ""),
            suggested_collection=str(parsed.get("suggested_collection", "") or ""),
            new_collection=str(parsed.get("new_collection", "") or ""),
            suggested_parent=str(parsed.get("suggested_parent", "") or ""),
            new_parent=str(parsed.get("new_parent", "") or ""),
            confidence=float(parsed.get("confidence", 0.0) or 0.0),
        )

    async def classify_batch(
        self, document_ids: list[str]
    ) -> list[ClassifyResult]:
        results = []
        for doc_id in document_ids:
            try:
                result = await self.classify_single(doc_id)
                results.append(result)
            except Exception:
                results.append(ClassifyResult(
                    document_id=doc_id,
                    keywords=[], abstract="",
                    suggested_collection="", new_collection="",
                    confidence=0.0,
                ))
        return results

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Parse LLM JSON output, stripping markdown fences if present."""
        text = text.strip()
        if text.startswith("```"):
            # Strip opening fence: ```json or ```
            lines = text.split("\n")
            if lines and "```" in lines[0]:
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Last resort: try to find a JSON object with regex
            import re
            m = re.search(r"\{.*\}", text, re.DOTALL)
            if m:
                return json.loads(m.group())
            return {}
