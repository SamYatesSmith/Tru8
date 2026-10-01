"""audit/FLAGS.md must match config.py (2026-10-01).

If this fails, run `cd backend && python -m scripts.flag_register` and commit
the regenerated register alongside the flag change.
"""

from scripts.flag_register import OUT, build


def test_flag_register_is_current():
    assert OUT.exists(), "audit/FLAGS.md missing: run python -m scripts.flag_register"
    assert (
        OUT.read_text(encoding="utf-8") == build()
    ), "audit/FLAGS.md is stale: run `python -m scripts.flag_register` and commit it"
