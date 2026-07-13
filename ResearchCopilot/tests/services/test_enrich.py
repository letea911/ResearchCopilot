import pytest
from unittest.mock import AsyncMock
from dataclasses import dataclass
from services.enrich import MetadataEnricher


@dataclass
class FakeDoc:
    id: str
    title: str
    doi: str | None = None


@pytest.mark.asyncio
async def test_enrich_matches_by_title(tmp_path):
    bib = tmp_path / "test.bib"
    bib.write_text('''@article{k, title={A Study of High Entropy LDH}, author={Smith, John}, year={2024}, journal={Nature}}''', encoding="utf-8")

    meta = AsyncMock()
    meta.list_documents.return_value = [
        FakeDoc(id="doc-1", title="A Study of High Entropy LDH"),
        FakeDoc(id="doc-2", title="Something Unrelated"),
    ]
    enricher = MetadataEnricher(meta)
    result = await enricher.enrich_from_bib(bib)
    assert result["matched"] == 1
    assert result["updated"] == 1
    meta.update_document_metadata.assert_awaited()


@pytest.mark.asyncio
async def test_enrich_no_match(tmp_path):
    bib = tmp_path / "test.bib"
    bib.write_text('''@article{k, title={Completely Different Topic XYZ}, author={A, B}, year={2024}}''', encoding="utf-8")
    meta = AsyncMock()
    meta.list_documents.return_value = [FakeDoc(id="doc-1", title="A Study of High Entropy LDH")]
    enricher = MetadataEnricher(meta)
    result = await enricher.enrich_from_bib(bib)
    assert result["matched"] == 0
    assert len(result["unmatched"]) == 1
