"""Recover omitted structured main-content blocks without publisher rules.

This is bounded supplementation, not full-page extraction or fact verification.
Navigation/hidden material is ineligible. Existing narrative text stays intact.
"""

import re

from bs4 import BeautifulSoup
from app.utils.encoding import fix_mojibake

MAX_ADDITIONAL_CHARS = 6000
MAX_BLOCKS = 12
MAX_BLOCK_CHARS = 1800
_VALUE = re.compile(r"^[+−-]?\d[\d,.]*\s*(?:%|°[CFK]?|[A-Za-z]{1,5})?$")


def _text(node):
    return re.sub(r"\s+", " ", fix_mojibake(node.get_text(" ", strip=True))).strip()


def _normalise(text):
    # Keep signs, decimal points and units: -5% must not deduplicate against 5%.
    return re.sub(r"\s+", " ", text.casefold().replace("|", " ")).strip()


def supplement_main_content(html: str, narrative: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for node in list(
        soup.select(
            "script, style, template, noscript, nav, aside, footer, header, form, "
            'button, input, select, textarea, [hidden], [inert], [aria-hidden="true"], '
            '[role="navigation"], [role="banner"], [role="contentinfo"], '
            '[role="complementary"], [role="dialog"]'
        )
    ):
        node.decompose()
    for node in list(soup.find_all(style=True)):
        if re.search(
            r"(?:display\s*:\s*none|visibility\s*:\s*hidden)",
            node.get("style", ""),
            re.I,
        ):
            node.decompose()
    roots = soup.select('main, [role="main"]') or soup.find_all("article")
    if not roots:
        return narrative
    candidates = []
    seen_nodes = set()
    for root in roots:
        for node in root.find_all(["table", "dl", "div", "section"]):
            if id(node) in seen_nodes:
                continue
            seen_nodes.add(id(node))
            text = _text(node)
            if not text or len(text) > MAX_BLOCK_CHARS:
                continue  # no mid-row or label/value truncation
            if node.name in {"div", "section"}:
                children = node.find_all(recursive=False)
                values = [_text(child) for child in children]
                # A standalone numeric value with sibling label/context. Do not
                # harvest every dated headline or numbered navigation link.
                if (
                    len(text) > 600
                    or len(values) < 2
                    or not any(_VALUE.fullmatch(v) for v in values)
                ):
                    continue
                if not any(
                    re.search(r"[A-Za-z]{3,}", v) and not _VALUE.fullmatch(v)
                    for v in values
                ):
                    continue
            elif node.name == "table":
                rows = [
                    " | ".join(
                        _text(cell)
                        for cell in row.find_all(["th", "td"], recursive=False)
                    )
                    for row in node.find_all("tr")
                ]
                caption = node.find("caption", recursive=False)
                text = "\n".join(
                    row for row in ([_text(caption)] if caption else []) + rows if row
                )
                if not text or len(text) > MAX_BLOCK_CHARS:
                    continue
            candidates.append(text)
    additions = []
    existing = _normalise(narrative)
    total = 0
    for text in candidates:
        normalised = _normalise(text)
        if not normalised or normalised in existing:
            continue
        if total + len(text) > MAX_ADDITIONAL_CHARS:
            continue
        additions.append(text)
        total += len(text)
        existing += " " + normalised
        if len(additions) == MAX_BLOCKS:
            break
    return "\n\n".join([narrative, *additions]) if additions else narrative
