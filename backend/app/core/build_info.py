"""Which commit is actually serving this request.

WHY THIS EXISTS
---------------
2026-08-05 cost 30p of founder money and about an hour on two live checks that
could not answer a simple question: had the fix been deployed at all? Nothing
the running app served named the code serving it. `/api/v1/health/` reported a
hard-coded `"0.1.0"`, and the manifest fingerprint hashes only model
configuration, so "not deployed" and "deployed but did not fire" were
indistinguishable from the outside.

THE HONESTY RULE FOR THIS MODULE
--------------------------------
It reports only what it can establish, and says `"unknown"` otherwise. A
plausible-looking placeholder is worse than an absence — a static version string
is exactly what wasted the hour, because it looked like an answer. For the same
reason every reading names its own source, so a caller can tell a
platform-injected SHA from a local working-tree guess.

WHERE THE VALUE COMES FROM
--------------------------
`.git/` is listed in `backend/.dockerignore`, so the repository is NOT present
in the production image: reading git cannot work there, and the
platform-injected environment variable is the only source that can. Railway sets
`RAILWAY_GIT_COMMIT_SHA` on GitHub-connected services. `GIT_COMMIT_SHA` is
honoured first as a manual override or Docker build arg, so this stays useful if
the host ever changes. The git fallback is for local runs only.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple

UNKNOWN = "unknown"

#: Checked in order. The generic name wins so a deploy can always override the
#: platform's value by hand.
_SHA_ENV_VARS = ("GIT_COMMIT_SHA", "RAILWAY_GIT_COMMIT_SHA")
_BRANCH_ENV_VARS = ("GIT_BRANCH", "RAILWAY_GIT_BRANCH")

_SHORT_LEN = 7


def _is_sha(value: Optional[str]) -> bool:
    """A full-length hex object name, and nothing else.

    Anything shorter or non-hex is treated as absent rather than reported. An
    env var holding a branch name or a truncated value would otherwise be
    served as though it were a verified commit.
    """
    if not value:
        return False
    value = value.strip()
    return len(value) == 40 and all(c in "0123456789abcdefABCDEF" for c in value)


def _from_env() -> Tuple[Optional[str], Optional[str]]:
    for name in _SHA_ENV_VARS:
        candidate = os.environ.get(name)
        if _is_sha(candidate):
            return candidate.strip().lower(), name
    return None, None


def _git_dir() -> Optional[Path]:
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".git"
        if candidate.is_dir():
            return candidate
    return None


def _from_git() -> Tuple[Optional[str], Optional[str]]:
    """Read HEAD straight off disk — no subprocess, no git binary required.

    Local development only; see the module docstring on why this can never be
    the production path.
    """
    git_dir = _git_dir()
    if git_dir is None:
        return None, None

    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None, None

    if not head.startswith("ref:"):
        # Detached HEAD holds the object name directly.
        return (head.lower(), "git_head") if _is_sha(head) else (None, None)

    ref = head[4:].strip()
    try:
        sha = (git_dir / ref).read_text(encoding="utf-8").strip()
        if _is_sha(sha):
            return sha.lower(), "git_head"
    except OSError:
        pass

    # A ref that has been packed has no loose file of its own.
    try:
        for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
            if line.startswith("#") or " " not in line:
                continue
            sha, _, name = line.partition(" ")
            if name.strip() == ref and _is_sha(sha):
                return sha.lower(), "git_packed_refs"
    except OSError:
        pass

    return None, None


def _branch() -> Optional[str]:
    for name in _BRANCH_ENV_VARS:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()

    git_dir = _git_dir()
    if git_dir is None:
        return None
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if head.startswith("ref: refs/heads/"):
        return head[len("ref: refs/heads/") :].strip() or None
    return None


@lru_cache(maxsize=1)
def get_build_info() -> dict:
    """Commit identity for the running process.

    Cached: none of the inputs change during a process's life. Tests that set
    the environment must call `get_build_info.cache_clear()`.
    """
    sha, source = _from_env()
    if sha is None:
        sha, source = _from_git()

    branch = _branch()
    return {
        "commit": sha[:_SHORT_LEN] if sha else UNKNOWN,
        "commit_full": sha or UNKNOWN,
        "commit_source": source or UNKNOWN,
        "branch": branch or UNKNOWN,
    }
