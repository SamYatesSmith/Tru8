"""Deterministic HTTP record/replay for the replay bench (a "cassette").

Every external call in the pipeline rides ``httpx.AsyncClient`` — web search
(``app/services/search.py``), all API adapters (``app/services/api_adapters/*``),
Gemini (``app/services/google_ai.py`` uses the REST/httpx transport) and OpenAI
(``openai.AsyncOpenAI`` runs on httpx under the hood). That single chokepoint is
what makes a *deterministic* bench possible: patch ``httpx.AsyncClient.send`` for
the duration of one bench claim and the entire non-deterministic surface — search
provider drift AND LLM variance — is frozen at once.

Three modes
-----------
- **record**: requests go live; each request/response pair is captured and, on
  exit, written to the claim's ``cassette.json`` (secrets scrubbed first).
- **replay**: requests are served from the cassette. A miss is a *hard error*
  naming the unmatched request — that surfaces real drift (e.g. a prompt that
  changed shape) instead of silently falling back to the live network.
- **patch**: replay, but a miss goes LIVE and is APPENDED to the cassette.
  Needed because record-time request construction can differ from replay-time
  for calls whose prompt embeds upstream-merge ordering (the evidence-mapping
  prompt: live network latencies order the web∥api merge differently than
  instant replay does). Replay-vs-replay is byte-deterministic (verified), so
  one patch pass after recording completes the cassette permanently.

Why a miss is fatal in replay
------------------------------
With the LLM frozen, extraction is deterministic, so the search queries it
produces are byte-identical run-to-run, so the search requests match the
cassette, and so on down the chain. If a request *doesn't* match, the pipeline's
own behaviour changed — exactly the signal the bench exists to catch.

Matching key
------------
``METHOD scheme://host/path?<sorted non-secret query>\n<sha256(body)>``. Secret
query params and auth headers are excluded from the key (and scrubbed from disk),
so a rotated API key never invalidates a cassette and no key is ever committed.

Date normalisation (2026-07-02)
-------------------------------
Three pipeline prompts embed the wall-clock date (extract.py x2,
article_classifier.py, query_planner.py). Un-normalised, their body hashes
drifted DAILY, so every cassette recorded before "today" missed — and the
miss was swallowed by extract's heuristic fallback, silently collapsing the
whole bench (~2 weeks undetected). ``_normalise_body_for_signature`` rewrites
those exact boilerplates to fixed tokens before hashing. Add any NEW
date-embedding prompt boilerplate to ``_DATE_BOILERPLATE_PATTERNS``.
Deliberately NOT normalised: ISO dates in URL query params (e.g. climate
adapters' date windows) — collapsing those could alias two legitimately
different requests; if they drift, the loud miss report names them.
"""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
import re
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode

import httpx


# Query-string params and headers that carry credentials. Excluded from the
# matching signature AND redacted before anything touches disk.
_SECRET_QUERY_KEYS = {
    "key",
    "api_key",
    "apikey",
    "apiKey",
    "token",
    "access_token",
    "subscription_token",
    "app_id",
    "app_key",
}
_SECRET_HEADER_KEYS = {
    "authorization",
    "x-api-key",
    "x-subscription-token",
    "x-goog-api-key",
    "api-key",
    "ocp-apim-subscription-key",
}
_REDACTED = "__REDACTED__"

# Response headers worth preserving on replay. We deliberately do NOT keep
# content-encoding or content-length: ``response.aread()`` returns the *decoded*
# body, so replaying the original gzip/br/zstd header would make httpx try to
# decompress already-decompressed bytes (corrupting every compressed response),
# and a stale content-length would mismatch the stored body. Everything else
# (Date, Set-Cookie, rate-limit counters, CF-Ray, ...) is volatile noise.
_KEEP_RESPONSE_HEADERS = {"content-type"}
# Stripped from replayed responses even if a cassette predates the rule above.
_DROP_ON_REPLAY = {"content-encoding", "content-length", "transfer-encoding"}


# Wall-clock-date boilerplates embedded in pipeline prompts. Normalised to
# fixed tokens before hashing so a cassette recorded on day X still matches
# on day Y. Keep patterns EXACT — over-broad date scrubbing could alias two
# genuinely different requests (see module docstring).
_DATE_BOILERPLATE_PATTERNS = [
    # extract.py:419/581 + article_classifier.py:805
    (
        re.compile(r"Today's date is \d{4}-\d{2}-\d{2} \(Year: \d{4}\)\."),
        "Today's date is <TODAY> (Year: <YR>).",
    ),
    # query_planner.py:310
    (
        re.compile(r"TODAY'S DATE: \d{4}-\d{2}-\d{2} \(CURRENT YEAR: \d{4}\)"),
        "TODAY'S DATE: <TODAY> (CURRENT YEAR: <YR>)",
    ),
]


