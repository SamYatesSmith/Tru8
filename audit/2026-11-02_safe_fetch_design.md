# Safe outbound fetch (security sweep #2): design rev 2, BUILT

2026-11-02 · Status: DESIGN, for independent review before build.
Sweep record: `audit/2026-11-02_security_sweep.md`. Fetch-site inventory by an agent, 2026-11-02.

## Problem
Only user-submitted ingest (`safe_get`) validates the destination. These fetch URLs we did not choose, follow redirects unchecked, and store or show what they get:

| # | Site | URL source | Shown |
|---|---|---|---|
| 2 | `services/evidence.py:483` `_extract_from_page` | search results, Wikipedia external links, recovery | snippet/text on public `/r/` |
| 3 | `services/pdf_evidence.py:59` (stream, 20MB cap) | search-result PDFs | page snippets |
| 4 | `services/factcheck_api.py:193` | Fact Check API `claimReview.url` | 2000 chars as evidence |
| 5 | `services/article_reader.py:70` | `Evidence.url` (Compare) | Compare summary |
| 6 | `services/title_recovery.py:141` | Wayback API `closest.url` | title |

Attack: a page on a domain the attacker controls ranks for a claim, and our fetcher follows its 302 to `169.254.169.254`, `*.railway.internal` or `localhost:8000/metrics`. The response text lands in a public record.

Separately, `assert_public_url` resolves DNS, then the HTTP library resolves again on connect. A DNS-rebinding host passes the first lookup and connects to an internal address on the second.

## Constraint that shapes the design
The replay bench (`scripts/replay_bench/cassette.py`) patches **`httpx.AsyncClient.send` / `httpx.Client.send`** and keys a cassette by the FIRST request (method + URL minus secrets + body hash). Redirects are followed inside that one `send`.
- Following redirects hop by hop in our code, or rewriting URLs to IPs, would change the keys of every recorded fetch. Every corpus cassette would miss, forcing a paid re-record.
- **The fix must leave `AsyncClient.send` calls and their URLs unchanged.**

## Design: validate at the connection layer, not the request layer
httpx follows redirects inside `send`, issuing one transport request per hop. httpcore opens each TCP connection through a **network backend** (`connect_tcp(host, port, …)`).

A `SafeNetworkBackend` wraps httpcore's default async backend:
1. In `connect_tcp(host, port, …)`:
   - Refuse internal hostnames: `localhost`, `*.local`, `*.internal`, `*.railway.internal`, `*.localhost`.
   - Resolve the host once (`getaddrinfo` in a thread, or `anyio.getaddrinfo`).
   - Validate EVERY address with the existing `_ip_is_blocked`. If any is blocked, raise `UnsafeUrlError`.
   - Connect to the **validated IP** by calling the inner backend's `connect_tcp(ip, port, …)`.
2. TLS is unaffected: httpcore's `start_tls` uses the request's hostname for SNI and certificate checks, not the connect address. HTTPS still verifies against the real name.
3. Because this runs on EVERY connection, every redirect hop is validated: a new host means a new connection means a check. DNS rebinding is closed because we connect to the exact address we checked.

`safe_async_client(**kwargs) -> httpx.AsyncClient` builds an `httpx.AsyncHTTPTransport` whose pool uses this backend. It keeps the caller's own timeout, headers and `follow_redirects`.
- httpx 0.27 has no public `network_backend` argument, so we construct `httpcore.AsyncConnectionPool(network_backend=…)` and wrap it in a minimal `AsyncBaseTransport` that maps httpx requests to httpcore ones. Alternatively, set the private `_pool` of an `AsyncHTTPTransport`. **Review: pick one.** The second is less code; the first avoids a private attribute.
- **Proxies:** none are configured. `trust_env=False` on these clients, so an `HTTP(S)_PROXY` environment variable cannot route around the backend.

Sites #2–#6 replace `httpx.AsyncClient(…)` with `safe_async_client(…)`. Nothing else changes: same URLs, same `send` calls, same `follow_redirects`.

## Bench and tests
- **Replay:** cassettes patch `AsyncClient.send`, so the transport and backend never run and no DNS happens. Signatures are unchanged. **Expect `--all` equal to the control arm**, after a control run first (known noise: 93DD/B4A3/82CF).
- **Unit tests (real sockets, patched resolver):**
  1. A host resolving to `10.0.0.5`, `169.254.169.254`, `::1` or an IPv4-mapped private address is blocked before any connect.
  2. Mixed public and private answers are blocked.
  3. `*.railway.internal` is blocked without DNS.
  4. A local test server on 127.0.0.1, with the test allowing loopback for that port only, issues a 302 to `http://evil-internal.test/` that resolves to 10.x. The chain stops with `UnsafeUrlError`, and the first hop really was fetched.
  5. Rebinding: the resolver returns a public address then a private one on later calls. The connection goes to the validated IP, and the second lookup never happens per connection.
  6. HTTPS SNI still uses the hostname (inspect the `start_tls` `server_hostname` argument).
  7. Each site uses `safe_async_client` (source check), and behaviour is unchanged on a public URL (stubbed backend).
