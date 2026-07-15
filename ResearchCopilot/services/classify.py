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
    "chemistry, materials science, and catalysis. You work in TWO STEPS:\n"
    "STEP 1 — Read the paper and identify its core research topics. "
    "Extract precise keywords and write a concise abstract.\n"
    "STEP 2 — Compare those keywords against the available library names. "
    "The best library is the one whose NAME best matches the paper's "
    "research TOPIC, MATERIAL SYSTEM, or METHOD. Think about semantic "
    "similarity: '电催化' matches electrocatalysis/OER/HER/ORR papers; "
    "'高熵' matches high-entropy alloy/oxide papers; 'DFT' matches "
    "density functional theory / first-principles papers.\n"
    "Always return ONLY valid JSON, no other text."
)

CLASSIFY_USER_TEMPLATE = """TASK: Classify this paper by first understanding it, then matching to libraries.

=== PAPER INFO ===
Title: {title}
Authors: {authors}

=== FULL TEXT ===
{chunks_text}

=== AVAILABLE LIBRARIES ===
(specific libraries first — pick from these whenever possible)
{collections}

=== STEP-BY-STEP INSTRUCTIONS ===

STEP 1 — UNDERSTAND THE PAPER
Read the full text. Identify:
- What is the MAIN research topic? (e.g. OER electrocatalysis, DFT calculations, catalyst synthesis)
- What MATERIAL SYSTEM is studied? (e.g. LDH, high-entropy oxides, perovskites, MOFs)
- What METHOD is used? (e.g. experiment, DFT, machine learning, EXAFS)

Based on your understanding, determine:
- "keywords": 4-6 precise keywords that capture the paper's topic, material, method
- "abstract": 2-3 sentence summary of what was studied and found

STEP 2 — MATCH KEYWORDS TO LIBRARIES
Look at the AVAILABLE LIBRARIES above. Compare your keywords to each library name:
- "电催化" ← matches papers about electrocatalysis, OER, HER, ORR, fuel cells, electrolysis
- "高熵" ← matches papers about high-entropy alloys/oxides/nitrides
- "DFT" ← matches papers using density functional theory, first-principles, VASP
- "原位" / "in-situ" ← matches papers about in-situ/operando characterization
- "合成" ← matches papers about material synthesis methods

Which library name has the STRONGEST semantic overlap with your keywords? That's your recommendation.

STEP 3 — OUTPUT JSON
Return ONLY this JSON (no other text):
{{
  "keywords": ["keyword1", "keyword2", ...],
  "abstract": "2-3 sentence summary...",
  "suggested_parent": "best-matching root library name, or empty string",
  "suggested_collection": "best-matching sub-library name, or empty string",
  "new_parent": "suggested new root library ONLY if no existing one fits, else empty string",
  "new_collection": "suggested new sub-library ONLY if needed, else empty string",
  "confidence": 0.0-1.0
}}

CRITICAL RULES:
- The keywords you extract in Step 1 MUST drive your library choice in Step 2.
- If your keywords are ["oxygen evolution reaction", "LDH", "electrocatalysis"], the library should be related to 电催化 or OER, NOT 临时库.
- Libraries marked ⚠ are LAST RESORT. Using them means no specific library matched your keywords.
- Set confidence based on keyword-library overlap: strong overlap → 0.8+, weak → 0.4-0.6, forced generic → ≤0.3.
- Only suggest new libraries (new_parent/new_collection) if the paper's topic has ZERO overlap with ALL existing libraries."""



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
        # Format hierarchy for the prompt.
        # Mark generic libraries so the LLM treats them as LAST RESORT.
        GENERIC = {"默认库", "临时库", "general", "default", "temp", "临时", "默认"}
        specific = []
        generic = []
        for node in tree:
            is_generic_root = node["name"] in GENERIC
            for child in node.get("children", []):
                if is_generic_root or child in GENERIC:
                    generic.append(f"  {node['name']} → {child}  ⚠ LAST RESORT")
                else:
                    specific.append(f"  {node['name']} → {child}")
            if not node["children"]:
                if is_generic_root:
                    generic.append(f"  {node['name']}  ⚠ LAST RESORT — avoid if possible")
                else:
                    specific.append(f"  {node['name']}")
        # Specific libraries first, then generic ones at the bottom
        all_lines = specific + generic
        collections_display = "\n".join(all_lines) if all_lines else "  默认库  ⚠ LAST RESORT — avoid if possible"

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
