"""P3-A mutation matrix — proof the new guards FIRE, not merely that they pass.

A green test file is not evidence it pins anything. Each mutation below breaks
exactly one property P3-A claims to hold; the named test MUST fail. If a
mutation is applied and the suite still passes, that guard is decoration.

Files are restored and SHA-verified after every mutation, so a crash cannot
leave a mutated tree behind.

Usage:  python -m scripts.p3a_mutation_matrix
"""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
ANALYZER = BACKEND / "app" / "pipeline" / "claim_map_analyzer.py"
SYMMETRY = BACKEND / "app" / "pipeline" / "opinion_symmetry.py"

TESTS = [
    "tests/unit/pipeline/test_grounds_mapping.py",
    "tests/unit/pipeline/test_opinion_symmetry.py",
]

# (label, file, find, replace, test that MUST fail)
MUTATIONS = [
    (
        "drop the collapsed check -> lock-collapse reads as grounds again",
        ANALYZER,
        '    if grounds.get("collapsed") is True:\n        return False\n',
        "",
        "test_lock_collapsed_map_is_not_treated_as_grounds",
    ),
    (
        "use `applied and converged` -> thin question sets demoted (the §4b trap)",
        ANALYZER,
        '    if grounds.get("collapsed") is True:\n        return False\n    return grounds.get("applied") is True',
        '    if grounds.get("converged") is not True:\n        return False\n    return grounds.get("applied") is True',
        "test_thin_but_genuine_question_set_is_still_grounds",
    ),
    (
        "stop disclosing collapse -> downstream cannot tell the two apart",
        SYMMETRY,
        '        "collapsed": bool(lock_collapsed),\n',
        "",
        "test_lock_collapse_restores_baseline_but_discloses",
    ),
    (
        "always disclose collapsed -> every grounds claim demoted to assertions",
        SYMMETRY,
        '        "collapsed": bool(lock_collapsed),',
        '        "collapsed": True,',
        "test_collapsed_is_false_when_the_rebuild_actually_produced_questions",
    ),
    (
        "truthy instead of `is True` -> corrupt metadata silently disables grounds",
        ANALYZER,
        '    if grounds.get("collapsed") is True:',
        '    if grounds.get("collapsed"):',
        "test_collapsed_only_disables_on_exact_true",
    ),
]


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run_tests() -> tuple[bool, str]:
    r = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *TESTS,
            "-q",
            "--no-cov",
            "-p",
            "no:cacheprovider",
        ],
        cwd=BACKEND,
        capture_output=True,
        text=True,
    )
    return r.returncode == 0, r.stdout + r.stderr


def main() -> int:
    baseline_sha = {p: sha(p) for p in (ANALYZER, SYMMETRY)}

    ok, out = run_tests()
    if not ok:
        print("BASELINE IS RED — fix that before trusting any mutation.")
        print(out[-2000:])
        return 1
    print("baseline GREEN\n")

    failures = []
    for label, path, find, replace, must_fail in MUTATIONS:
        # Bytes, not text: on Windows a text-mode write translates "\n" to
        # "\r\n", so a byte-exact restore is impossible through read_text /
        # write_text and the SHA guard trips on its own round-trip.
        original_bytes = path.read_bytes()
        original = original_bytes.decode("utf-8")
        if find not in original:
            print(f"[SKIP-BROKEN] {label}\n    anchor not found in {path.name}")
            failures.append(label)
            continue
        try:
            path.write_bytes(original.replace(find, replace, 1).encode("utf-8"))
            passed, out = run_tests()
            fired = (not passed) and must_fail in out
            status = "FIRES" if fired else "DID NOT FIRE"
            print(f"[{status}] {label}")
            print(f"           expects: {must_fail}")
            if not fired:
                failures.append(label)
                if passed:
                    print("           suite still GREEN under mutation")
                else:
                    print("           suite red, but NOT via the named test")
        finally:
            path.write_bytes(original_bytes)
            assert sha(path) == baseline_sha[path], f"RESTORE FAILED for {path}"

    for p, s in baseline_sha.items():
        assert sha(p) == s, f"tree left mutated: {p}"
    print("\nall files restored and SHA-verified")

    if failures:
        print(f"\n{len(failures)}/{len(MUTATIONS)} mutation(s) did not fire:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print(f"\n{len(MUTATIONS)}/{len(MUTATIONS)} mutations fire — guards are real.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
