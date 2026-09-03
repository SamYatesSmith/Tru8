"""Oversize PDF bodies are stored as a stub and replayed by declared size.

WHY THIS EXISTS (2026-09-03)
---------------------------
The bench re-record on the Build A twin captured a 32.5 MB Gallagher Re PDF on
`TRU-5647-FA4F`. The pipeline never consumed it — the PDF guard in
`app/services/pdf_evidence.py` abandons any PDF over `MAX_PDF_BYTES` — but the
recorder buffers the whole body and stored 43 MB of base64, which gzips to a
30 MB blob (PDFs do not compress) that would have sat in git history for good.

The rule these tests pin:

    application/pdf AND len(body) > cap  -> stub: no body, `body_truncated_from`
    replay of a stub                     -> `content-length` = original size, body b""
    anything else                        -> stored whole, exactly as before

And the invariant that makes the stub behaviour-preserving: the bench cap must
never sit BELOW the pipeline's guard. If it did, a PDF between the two sizes
would be stubbed on record but accepted by the guard on replay, and the pipeline
would parse an empty document instead of the one it saw live.
"""

from __future__ import annotations

import httpx

from app.services.pdf_evidence import MAX_PDF_BYTES
from scripts.replay_bench.cassette import (
    _PDF_STUB_OVER_BYTES,
    _response_from_entry,
    _serialise_response,
)

_REQ = httpx.Request("GET", "https://example.org/report.pdf")


def _response(content_type: str, body: bytes) -> httpx.Response:
    return httpx.Response(
        200, headers={"content-type": content_type}, content=body, request=_REQ
    )


def test_bench_cap_never_below_the_pipeline_guard():
    assert _PDF_STUB_OVER_BYTES >= MAX_PDF_BYTES


def test_oversize_pdf_is_stored_as_a_stub():
    body = b"%PDF-" + b"\x00" * (_PDF_STUB_OVER_BYTES + 1 - 5)
    entry = _serialise_response(_response("application/pdf", body), body)

    assert entry["body_truncated_from"] == len(body)
    assert "body_b64" not in entry
    assert "body_text" not in entry
    assert entry["headers"]["content-type"] == "application/pdf"


def test_pdf_at_the_cap_is_stored_whole():
    body = b"\xff" * _PDF_STUB_OVER_BYTES  # invalid UTF-8: lands in body_b64
    entry = _serialise_response(_response("application/pdf", body), body)

    assert "body_truncated_from" not in entry
    assert "body_b64" in entry


def test_oversize_non_pdf_is_stored_whole():
    body = b"<html>" + b"a" * (_PDF_STUB_OVER_BYTES + 1)
    entry = _serialise_response(_response("text/html; charset=utf-8", body), body)

    assert "body_truncated_from" not in entry
    assert entry["body_text"] == body.decode("utf-8")


def test_stub_replays_with_the_original_size_declared_and_no_body():
    entry = {
        "status_code": 200,
        "headers": {"content-type": "application/pdf"},
        "body_truncated_from": 32_560_309,
    }
    resp = _response_from_entry(entry, _REQ)

    assert resp.status_code == 200
    assert int(resp.headers["content-length"]) == 32_560_309
    assert int(resp.headers["content-length"]) > MAX_PDF_BYTES
    assert resp.content == b""


def test_ordinary_entry_replays_unchanged():
    entry = {
        "status_code": 200,
        "headers": {"content-type": "text/html", "content-length": "5"},
        "body_text": "hello",
    }
    resp = _response_from_entry(entry, _REQ)

    assert resp.content == b"hello"
    # content-length is dropped on replay so httpx derives it from the body.
    assert resp.headers.get("content-length") in (None, "5")