- **Failure handling:** `UnsafeUrlError` is a `ValueError`. Each site's existing `except Exception` handling (evidence falls back to the search snippet) applies.
  - Invariant 5 (every exclusion has a receipt): add a URL-ledger receipt `stage=unsafe_url` at the evidence and PDF sites, and a log line elsewhere.

## Out of scope (recorded)
- Ingest `safe_get` (`requests`) keeps resolving DNS twice, so its rebinding gap stays open. It needs the same idea on a `requests` adapter; next batch.
- Fixed-base API clients (search, LLMs, gov/academic adapters, legal) are not attacker-chosen hosts, though `government_api_client` follows redirects. A possible follow-up.
- Wayback save: archive.org fetches the target, not us.

## Risk
- **Pool behaviour:** pool settings change (limits, HTTP/2 off as today). Keep httpx defaults.
- **A legitimate site with an address in a blocked range:** essentially none publicly. The blocked list is unchanged from the reviewed F-SEC-02 list.
- **Latency:** one extra `getaddrinfo` per new connection, the same lookup the library did anyway, now done once.


## Review round 1 (independent, 2026-11-02): verdict "build after fixes"; all adopted
Library facts confirmed in source (httpcore 1.0.7, and 1.0.9 is identical in the pool/connection code):
- A new origin means a new connection, which means `connect_tcp(host=origin.host)`; there is no cross-host reuse and no HTTP/2 coalescing.
- Retries re-enter `connect_tcp`.
- Passing `transport=` disables env proxies.
- SNI is `sni_hostname or origin.host`.

1. **HIGH, client kwargs silently dropped with a custom transport.** `safe_async_client` accepts only `timeout`/`headers`/`follow_redirects`/`cookies` and raises `TypeError` otherwise. Tested.
2. **HIGH, single-IP connect would lose the cross-address fallback.** It now resolves once, validates ALL addresses, then tries each validated IP within the remaining timeout. Tested (dual-stack, first address unreachable).
3. **MEDIUM, wiring.** Replace `AsyncHTTPTransport._pool` with an explicit `AsyncConnectionPool` (verify on, HTTP/1.1, 100/20/5 s, retries 0, `trust_env=False`). A guard test pins the wiring.
4. **MEDIUM, replay vs record.** The cassette now replays a recorded `UnsafeUrlError` as `UnsafeUrlError`. Tested, mutation-checked.
5. **MEDIUM, failure path.** Each site catches `UnsafeUrlError` FIRST: the item is dropped with no snippet fallback, and `[URL LEDGER] dropped stage=unsafe_url url=… reason=…` is logged.
6. **MEDIUM, webhooks added** (pins the address; `safe_async_post`'s pre-check is kept).
7. **LOW:**
   - trailing-dot hostnames;
   - `2002::/16` added explicitly;
   - decimal/short IP literals are blocked on the resolved address (test skips on Windows' resolver);
   - no extra thread hop (`anyio.getaddrinfo` only);
   - tests that patch `httpx.AsyncClient` keep working (looked up at call time).

## Build (2026-11-02)
- `app/core/url_safety.py`: `SafeNetworkBackend`, `safe_async_client`, `_is_internal_hostname`.
- Sites switched (no raw `httpx.AsyncClient(` left in them):
  - `evidence.py`
  - `pdf_evidence.py`
  - `factcheck_api.py`, both calls
  - `article_reader.py`
  - `title_recovery.py`
  - `webhooks.py`
- Tests in `tests/unit/test_safe_fetch.py`:
  - backend unit tests;
  - DNS-rebinding pin;
  - fallback across addresses;
  - real local-server redirect chain stopped mid-chain;
  - TLS SNI keeps the hostname;
  - kwarg refusal;
  - wiring guard;
  - site source check.
- Cassette refusal-replay test added. 334 related tests pass.


## Verification (2026-11-02)
- **Replay bench `--all`:** 121/14/15/2 — the documented busy-machine baseline. The drifting claims (82CF, 93DD, B4A3) were checked alone:
  - 93DD is clean (14/1/2).
  - 82CF is the documented cross-process drift.
  - B4A3 drifts 2 misses with the change and **13 misses on the unchanged code across both control runs**, so the drift predates this work.
- **Independent verifier:** found no bypass. It also confirmed:
  - IPv6 bracket handling;
  - IDN reaching us as punycode;
  - decimal and hex hosts resolving and then being blocked;
  - no second DNS lookup after the check;
  - exception mapping;
  - pool closure;
  - no extra threads.
- **Verifier findings, fixed and each mutation-checked:**
  1. **MEDIUM:** a hanging first address ate the whole connect budget. Every address but the last is now capped (≤2 s, a fair share of what remains).
  2. **MEDIUM:** each client built two SSL contexts. One is now built and shared.
  3. **LOW:** the title-recovery refusal receipt never fired. `_recover_one` now re-raises `UnsafeUrlError`.
  - Site-level tests added: an evidence page dropped with its receipt, and the title-recovery receipt.
- **Unit suite:** 4,583 passed, 0 failed.
- **Note:** the safe client sets `trust_env=False`, so `SSL_CERT_FILE`/`SSL_CERT_DIR` are ignored for these fetches. Not set on Railway as far as is known.
