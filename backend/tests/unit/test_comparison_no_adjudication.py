"""COMPARE: the premise-adoption wall, enforced structurally.

The live acceptance probe (design §10.2 — identical pair run with and
without the claim line, delta measured in both valence directions) is a
verification-stage task and cannot run in unit tests. What CAN be pinned
here is the structural half: the prompt builder has no claim parameter at
all, and the orchestration never reads the claim's text — so the claim
CANNOT leak into the prompt without changing a signature these tests watch.

Prompt-only fixes have failed in this codebase before
(feedback_nf11_prompt_only_failed); this is the mechanical rule behind the
prompt's wording.
"""

import inspect

from app.services import comparison


class TestClaimCannotReachThePrompt:
    def test_prompt_builder_has_no_claim_parameter(self):
        params = set(inspect.signature(comparison.build_comparison_prompt).parameters)
        assert params == {
            "element_descriptions",
            "source_a",
            "source_b",
            "text_a",
            "text_b",
            "basis_a",
            "basis_b",
        }

    def test_orchestration_never_reads_claim_text(self):
        source = inspect.getsource(comparison.run_comparison)
        assert "claim.text" not in source
        assert "normalised_claim" not in source
        assert "normalisedClaim" not in source

    def test_prompt_scope_is_element_descriptions(self):
        # The scoping input exists and is threaded from the claim MAP (the
        # neutral, question-shaped layer), not the claim.
        source = inspect.getsource(comparison.run_comparison)
        assert "element_descriptions" in source
        assert "description" in source