def _normalise_body_for_signature(body: bytes) -> bytes:
    """Rewrite known date boilerplates to fixed tokens (signature only —
    stored bodies are untouched). Non-UTF-8 bodies pass through unchanged."""
    if not body:
        return body
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError:
        return body
    for pattern, replacement in _DATE_BOILERPLATE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.encode("utf-8")


def _canonical_signature(request: httpx.Request) -> str:
    """Stable identity for a request, independent of credentials, header
    order, and the wall-clock date boilerplates in pipeline prompts."""
    url = request.url
    safe_query = [
        (k, v)
        for k, v in parse_qsl(url.query.decode("ascii"), keep_blank_values=True)
        if k not in _SECRET_QUERY_KEYS
    ]
    safe_query.sort()
    query = urlencode(safe_query)

    body = request.content or b""
    body_hash = hashlib.sha256(_normalise_body_for_signature(body)).hexdigest()

    base = f"{request.method} {url.scheme}://{url.host}{url.path}"
    if query:
        base = f"{base}?{query}"
    return f"{base}\n{body_hash}"


def _redact_url(request: httpx.Request) -> str:
    """URL string with secret query params blanked, for human-readable storage."""
    url = request.url
    pairs = [
        (k, _REDACTED if k in _SECRET_QUERY_KEYS else v)
        for k, v in parse_qsl(url.query.decode("ascii"), keep_blank_values=True)
    ]
    rebuilt = url.copy_with(query=urlencode(pairs).encode("ascii"))
    return str(rebuilt)


def _serialise_response(response: httpx.Response, body: bytes) -> Dict[str, Any]:
    headers = {
        k: v for k, v in response.headers.items() if k.lower() in _KEEP_RESPONSE_HEADERS
    }
    try:
        text = body.decode("utf-8")
        return {
            "status_code": response.status_code,
            "headers": headers,
            "body_text": text,
        }
    except UnicodeDecodeError:
        return {
            "status_code": response.status_code,
            "headers": headers,
            "body_b64": base64.b64encode(body).decode("ascii"),
        }


def _deserialise_body(entry: Dict[str, Any]) -> bytes:
    if "body_b64" in entry:
        return base64.b64decode(entry["body_b64"])
    return entry.get("body_text", "").encode("utf-8")


class CassetteMiss(RuntimeError):
    """Raised in replay mode when a request has no recorded counterpart."""


