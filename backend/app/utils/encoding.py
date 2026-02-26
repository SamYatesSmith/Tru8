"""Shared encoding utilities — UTF-8 sanitization for API responses."""


def fix_mojibake(text: str) -> str:
    """Fix double-encoded UTF-8 (UTF-8 bytes misread as Latin-1/CP1252).

    Common symptom: â€™ instead of ', Â° instead of °.
    This happens when a page's UTF-8 bytes are decoded as Latin-1.
    Fix: re-encode as Latin-1 to recover the original bytes, then decode as UTF-8.
    """
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text
