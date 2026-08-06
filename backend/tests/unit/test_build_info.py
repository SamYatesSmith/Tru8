"""What code is running — the answer 2026-08-05 could not get.

Two live checks that day (30p of founder money, about an hour) could not
distinguish "the fix is not deployed" from "the fix is deployed and did not
fire", because nothing the app served named the commit serving it.

The property under test is therefore not "a SHA appears somewhere". It is that
the value is either PROVABLE or openly `unknown` — a plausible-looking
placeholder is what wasted the hour in the first place, because it read as an
answer.
"""

import subprocess

import pytest

from app.core import build_info
from app.core.build_info import UNKNOWN, get_build_info

REAL_SHA = "27fc5dc4737fefeeee5e018cd92617f6bf2020ed"
OTHER_SHA = "656618b0000000000000000000000000000000ab"

_ALL_ENV = (
    "GIT_COMMIT_SHA",
    "RAILWAY_GIT_COMMIT_SHA",
    "GIT_BRANCH",
    "RAILWAY_GIT_BRANCH",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """No leakage in either direction — the reading is process-cached."""
    for name in _ALL_ENV:
        monkeypatch.delenv(name, raising=False)
    get_build_info.cache_clear()
    yield
    get_build_info.cache_clear()


# ---------------------------------------------------------------------------
# The production path — an injected environment variable
# ---------------------------------------------------------------------------


def test_the_platform_variable_is_read(monkeypatch):
    """`.git` is in .dockerignore, so this is the ONLY source that works in prod."""
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", REAL_SHA)

    info = get_build_info()

    assert info["commit"] == "27fc5dc"
    assert info["commit_full"] == REAL_SHA
    assert info["commit_source"] == "RAILWAY_GIT_COMMIT_SHA"


def test_the_short_commit_matches_what_git_log_prints():
    """The whole point is comparing it against `git log --oneline` by eye."""
    git_dir = build_info._git_dir()
    if git_dir is None:
        pytest.skip("no repository present (expected inside the built image)")
    expected = subprocess.run(
        ["git", "rev-parse", "--short=7", "HEAD"],
        capture_output=True,
        text=True,
        cwd=git_dir.parent,
    )
    if expected.returncode != 0:
        pytest.skip("git binary unavailable")

    assert get_build_info()["commit"] == expected.stdout.strip()


def test_a_manual_override_beats_the_platform(monkeypatch):
    """So this survives a change of host without a code change."""
    monkeypatch.setenv("RAILWAY_GIT_COMMIT_SHA", OTHER_SHA)
    monkeypatch.setenv("GIT_COMMIT_SHA", REAL_SHA)

    assert get_build_info()["commit_full"] == REAL_SHA


def test_the_branch_is_reported(monkeypatch):
    monkeypatch.setenv("RAILWAY_GIT_BRANCH", "main")

    assert get_build_info()["branch"] == "main"


# ---------------------------------------------------------------------------
# Honesty — the property that makes this endpoint worth reading at all
# ---------------------------------------------------------------------------


def test_nothing_knowable_reports_unknown_not_a_placeholder(monkeypatch):
    """An absence must look like an absence.

    If this ever returns a version-shaped string when it cannot establish the
    commit, the endpoint becomes what it replaced: something that reads like an
    answer and is not one.

    Asserted against the LITERAL, deliberately. Comparing against the imported
    `UNKNOWN` sentinel let a mutation that redefined it to "0.1.0" pass this
    file untouched — the assertion simply moved with the mutation.
    """
    monkeypatch.setattr(build_info, "_git_dir", lambda: None)

    info = get_build_info()

    assert info == {
        "commit": "unknown",
        "commit_full": "unknown",
        "commit_source": "unknown",
        "branch": "unknown",
    }


def test_the_sentinel_cannot_be_mistaken_for_a_version():
    """Pins the sentinel itself, so redefining it fails here rather than silently.

    The defect this module exists to fix was a static, version-shaped string
    being served as though it identified the running code. A sentinel that looked
    like one would reintroduce it.
    """
    assert UNKNOWN == "unknown"
    assert not any(c.isdigit() for c in UNKNOWN)


@pytest.mark.parametrize(
    "value",
    [
        "main",  # a branch name in the SHA slot
        "27fc5dc",  # already shortened — cannot be verified as an object name
        "",
        "   ",
        "27fc5dc4737fefeeee5e018cd92617f6bf2020eg",  # 40 chars, 'g' is not hex
        "27fc5dc4737fefeeee5e018cd92617f6bf2020ed0",  # 41 chars
    ],
)
def test_a_value_that_is_not_a_commit_is_not_served_as_one(monkeypatch, value):
    """Refusing these is what keeps `commit_source` meaningful."""
    monkeypatch.setattr(build_info, "_git_dir", lambda: None)
    monkeypatch.setenv("GIT_COMMIT_SHA", value)

    info = get_build_info()

    assert info["commit"] == "unknown"
    assert info["commit_source"] == "unknown"


def test_the_source_is_always_named(monkeypatch):
    """A caller must be able to tell a platform SHA from a local guess."""
    monkeypatch.setenv("GIT_COMMIT_SHA", REAL_SHA)
    assert get_build_info()["commit_source"] == "GIT_COMMIT_SHA"

    get_build_info.cache_clear()
    monkeypatch.delenv("GIT_COMMIT_SHA")
    assert get_build_info()["commit_source"] in ("git_head", "git_packed_refs")


def test_case_and_whitespace_are_normalised(monkeypatch):
    monkeypatch.setenv("GIT_COMMIT_SHA", f"  {REAL_SHA.upper()}  ")

    assert get_build_info()["commit_full"] == REAL_SHA