class HttpxCassette:
    """Context manager that records or replays all ``httpx.AsyncClient`` traffic.

    Patches the class-level ``send`` so every client instance — including the
    ones openai / google-ai create internally — is captured, without editing any
    adapter. Restores the original on exit.
    """

    # The genuine method, saved across nested/concurrent uses via a refcount so
    # we never double-patch or restore early.
    _orig_send = None
    _depth = 0
    _patch_lock = threading.Lock()

    def __init__(self, cassette_path: Path, mode: str) -> None:
        if mode not in ("record", "replay", "patch"):
            raise ValueError(
                f"mode must be 'record', 'replay' or 'patch', got {mode!r}"
            )
        self.cassette_path = cassette_path
        self.mode = mode
        self._lock = threading.Lock()
        # sig -> list of serialised responses (FIFO across repeated identical calls)
        self._recorded: Dict[str, List[Dict[str, Any]]] = {}
        self._replay_cursor: Dict[str, int] = {}
        self._miss_count = 0
        self._hit_count = 0
        self._patched_count = 0

    # -- lifecycle ---------------------------------------------------------

    def __enter__(self) -> "HttpxCassette":
        if self.mode in ("replay", "patch"):
            self._load()
        cassette = self

        async def _patched_send(client, request, **kwargs):  # type: ignore[no-untyped-def]
            return await cassette._handle(client, request, **kwargs)

        with HttpxCassette._patch_lock:
            if HttpxCassette._depth == 0:
                HttpxCassette._orig_send = httpx.AsyncClient.send
                httpx.AsyncClient.send = _patched_send  # type: ignore[assignment]
            HttpxCassette._depth += 1
        return self

    def __exit__(self, *_exc) -> None:
        with HttpxCassette._patch_lock:
            HttpxCassette._depth -= 1
            if HttpxCassette._depth == 0 and HttpxCassette._orig_send is not None:
                httpx.AsyncClient.send = HttpxCassette._orig_send  # type: ignore[assignment]
                HttpxCassette._orig_send = None
        if self.mode == "record" or (self.mode == "patch" and self._patched_count):
            self._dump()

    # -- request handling --------------------------------------------------

    async def _handle(self, client, request: httpx.Request, **kwargs):  # type: ignore[no-untyped-def]
        sig = _canonical_signature(request)
        if self.mode == "replay":
            return self._replay(sig, request)
        if self.mode == "patch":
            try:
                return self._replay(sig, request)
            except CassetteMiss:
                # Go live for just this request and append it to the cassette
                # so subsequent pure-replay runs are complete.
                self._patched_count += 1
                return await self._record(client, sig, request, **kwargs)
        return await self._record(client, sig, request, **kwargs)

    async def _record(self, client, sig: str, request: httpx.Request, **kwargs):  # type: ignore[no-untyped-def]
        assert HttpxCassette._orig_send is not None
        try:
            response = await HttpxCassette._orig_send(client, request, **kwargs)
        except httpx.HTTPError as exc:
            # Record transport failures too (timeouts, refused connections):
            # otherwise a URL that fails live is never captured, and replay
            # misses on it forever (e.g. hard-blocking hosts like WaPo).
            # Replay re-raises an equivalent exception — same pipeline path.
            entry = {
                "_exception": type(exc).__name__,
                "_url": _redact_url(request),
                "_method": request.method,
            }
            with self._lock:
                self._recorded.setdefault(sig, []).append(entry)
            raise
        body = await response.aread()  # buffers content; response stays usable
        entry = _serialise_response(response, body)
        entry["_url"] = _redact_url(request)
        entry["_method"] = request.method
        with self._lock:
            self._recorded.setdefault(sig, []).append(entry)
        return response

    def _replay(self, sig: str, request: httpx.Request) -> httpx.Response:
        with self._lock:
            entries = self._recorded.get(sig)
            if not entries:
                self._miss_count += 1
                raise CassetteMiss(
                    f"no recorded response for: {request.method} {_redact_url(request)}\n"
                    f"signature={sig!r}\n"
                    f"cassette={self.cassette_path} ({len(self._recorded)} sigs). "
                    f"Re-record with --record if the pipeline legitimately changed."
                )
            idx = self._replay_cursor.get(sig, 0)
            # Reuse the last recorded response once identical calls are exhausted
            # (e.g. retries / repeated identical queries) rather than miss.
            entry = entries[min(idx, len(entries) - 1)]
            self._replay_cursor[sig] = idx + 1
            self._hit_count += 1
        if "_exception" in entry:
            # Recorded transport failure — replay it as an equivalent error so
            # the pipeline takes the same fetch-failed path deterministically.
            exc_cls = getattr(httpx, entry["_exception"], httpx.ConnectError)
            raise exc_cls(f"replayed {entry['_exception']} for {entry.get('_url')}")
        headers = {
            k: v
            for k, v in entry.get("headers", {}).items()
            if k.lower() not in _DROP_ON_REPLAY
        }
        return httpx.Response(
            status_code=entry["status_code"],
            headers=headers,
            content=_deserialise_body(entry),
            request=request,
        )

    # -- persistence -------------------------------------------------------

    def _load(self) -> None:
        if not self.cassette_path.exists():
            raise FileNotFoundError(
                f"cassette not found: {self.cassette_path}. "
                f"Record it first: python scripts/replay_bench.py --claim <ID> --record"
            )
        if self.cassette_path.suffix == ".gz":
            with gzip.open(self.cassette_path, "rt", encoding="utf-8") as fh:
                data = json.load(fh)
        else:
            data = json.loads(self.cassette_path.read_text(encoding="utf-8"))
        self._recorded = data.get("interactions", {})

    def _dump(self) -> None:
        self.cassette_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_comment": "Deterministic HTTP cassette for the replay bench. "
            "Secrets scrubbed. Re-record with scripts/replay_bench.py --record.",
            "interactions": self._recorded,
        }
        text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
        if self.cassette_path.suffix == ".gz":
            with gzip.open(self.cassette_path, "wt", encoding="utf-8") as fh:
                fh.write(text)
        else:
            self.cassette_path.write_text(text, encoding="utf-8")

    @property
    def stats(self) -> Dict[str, int]:
        return {
            "signatures": len(self._recorded),
            "hits": self._hit_count,
            "misses": self._miss_count,
            "patched": self._patched_count,
        }
