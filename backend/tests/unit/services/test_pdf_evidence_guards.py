"""Memory guards on the PDF evidence path (2026-07-23, check 46406547 outage).

One 7.8MB treaty PDF measured ~600MB RSS through the pypdf parse, and parses
ran under the shared 25-slot url-fetch semaphore — concurrent treaty-sized
parses OOM-killed the prod container (SIGKILL: no exception, no Sentry, check
stuck 'processing'). These tests lock the two guards:

  1. byte cap — oversize PDFs are skipped (content-length precheck AND
     mid-stream cap when the header lies/is absent), returning [] with a
     logged receipt, never buffered or parsed;
  2. parse serialisation — at most ONE PDF parse in flight module-wide,
     regardless of caller fan-out.
"""

import asyncio
from io import BytesIO
from unittest.mock import patch

import pytest

from app.services import pdf_evidence as mod
from app.services.pdf_evidence import MAX_PDF_BYTES, PDFEvidenceExtractor


class _FakeStreamResponse:
    def __init__(self, chunks, content_length=None, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.headers = (
            {"content-length": str(content_length)}
            if content_length is not None
            else {}
        )

    def raise_for_status(self):
        assert self.status_code == 200

    async def aiter_bytes(self):
        for c in self._chunks:
            yield c

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeClient:
    def __init__(self, response):
        self._response = response

    def stream(self, method, url):
        return self._response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _patched_client(response):
    return patch.object(mod.httpx, "AsyncClient", lambda **kw: _FakeClient(response))


@pytest.mark.asyncio
async def test_oversize_content_length_skipped_before_download():
    """A declared content-length over the cap returns [] without reading the body."""
    resp = _FakeStreamResponse(
        chunks=[b"x"],  # would be read if the precheck failed
        content_length=MAX_PDF_BYTES + 1,
    )
    with _patched_client(resp):
        out = await PDFEvidenceExtractor().extract_evidence_from_pdf(
            "https://example.gov/huge.pdf", "claim"
        )
    assert out == []


@pytest.mark.asyncio
async def test_midstream_cap_when_header_absent():
    """No content-length header: the streamed cap still stops an oversize body."""
    chunk = b"x" * (1024 * 1024)
    resp = _FakeStreamResponse(chunks=[chunk] * 21, content_length=None)  # 21MB
    with _patched_client(resp):
        out = await PDFEvidenceExtractor().extract_evidence_from_pdf(
            "https://example.gov/lying.pdf", "claim"
        )
    assert out == []


@pytest.mark.asyncio
async def test_under_cap_pdf_still_parsed():
    """A normal-size download proceeds to the (mocked) parse stage."""
    resp = _FakeStreamResponse(chunks=[b"%PDF-1.4 tiny"], content_length=13)
    with _patched_client(resp), patch.object(
        PDFEvidenceExtractor,
        "_extract_pdf_metadata",
        return_value={"title": "t", "total_pages": 1},
    ), patch.object(
        PDFEvidenceExtractor,
        "_search_pdf_for_claim",
        return_value=[{"text": "hit", "page_number": 1, "relevance_score": 1.0}],
    ):
        out = await PDFEvidenceExtractor().extract_evidence_from_pdf(
            "https://example.gov/ok.pdf", "claim", max_results=1
        )
    assert len(out) == 1 and out[0]["text"] == "hit"


@pytest.mark.asyncio
async def test_parse_serialised_module_wide():
    """Two concurrent extractions never overlap inside the parse section."""
    in_parse = 0
    max_in_parse = 0

    def slow_metadata(self, pdf_bytes):
        nonlocal in_parse, max_in_parse
        in_parse += 1
        max_in_parse = max(max_in_parse, in_parse)
        import time

        time.sleep(0.05)
        in_parse -= 1
        return {"title": "t", "total_pages": 1}

    resp_factory = lambda: _FakeStreamResponse(
        chunks=[b"%PDF-1.4 tiny"], content_length=13
    )
    with patch.object(
        mod.httpx, "AsyncClient", lambda **kw: _FakeClient(resp_factory())
    ), patch.object(
        PDFEvidenceExtractor, "_extract_pdf_metadata", slow_metadata
    ), patch.object(
        PDFEvidenceExtractor, "_search_pdf_for_claim", lambda *a: []
    ):
        await asyncio.gather(
            PDFEvidenceExtractor().extract_evidence_from_pdf(
                "https://example.gov/a.pdf", "claim"
            ),
            PDFEvidenceExtractor().extract_evidence_from_pdf(
                "https://example.gov/b.pdf", "claim"
            ),
            PDFEvidenceExtractor().extract_evidence_from_pdf(
                "https://example.gov/c.pdf", "claim"
            ),
        )
    assert max_in_parse == 1, f"parse overlap detected (max={max_in_parse})"
