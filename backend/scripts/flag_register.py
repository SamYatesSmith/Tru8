"""Generate audit/FLAGS.md: every boolean feature flag, its default and why.

Run from backend/:  python -m scripts.flag_register
A unit test (tests/unit/test_flag_register.py) fails when the committed
register no longer matches config.py, so the register cannot drift.

Defaults come from the Settings model (never from .env or Railway). Production
can override any flag with an environment variable of the same name; the
register cannot see those, so check Railway when a flag's live value matters.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

BACKEND = Path(__file__).resolve().parents[1]
CONFIG = BACKEND / "app" / "core" / "config.py"
OUT = BACKEND.parent / "audit" / "FLAGS.md"

_FIELD = re.compile(r"^    ([A-Z][A-Z0-9_]*)\s*:\s*bool\b")
_READ = re.compile(
    r"""settings\s*,\s*["']([A-Z][A-Z0-9_]*)["']|settings\.([A-Z][A-Z0-9_]*)"""
)


def _is_flag(name: str) -> bool:
    return name.startswith("ENABLE_") or name.endswith("_ENABLED")


def _comments(lines: List[str]) -> Dict[str, str]:
    """The contiguous comment block directly above each flag field."""
    out: Dict[str, str] = {}
    for i, line in enumerate(lines):
        m = _FIELD.match(line)
        if not m or not _is_flag(m.group(1)):
            continue
        block: List[str] = []
        j = i - 1
        while j >= 0 and lines[j].strip().startswith("#"):
            block.insert(0, lines[j].strip().lstrip("#").strip())
            j -= 1
        out[m.group(1)] = " ".join(b for b in block if b)
    return out


def _summary(comment: str) -> str:
    """First sentence of the comment, plus any dated OFF/ON/ROLLBACK line."""
    if not comment:
        return ""
    first = re.split(r"(?<=[.!?])\s", comment, maxsplit=1)[0]
    extra = re.findall(
        r"((?:OFF|ON|SWITCHED ON|ROLLED BACK)\s+\d{4}-\d{2}-\d{2}[^.]*\.)", comment
    )
    text = first + ("" if not extra or extra[0] in first else " " + extra[-1])
    text = text.replace("|", "/")
    return text if len(text) <= 260 else text[:257] + "..."


def _readers() -> Dict[str, int]:
    """How many app files read each flag name (0 = declared but unused)."""
    counts: Dict[str, set] = {}
    paths = list((BACKEND / "app").rglob("*.py")) + [BACKEND / "main.py"]
    for path in paths:
        if path == CONFIG:
            continue
        for m in _READ.finditer(path.read_text(encoding="utf-8", errors="replace")):
            name = m.group(1) or m.group(2)
            if _is_flag(name):
                counts.setdefault(name, set()).add(path)
    return {k: len(v) for k, v in counts.items()}


def build() -> str:
    sys.path.insert(0, str(BACKEND))
    from app.core.config import Settings  # noqa: E402

    fields = {
        name: f.default
        for name, f in Settings.model_fields.items()
        if _is_flag(name) and isinstance(f.default, bool)
    }
    comments = _comments(CONFIG.read_text(encoding="utf-8").splitlines())
    readers = _readers()
    undeclared = sorted(n for n in readers if n not in fields)

    rows: List[Tuple[str, bool]] = sorted(fields.items(), key=lambda kv: (kv[1], kv[0]))
    off = [n for n, d in rows if not d]
    out = [
        "# Feature flags (generated — do not edit by hand)",
        "",
        "Regenerate with `cd backend && python -m scripts.flag_register`. "
        "`tests/unit/test_flag_register.py` fails when this file is stale.",
        "",
        "Defaults are the code's. **Railway can override any flag with an env var of the "
        "same name; this file cannot see that.** Check Railway when a live value matters.",
        "",
        f"**{len(rows)} flags: {len(rows) - len(off)} on, {len(off)} off by default.**",
        "",
        "| Flag | Default | Read in | Why (from config.py) |",
        "|---|---|---|---|",
    ]
    for name, default in rows:
        n = readers.get(name, 0)
        where = (
            f"{n} file{'s' if n != 1 else ''}"
            if n
            else "**unused** (setting it does nothing)"
        )
        out.append(
            f"| `{name}` | {'ON' if default else '**OFF**'} | {where} | "
            f"{_summary(comments.get(name, ''))} |"
        )
    if undeclared:
        out += [
            "",
            "## Read in code but not declared in Settings",
            "",
            "These fall back to the default written at each `getattr` call, and no env var "
            "can set them.",
            "",
        ] + [f"- `{n}`" for n in undeclared]
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    text = build()
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({text.count(chr(10) + '| `')} flags)")
