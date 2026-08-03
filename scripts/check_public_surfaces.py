#!/usr/bin/env python3
"""Assert the public surfaces a stranger actually touches are alive and real.

Why this exists
---------------
On 2026-08-03 the sample evidence report linked from the homepage hero, the
closing CTA and /compare had been dead for an unknown length of time. It
returned **HTTP 200** carrying the text "Report Not Found", so:

  * no uptime monitor treated it as an outage — 200 is 200;
  * search engines indexed it as a valid page;
  * and it was the ONLY way to evaluate the product without signing up.

A status-code check would not have caught it. This script therefore asserts on
CONTENT as well as status: a page is healthy when it contains what it is
supposed to contain, not merely when it responds.

Usage
-----
    python scripts/check_public_surfaces.py
    python scripts/check_public_surfaces.py --base https://staging.example.com

Exits non-zero if any check fails, so it can gate a scheduled workflow.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import List, Optional

DEFAULT_WEB = "https://www.trueight.com"
DEFAULT_API = "https://api.trueight.com"
TIMEOUT = 30

# Kept in step with web/lib/marketing.ts::SAMPLE_REPORT_PATH.
# If you repoint the sample, repoint it here too — that is the whole point.
SAMPLE_REPORT_PATH = "/r/TRU-8723-1E97"


@dataclass
class Check:
    name: str
    url: str
    expect_status: int = 200
    must_contain: List[str] = field(default_factory=list)
    must_not_contain: List[str] = field(default_factory=list)
    why: str = ""


def _fetch(url: str):
    req = urllib.request.Request(url, headers={"User-Agent": "tru8-surface-check"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")
    except Exception as exc:  # noqa: BLE001 — any failure is a failed check
        return None, str(exc)


def run(checks: List[Check]) -> int:
    failures = 0
    for check in checks:
        status, body = _fetch(check.url)
        problems: List[str] = []

        if status != check.expect_status:
            problems.append(f"status {status}, expected {check.expect_status}")

        if status is not None:
            for needle in check.must_contain:
                if needle.lower() not in body.lower():
                    problems.append(f"missing expected content: {needle!r}")
            for needle in check.must_not_contain:
                if needle.lower() in body.lower():
                    problems.append(f"contains forbidden content: {needle!r}")

        if problems:
            failures += 1
            print(f"FAIL  {check.name}\n      {check.url}")
            for problem in problems:
                print(f"      - {problem}")
            if check.why:
                print(f"      why it matters: {check.why}")
        else:
            print(f"ok    {check.name}")

    print()
    print(f"{len(checks) - failures}/{len(checks)} surfaces healthy")
    return 1 if failures else 0


def build_checks(web: str, api: str) -> List[Check]:
    return [
        Check(
            name="API health",
            url=f"{api}/api/v1/health/",
            must_contain=["healthy"],
            why="the pipeline is unreachable; every check will fail",
        ),
        Check(
            name="Homepage",
            url=web,
            must_contain=["evidence"],
            why="the front door is down",
        ),
        Check(
            name="Pricing",
            url=f"{web}/pricing",
            must_contain=["Console"],
            why="nobody can see what to buy",
        ),
        Check(
            name="Sample report (the demo a stranger evaluates)",
            url=f"{web}{SAMPLE_REPORT_PATH}",
            must_not_contain=["Report Not Found", "Page not found"],
            why=(
                "this is the only no-signup evaluation path, linked from the "
                "hero, the closing CTA and /compare — a dead one silently wastes "
                "every pound of acquisition spend"
            ),
        ),
        Check(
            name="Sample report API record still exists",
            url=f"{api}/api/v1/checks/public/{SAMPLE_REPORT_PATH.rsplit('/', 1)[-1]}",
            must_contain=["claims"],
            why="the underlying check was deleted or never existed",
        ),
        Check(
            name="Unknown report returns a real 404",
            url=f"{web}/r/TRU-0000-0000",
            expect_status=404,
            why=(
                "a soft 404 (200 carrying not-found content) is invisible to "
                "monitoring and gets indexed by search engines"
            ),
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default=DEFAULT_WEB, help="web base URL")
    parser.add_argument("--api", default=DEFAULT_API, help="API base URL")
    args = parser.parse_args()

    web = args.base.rstrip("/")
    api = args.api.rstrip("/")
    print(f"Checking public surfaces: {web} / {api}\n")
    return run(build_checks(web, api))


if __name__ == "__main__":
    sys.exit(main())
