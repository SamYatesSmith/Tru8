"""Brand assets for the PDF evidence report, embedded as ``data:`` URIs.

The PDF renders through WeasyPrint with an external-fetch blocker (F-SEC-05):
it may not load anything over the network or off disk at render time. So the
product's brand fonts (Inter + JetBrains Mono) cannot be referenced by URL —
they are base64-embedded into an ``@font-face`` stylesheet computed once at
import. This keeps the render fully self-contained (no network, no filesystem
access from the renderer) while giving the print artefact the same typography
as the dashboard, ``/r/`` and the OG share cards.

If a font file is missing the rule is skipped and the template's Helvetica
fallback stack applies — the report still renders, just without brand type.
"""

from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).resolve().parent.parent / "templates" / "pdf" / "fonts"

# (family, css font-weight, css font-style, filename). Only the weights the
# brand actually ships are embedded: Inter 400/600, JetBrains Mono 400/700.
_FONT_FILES: list[tuple[str, int, str, str]] = [
    ("Inter", 400, "normal", "Inter-Regular.ttf"),
    ("Inter", 600, "normal", "Inter-SemiBold.ttf"),
    ("JetBrains Mono", 400, "normal", "JetBrainsMono-Regular.ttf"),
    ("JetBrains Mono", 700, "normal", "JetBrainsMono-Bold.ttf"),
]


def _build_font_face_css() -> str:
    """Read the brand TTFs and return an ``@font-face`` block with data: URIs.

    Missing files are skipped with a warning so a partial/absent font set can
    never break PDF rendering — the Helvetica fallback stack takes over.
    """
    rules: list[str] = []
    for family, weight, style, filename in _FONT_FILES:
        path = _FONTS_DIR / filename
        try:
            data = path.read_bytes()
        except OSError as exc:
            logger.warning(
                "PDF brand font unavailable, using fallback: %s (%s)", filename, exc
            )
            continue
        b64 = base64.b64encode(data).decode("ascii")
        rules.append(
            f"@font-face{{font-family:'{family}';font-style:{style};"
            f"font-weight:{weight};src:url(data:font/ttf;base64,{b64}) "
            "format('truetype');}"
        )
    return "".join(rules)


# Computed once at import — the TTFs are small (~250KB total) and static.
FONT_FACE_CSS: str = _build_font_face_css()
