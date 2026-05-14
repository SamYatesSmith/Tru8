"""Runtime probe: hit every endpoint without auth and check the status.

Protected endpoints must return 401 or 403.
Public endpoints (health/verify/waitlist/discovery) can return anything 2xx-4xx.
DEBUG-gated test endpoints must return 404 when DEBUG=false.
"""

from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path

os.environ["DEBUG"] = "false"
os.environ.setdefault("ENVIRONMENT", "test")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from httpx import ASGITransport, AsyncClient  # noqa: E402

from main import app  # noqa: E402


PUBLIC_PATHS = {
    "/",
    "/api/v1/health/",
    "/api/v1/health/ready",
    "/api/v1/health/cache-metrics",
    "/api/v1/health/circuit-breakers",
    "/api/v1/health/email-config",
    "/api/v1/waitlist",
    "/api/v1/checks/public/{check_id}",
    "/api/v1/agent/health",
    "/api/v1/agent/tiers",
    "/verify/{check_id}",
    "/.well-known/mcp/server-card.json",
    "/llms.txt",
    "/api/openapi.json",
    "/api/docs",
    "/api/redoc",
}

# Stripe webhook verifies signature inside the handler (not via Depends),
# so an unauthenticated request lands in the handler and returns 400 for
# missing signature. We treat 400 as expected here.
WEBHOOK_PATHS = {"/api/v1/payments/webhook"}

DEBUG_GATED_PREFIX = "/api/v1/checks/test"

# Mounted ASGI sub-app — not a route we can probe by method.
SKIP_PATHS = {"/metrics"}

PARAM_RE = re.compile(r"\{[^}]+\}")
DUMMY_UUID = "00000000-0000-0000-0000-000000000000"


def fill_path_params(path: str) -> str:
    return PARAM_RE.sub(DUMMY_UUID, path)


def collect_routes():
    out = []
    for r in app.routes:
        path = getattr(r, "path", None)
        methods = getattr(r, "methods", None)
        if not path or not methods:
            continue
        if path in SKIP_PATHS:
            continue
        for m in methods:
            if m in ("HEAD", "OPTIONS"):
                continue
            out.append((m, path))
    return out


def expected_status(method: str, path: str) -> str:
    if path in PUBLIC_PATHS:
        return "public"
    if path in WEBHOOK_PATHS:
        return "webhook"
    if path.startswith(DEBUG_GATED_PREFIX):
        return "debug-gated"
    return "protected"


def status_ok(category: str, code: int) -> bool:
    if category == "protected":
        return code in (401, 403)
    if category == "debug-gated":
        return code == 404
    if category == "webhook":
        # Missing signature -> 400; some impls 401. Either is fine.
        return code in (400, 401, 403)
    if category == "public":
        # 200 ideal; 404 acceptable for /verify/{id} with bogus id;
        # 422 acceptable for /waitlist if body required;
        # 405 if method not allowed (we tested every declared method, but
        # some routes share path with different methods).
        return code < 500 and code not in (401, 403)
    return False


async def probe():
    routes = collect_routes()
    results = []
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://probe"
    ) as client:
        for method, path in routes:
            url = fill_path_params(path)
            try:
                # Send empty JSON for body-bearing methods so we don't trip
                # framework-level body parsing before auth runs.
                kwargs = {}
                if method in ("POST", "PUT", "PATCH", "DELETE"):
                    kwargs["json"] = {}
                resp = await client.request(method, url, **kwargs)
                code = resp.status_code
            except Exception as e:  # noqa: BLE001
                code = -1
                results.append((method, path, "EXC", str(e)[:80]))
                continue
            cat = expected_status(method, path)
            ok = status_ok(cat, code)
            results.append((method, path, cat, code, ok))
    return results


def main():
    results = asyncio.run(probe())
    failures = [r for r in results if len(r) == 5 and not r[4]]
    exceptions = [r for r in results if len(r) == 4 and r[2] == "EXC"]

    print(f"\nProbed {len(results)} routes\n")

    by_cat = {}
    for r in results:
        if len(r) != 5:
            continue
        cat = r[2]
        by_cat.setdefault(cat, {"pass": 0, "fail": 0})
        by_cat[cat]["pass" if r[4] else "fail"] += 1

    print("Summary by category:")
    for cat, counts in sorted(by_cat.items()):
        print(f"  {cat:14s}  pass={counts['pass']:3d}  fail={counts['fail']:3d}")
    print()

    if failures:
        print("FAILURES (status not in expected set):")
        for method, path, cat, code, _ in failures:
            print(f"  [{cat:11s}] {method:6s} {path}  -> {code}")
        print()

    if exceptions:
        print("EXCEPTIONS:")
        for method, path, _, msg in exceptions:
            print(f"  {method:6s} {path}  -> {msg}")
        print()

    if not failures and not exceptions:
        print(
            "ALL OK — every protected endpoint returned 401/403, every "
            "DEBUG-gated test endpoint returned 404, and every public "
            "endpoint returned a non-auth-error response."
        )
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
