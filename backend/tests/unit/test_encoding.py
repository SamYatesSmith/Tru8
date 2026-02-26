"""Tests for UTF-8 mojibake fix and recursive string sanitization."""

from app.utils.encoding import fix_mojibake
from app.api.v1.checks import _sanitize_strings


# ---------------------------------------------------------------------------
# fix_mojibake
# ---------------------------------------------------------------------------


class TestFixMojibake:
    def test_fix_mojibake_curly_quote(self):
        # U+2019 RIGHT SINGLE QUOTATION MARK: UTF-8 bytes \xe2\x80\x99
        # Misread as Latin-1 produces the mojibake string.
        mojibake = "\u2019".encode("utf-8").decode("latin-1")
        assert fix_mojibake(mojibake) == "\u2019"

    def test_fix_mojibake_degree_sign(self):
        # U+00B0 DEGREE SIGN: UTF-8 bytes \xc2\xb0
        # Misread as Latin-1 produces "Â°".
        mojibake = "\u00b0".encode("utf-8").decode("latin-1")
        assert mojibake == "\u00c2\u00b0"  # confirm the input is "Â°"
        assert fix_mojibake(mojibake) == "\u00b0"

    def test_fix_mojibake_em_dash(self):
        # U+2014 EM DASH: UTF-8 bytes \xe2\x80\x94
        mojibake = "\u2014".encode("utf-8").decode("latin-1")
        assert fix_mojibake(mojibake) == "\u2014"

    def test_fix_mojibake_clean_passthrough(self):
        clean = "Hello, world! This is clean UTF-8."
        assert fix_mojibake(clean) == clean

    def test_fix_mojibake_empty_string(self):
        assert fix_mojibake("") == ""

    def test_fix_mojibake_non_latin_passthrough(self):
        # CJK and Arabic characters cannot be encoded as Latin-1,
        # so UnicodeEncodeError is caught and the original is returned.
        cjk = "\u4f60\u597d\u4e16\u754c"
        assert fix_mojibake(cjk) == cjk

        arabic = "\u0645\u0631\u062d\u0628\u0627"
        assert fix_mojibake(arabic) == arabic


# ---------------------------------------------------------------------------
# _sanitize_strings
# ---------------------------------------------------------------------------


class TestSanitizeStrings:
    def test_sanitize_strings_nested_dict(self):
        mojibake = "\u2019".encode("utf-8").decode("latin-1")
        data = {"outer": {"inner": mojibake}}
        result = _sanitize_strings(data)
        assert result == {"outer": {"inner": "\u2019"}}

    def test_sanitize_strings_list(self):
        mojibake_a = "\u2014".encode("utf-8").decode("latin-1")
        mojibake_b = "\u00b0".encode("utf-8").decode("latin-1")
        data = [mojibake_a, mojibake_b, "clean"]
        result = _sanitize_strings(data)
        assert result == ["\u2014", "\u00b0", "clean"]

    def test_sanitize_strings_non_string_passthrough(self):
        assert _sanitize_strings(42) == 42
        assert _sanitize_strings(None) is None
        assert _sanitize_strings(True) is True

    def test_sanitize_strings_deep_nesting(self):
        mojibake = "\u2019".encode("utf-8").decode("latin-1")
        data = {"a": [{"b": {"c": mojibake}}]}
        result = _sanitize_strings(data)
        assert result == {"a": [{"b": {"c": "\u2019"}}]}
