"""Unstated quantity — a grounds question must not demand a figure the claim
never stated.

Blind review of the 2026-09-09 post-fix regrade
(audit/review_sheets/2026-09-09-postfix): 11 of 27 rejected labels sat on ONE
record, "Electric cars are cleaner than petrol cars", whose grounds questions
asked for quantities the claim never mentioned —

    "What is the total lifecycle greenhouse gas emission volume associated
     with the manufacturing and operation of electric cars compared to petrol
     cars?"
    "What proportion of the electricity used to charge electric cars is
     generated from fossil fuels across major vehicle markets?"

A source that says "electric cars emit less over their lifetime" answers the
claim and cannot answer the question, so the reviewer says "neither" and the
label reads as unjustified. The same disease as "exactly 5g" on the assertion
path (app/utils/invented_precision.py), in question form.

This module is the mechanical half of the fix (NF-11: a prompt rule is a first
line of defence, never a guarantee). It only ever *detects*; rewriting is the
caller's business (opinion_symmetry._repair_questions). It fires only on the
question heads measured in the review plus their close kin, and never when
the claim itself states a quantity — a claim that says "30%" may be asked
"what proportion".
"""

from __future__ import annotations

import re
from typing import List

# Heads that ask for a figure. Deliberately NARROW: "how much" / "how many"
# and "what is the average" are left out on purpose — "How much did the
# scheme cost?" is a legitimate ground for "the scheme was a waste of money",
# and the prompt rule covers the open set. This list is the measured forms.
_QUANTITY_HEAD = re.compile(
    r"^\s*(?:"
    r"what\s+(?:proportion|percentage|share|fraction|volume|quantity|magnitude)\b"
    r"|what\s+(?:is|was|are|were)\s+the\s+"
    r"(?:total|exact|precise|quantified|overall|aggregate|absolute|net)\b"
    r"|by\s+what\s+(?:proportion|percentage|share|fraction|margin|factor)\b"
    # Two heads the build-2 measurement exposed (2026-09-10 b2 runs 1-2, EV
    # record, 4 labels): "How does the PROPORTION of … compare across …" and
    # "What do lifecycle analyses show regarding the TOTAL carbon footprint …".
    # The quantity noun sits after an auxiliary or a reporting verb rather
    # than at the head; the demand is the same.
    r"|how\s+(?:does|do|did)\s+the\s+"
    r"(?:proportion|percentage|share|fraction|volume|total|amount|magnitude)\b"
    r"|what\s+(?:do|does|did)\s+[^?]{0,60}?\b(?:show|indicate|say|reveal|report|find)\s+"
    r"(?:regarding|about|on)\s+the\s+"
    r"(?:total|proportion|percentage|share|volume|exact|precise|aggregate|quantified)\b"
    r")",
    re.I,
)

# A claim that carries any of these has stated a quantity; the question may
# then ask for one. "number of" rather than bare "number" — "a number of
# reasons" is not a figure.
_CLAIM_QUANTITY = re.compile(
    r"(?:\d|%|\bper\s?cent\b|\bpercentage\b|\bproportion\b|\bshare\b|\bfraction\b"
    r"|\btotal\b|\bmajority\b|\bminority\b|\bhalf\b|\bthird\b|\bquarter\b"
    r"|\bdouble\b|\btriple\b|\btwice\b|\bfold\b|\bvolume\b|\bamount\b"
    r"|\bnumber\s+of\b|\bhow\s+much\b|\bhow\s+many\b|\bmagnitude\b)",
    re.I,
)


def claim_states_quantity(claim_text: str) -> bool:
    """True when the claim itself names a figure, proportion, total or
    threshold — the question is then entitled to ask for one."""
    return bool(_CLAIM_QUANTITY.search(claim_text or ""))


def demands_unstated_quantity(question: str, claim_text: str) -> bool:
    """True when ``question`` opens by asking for a figure and ``claim_text``
    states none."""
    if not question:
        return False
    if claim_states_quantity(claim_text):
        return False
    return bool(_QUANTITY_HEAD.match(question))


def unstated_quantity_indices(descriptions: List[str], claim_text: str) -> List[int]:
    """Positions of the quantity-demanding descriptions, in order."""
    return [
        i
        for i, d in enumerate(descriptions)
        if demands_unstated_quantity(d or "", claim_text)
    ]
