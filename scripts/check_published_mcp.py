#!/usr/bin/env python3
"""Does the MCP package we PUBLISH actually run for a new user?

WHY THIS EXISTS
---------------
On 2026-08-04 `pip install tru8-mcp` had been failing with
`ModuleNotFoundError: No module named 'mcp.server.fastmcp'` for an unknown
number of days, while Tru8 was listed on the official MCP registry. Every
developer who followed that listing hit a dead end.

Nothing caught it, and three separate things that look like they should have,
did not:

  * The repo was fine. The break was in the *published* artefact's dependency
    metadata (`mcp>=1.0.0` resolving to mcp 2.0.0, which removed the module
    the server imports). Testing the working tree can never see this.
  * The unit tests skipped. `tests/unit/test_mcp_server.py` opens with
    `pytest.importorskip("mcp.server.fastmcp")`, added for the OPPOSITE
    problem (mcp too old) — it silently absorbed mcp being too new.
  * The developer machine had a working mcp already installed, so it ran
    locally right up until it was published.

The only check that can catch this class is the one performed here: install
the published package, in an environment that has nothing else in it, and
make it speak.

WHAT IT ASSERTS
---------------
1. `pip install tru8-mcp` resolves and installs — no version pin, because a
   new user does not pin either. Dependency drift is the failure mode.
2. The server starts and completes an MCP `initialize` handshake.
3. `tools/list` returns the tools we advertise.

Run locally:  python scripts/check_published_mcp.py
In CI:        .github/workflows/production-health.yml (twice daily)

Standard library only, so this monitor cannot itself fail on a dependency.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path

PACKAGE = "tru8-mcp"
MODULE = "tru8_mcp"
EXPECTED_TOOLS = {"tru8_check", "tru8_get_result", "tru8_get_result_raw"}

# Long enough for a cold PyPI install on a slow runner; short enough that a
# hung job fails the same day rather than burning the schedule.
INSTALL_TIMEOUT = 300
HANDSHAKE_TIMEOUT = 90

failures: list[str] = []
notes: list[str] = []


def _bin(env_dir: Path, name: str) -> Path:
    """Locate an executable inside a venv on either platform."""
    sub = "Scripts" if os.name == "nt" else "bin"
    exe = f"{name}.exe" if os.name == "nt" else name
    return env_dir / sub / exe


def _handshake(python: Path) -> tuple[bool, set[str], str]:
    """Start the server over stdio and run initialize + tools/list."""
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "tru8-health-check", "version": "1"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    payload = "".join(json.dumps(r) + "\n" for r in requests)

    env = dict(os.environ)
    # A syntactically plausible key. The handshake and tool listing are local —
    # nothing here calls the Tru8 API, so no real credential is needed and the
    # monitor stays safe to run from anywhere.
    env["TRU8_API_KEY"] = "tru8_sk_health_check_not_a_real_key"
    env["TRU8_API_URL"] = "https://api.trueight.com"

    proc = subprocess.run(
        [str(python), "-m", MODULE],
        input=payload,
        capture_output=True,
        text=True,
        timeout=HANDSHAKE_TIMEOUT,
        env=env,
    )

    initialized = False
    tools: set[str] = set()
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if msg.get("id") == 1 and "result" in msg:
            initialized = True
        if msg.get("id") == 2 and "result" in msg:
            tools = {t.get("name") for t in msg["result"].get("tools", [])}

    return initialized, tools, (proc.stderr or "").strip()


def main() -> int:
    print(f"Checking the PUBLISHED {PACKAGE} package, as a new user would get it\n")
    tmp = Path(tempfile.mkdtemp(prefix="tru8-mcp-check-"))
    try:
        env_dir = tmp / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(env_dir)
        python = _bin(env_dir, "python")

        # 1. Install exactly what a new user installs — unpinned, so that
        #    dependency drift (the actual 2026-08-04 failure) is in scope.
        #
        #    A local artefact may be given instead, to run this BEFORE upload:
        #        python scripts/check_published_mcp.py path/to/dist/*.whl
        #    A PyPI version cannot be re-uploaded, so catching it here is the
        #    difference between a non-event and a public break.
        target = sys.argv[1] if len(sys.argv) > 1 else PACKAGE
        if target != PACKAGE:
            if not Path(target).exists():
                print(f"FAIL  artefact not found: {target}")
                return 1
            print(f"      pre-publish mode — testing local artefact\n      {target}")

        install = subprocess.run(
            [str(python), "-m", "pip", "install", "--no-cache-dir", "-q", target],
            capture_output=True,
            text=True,
            timeout=INSTALL_TIMEOUT,
        )
        if install.returncode != 0:
            tail = (install.stderr or install.stdout or "").strip().splitlines()[-6:]
            failures.append("pip install failed:\n      " + "\n      ".join(tail))
            print("FAIL  pip install " + target)
            return 1
        print(f"ok    pip install {target if target == PACKAGE else Path(target).name}")

        # Record what actually got resolved — this is the number that moves
        # underneath us when an upstream ships a major version.
        versions = subprocess.run(
            [
                str(python),
                "-c",
                "import importlib.metadata as m;"
                f"print(m.version('{PACKAGE}'), m.version('mcp'))",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if versions.returncode == 0:
            pkg_v, mcp_v = versions.stdout.split()
            notes.append(f"{PACKAGE}=={pkg_v} resolved mcp=={mcp_v}")
            print(f"ok    resolved {PACKAGE}=={pkg_v} with mcp=={mcp_v}")
        else:
            failures.append("could not read installed versions")
            print("FAIL  reading installed versions")

        # 2 + 3. Make it speak. An import check alone would have caught the
        # 2026-08-04 break, but a handshake also catches a server that imports
        # and then cannot serve.
        try:
            initialized, tools, stderr = _handshake(python)
        except subprocess.TimeoutExpired:
            failures.append(f"server did not respond within {HANDSHAKE_TIMEOUT}s")
            print("FAIL  MCP handshake (timeout)")
            return 1

        if initialized:
            print("ok    MCP initialize handshake")
        else:
            tail = "\n      ".join(stderr.splitlines()[-6:]) or "(no stderr)"
            failures.append("server did not complete initialize:\n      " + tail)
            print("FAIL  MCP initialize handshake")

        missing = EXPECTED_TOOLS - tools
        if not missing:
            print(f"ok    tools advertised ({len(tools)}): {', '.join(sorted(tools))}")
        else:
            failures.append(
                f"tools missing from tools/list: {', '.join(sorted(missing))}"
            )
            print(f"FAIL  tools/list missing: {', '.join(sorted(missing))}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print()
    for n in notes:
        print(f"      {n}")
    if failures:
        print(f"\n{len(failures)} problem(s) with the PUBLISHED package:\n")
        for f in failures:
            print(f"  - {f}")
        print(
            "\nThis is what a new user gets from `pip install "
            f"{PACKAGE}`. The repo passing its own tests does not help them."
        )
        return 1

    print("\nPublished package installs and runs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
