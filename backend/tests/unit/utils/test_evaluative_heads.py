"""Evaluative-head detector — F-VERDICT / P13 (2026-07-26).

Acceptance criteria (1)-(10), frozen at design time before any code was written.
The MUST-NOT-FIRE cases are drawn from the live over-correction battery that was
cleared at the cost of four live checks (Thames Water / MMR): the detector must
not re-open that guard by routing damning-but-EMPIRICAL claims to neutral
grounds.
"""

import pytest

from app.utils.evaluative_heads import (
    EvaluativeHead,
    find_evaluative_head,
    has_evaluative_head,
)


# ── MUST FIRE ───────────────────────────────────────────────────────────────


def test_1_idea_as_subject_fires_predicative():
    """F-VERDICT witness (TRU-52FB-DDC3) — the live invariant breach.

    Returned as an element marked +SUPPORTED by 11 sources. The LLM hint read
    "indefensible" about a *theory* as an epistemic claim.
    """
    head = find_evaluative_head("The learning-styles theory is indefensible.")
    assert head == EvaluativeHead(head="indefensible", shape="predicative")


def test_2_extraposition_fires_and_is_labelled_extraposed():
    """P13 witness (b) — TRU-7EF2-087A, which VOIDED a live verification.

    The shape label is load-bearing: only the extraposed shape loses its head
    during extraction, so only it triggers restoration.
    """
    head = find_evaluative_head(
        "It is indefensible for a government to fund homeopathy with public money."
    )
    assert head == EvaluativeHead(head="indefensible", shape="extraposed")


def test_3_perfect_copula_fires():
    """ "has been a disaster" is as much a main-predicate judgement as "is"."""
    head = find_evaluative_head(
        "The government's handling of the floods has been a disaster."
    )
    assert head == EvaluativeHead(head="disaster", shape="predicative")


def test_4_positive_valence_fires_identically():
    """Invariant #7 forbids distortion in EITHER direction — a positive
    judgement must route to neutral grounds exactly as a negative one does."""
    head = find_evaluative_head("The apprenticeship scheme has been a triumph.")
    assert head == EvaluativeHead(head="triumph", shape="predicative")


# ── MUST NOT FIRE ───────────────────────────────────────────────────────────


def test_5_empirical_discharge_claim_does_not_fire():
    """Over-correction guard, Thames Water battery. Verb predicate, no copular
    evaluative head — structurally unreachable."""
    assert (
        find_evaluative_head(
            "Thames Water discharged 72 billion litres of sewage into rivers in 2023."
        )
        is None
    )


def test_6_empirical_uptake_claim_does_not_fire():
    """Over-correction guard, MMR battery."""
    assert (
        find_evaluative_head("MMR uptake fell below the herd-immunity threshold.")
        is None
    )


def test_7_false_but_factual_assertion_does_not_fire():
    """Rule 6 (extract.py:127-130) classes flat factual assertions as NOT
    evaluative even when false or inflammatory — these stay plain claims."""
    assert find_evaluative_head("The election was stolen.") is None


def test_8_codified_predicate_does_not_fire():
    """Adjudicable predicates have a legal test, so they are researchable as
    plain claims and are excluded from the lexicon by design."""
    assert find_evaluative_head("The merger is anticompetitive.") is None


def test_9_attributed_judgement_does_not_fire():
    """A REPORTED stance is a plain factual claim about what someone said.
    Battery A's attributed-opinion result (0 hints) must be preserved."""
    assert find_evaluative_head("Critics said the policy is a disaster.") is None


def test_10_dual_use_lexeme_in_subject_position_does_not_fire():
    """ "failure" is excluded from the lexicon precisely because of clinical and
    engineering prose like this."""
    assert (
        find_evaluative_head(
            "Heart failure is the leading cause of admissions over 65."
        )
        is None
    )


# ── Properties ──────────────────────────────────────────────────────────────


def test_detector_is_pure_and_idempotent():
    text = "The learning-styles theory is indefensible."
    assert find_evaluative_head(text) == find_evaluative_head(text)


def test_empty_and_none_safe():
    assert find_evaluative_head("") is None
    assert find_evaluative_head(None) is None


def test_attribution_guard_is_sentence_local():
    """An unrelated attribution in a NEIGHBOURING sentence must not suppress a
    genuine judgement — otherwise any article quoting someone goes unguarded."""
    text = "The minister reported record figures. The procurement round was a fiasco."
    head = find_evaluative_head(text)
    assert head is not None
    assert head.head == "fiasco"


def test_has_evaluative_head_convenience():
    assert has_evaluative_head("The rollout has been a shambles.") is True
    assert has_evaluative_head("Rainfall rose 12% year on year.") is False


# ── Regression: independent-verification false fires (2026-07-26) ───────────
# The verifier's exact strings. Each of these FIRED before the terminal-position
# guard, the attribution rewrite and the impact-adjective removal. A false fire
# routes an empirical claim to neutral grounds — the over-correction the live
# battery cleared at the cost of four checks.


@pytest.mark.parametrize(
    "text",
    [
        # A1 — nominal head as a NOUN MODIFIER after a copula.
        "The Federal Emergency Management Agency is the disaster response body created in 1979.",
        "The National Flood Insurance Program is a disaster mitigation scheme.",
        "Swiss Re is a catastrophe reinsurer with $12bn in 2023 premiums.",
        "The Grenfell Tower fire was a disaster in which 72 people died.",
        "The 1984 Bhopal gas leak was a catastrophe that killed at least 3,787 people.",
        "The Horizon IT system was a scandal that led to 900 prosecutions.",
        "Tuvalu is a disaster-prone state.",
        "Puerto Rico is a disaster area under federal law.",
        "The film is a disaster movie about a tsunami.",
        "Lloyd's is a catastrophe reinsurance market.",
        # A2 — impact adjectives stating a MEASURED effect, not a judgement.
        "The 2010 harvest was disastrous for wheat yields in Russia.",
        "Q3 sales were catastrophic, falling 41% year on year.",
        "Coral bleaching is catastrophic for reef fish populations.",
        "The drought was catastrophic for smallholder farmers in Kenya.",
    ],
)
def test_empirical_prose_never_fires(text):
    assert find_evaluative_head(text) is None, f"false fire on: {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        # Post-posed attribution — the dominant journalistic form, which a
        # backward-only guard missed entirely.
        "The rollout has been a disaster, according to the National Audit Office.",
        '"The scheme is a fiasco," said the local MP.',
        "It is indefensible for the government to fund homeopathy, say critics.",
        # Attribution verbs absent from the original lexicon.
        "The report concluded the response was a disaster.",
        "MPs were told the rollout is a disaster.",
        "The committee found the procurement round was a shambles.",
        "Campaigners warned the closure is a betrayal.",
    ],
)
def test_attributed_judgements_never_fire(text):
    assert find_evaluative_head(text) is None, f"attribution bypassed on: {text!r}"


def test_abbreviation_does_not_strand_the_attribution_guard():
    """The sentence splitter cut at "U.S. ", leaving the guard in the discarded
    fragment. Splitting now requires a capital/quote after the boundary."""
    assert (
        find_evaluative_head("According to the NAO, the U.S. rollout was a disaster.")
        is None
    )


@pytest.mark.parametrize(
    "text,expected_head",
    [
        ("The rollout is a complete disaster.", "disaster"),
        ("The scheme was an utter fiasco.", "fiasco"),
        ("The policy is arguably indefensible.", "indefensible"),
    ],
)
def test_intensifier_slot_does_not_block_a_genuine_judgement(text, expected_head):
    """Recall hole: `\w+ly` alone missed "a COMPLETE disaster", the commonest
    intensified shape."""
    head = find_evaluative_head(text)
    assert head is not None, f"missed: {text!r}"
    assert head.head == expected_head


# ── Regression: re-verification round 2 (2026-07-26) ───────────────────────


@pytest.mark.parametrize(
    "text,expected_head",
    [
        ("It is a disgrace that the fund was cut.", "disgrace"),
        ("It is a scandal that 4,000 homes remain unfit.", "scandal"),
        ("It is a travesty that the fund was cut.", "travesty"),
        ("It is a farce that the inquiry has taken nine years.", "farce"),
        ("It is a disaster that the scheme was scrapped.", "disaster"),
    ],
)
def test_nominal_extraposed_shape_fires(text, expected_head):
    """RECALL REGRESSION caught in re-verification: the terminal guard pushed
    "It is a disgrace that…" out of the predicative branch, and the extraposed
    branch had no determiner slot — so the module's own core shape fell between
    them. 5/5 fired before the guard, 0/5 after. Must be `extraposed`, so
    restoration covers it."""
    head = find_evaluative_head(text)
    assert head is not None, f"nominal extraposed missed: {text!r}"
    assert head.head == expected_head
    assert head.shape == "extraposed"


@pytest.mark.parametrize(
    "text,expected_head",
    [
        ("The rollout is arguably a disaster.", "disaster"),
        ('The scheme is a "disaster".', "disaster"),
        ("The policy is arguably indefensible.", "indefensible"),
    ],
)
def test_intensifier_order_and_quoting(text, expected_head):
    """English allows the adverb on either side of the determiner; pinning it to
    one side missed "is arguably a disaster" while "is arguably indefensible"
    fired."""
    head = find_evaluative_head(text)
    assert head is not None, f"missed: {text!r}"
    assert head.head == expected_head


def test_extraposed_branch_still_rejects_bare_nominal_predicate():
    """The determiner slot must not let the extraposed branch swallow a plain
    predicate nominal — "It is a disaster for the region" has no complement
    clause and is not an extraposed judgement."""
    assert find_evaluative_head("It is a disaster for the region.") is None


# ── Regression: re-verification round 3 (2026-07-26) ───────────────────────
# The `for` complement guard was added without its `to` twin, one line away.
# The pin test at the time covered only `for`, so it passed. These fired as
# `extraposed`, which reaches RESTORATION — it rewrites the user's claim set.


@pytest.mark.parametrize(
    "text",
    [
        # Bare `to` + noun phrase — predicate nominal, not a complement clause.
        "It was a scandal to many observers.",
        "It is a disaster to the local economy.",
        "It was a catastrophe to the industry.",
        "It is a disgrace to the profession.",
        "It was a betrayal to the workforce.",
        "It is a triumph to the sport.",
        # The `for` twin, already guarded — pinned so it cannot regress either.
        "It is a disaster for the region.",
        # Unbounded `for … to` window completed by an unrelated later clause.
        "It was a disaster for the region, causing damage to hundreds of homes.",
        "It was a disaster for the region and led to widespread flooding.",
        "It is a scandal for the club, which sold players to rivals.",
        "It is a triumph for the team, second only to the 1966 win.",
        # Quoted/bracketed noun modifier — the closing mark was being accepted
        # as valid terminal punctuation.
        'The scheme is a "disaster" relief fund.',
        "The body is a (disaster) response unit.",
    ],
)
def test_round3_false_fire_vectors_never_fire(text):
    assert find_evaluative_head(text) is None, f"false fire on: {text!r}"


@pytest.mark.parametrize(
    "text,expected_head",
    [
        # NOTE: the adjectival bare-`to` cases that used to live here moved to
        # `test_round5_measured_recall_cost_of_removing_the_bare_to_arm` — the
        # arm was removed for BOTH head classes in round 5 after experiencer PPs
        # ("It is outrageous to me.") proved it leaks on the adjectival side too.
        ("It is unconscionable for a regulator to allow it.", "unconscionable"),
        # Criterion 2 — the `for … to` frame, re-pinned against the new window.
        (
            "It is indefensible for a government to fund homeopathy with public money.",
            "indefensible",
        ),
    ],
)
def test_round3_genuine_complement_clauses_still_fire(text, expected_head):
    head = find_evaluative_head(text)
    assert head is not None, f"complement clause missed: {text!r}"
    assert head.head == expected_head
    assert head.shape == "extraposed"


@pytest.mark.parametrize(
    "text,expected_head",
    [
        ('The scheme is a "disaster".', "disaster"),
        ("The rollout is a 'fiasco'.", "fiasco"),
    ],
)
def test_quoted_head_in_final_position_still_fires(text, expected_head):
    """Stripping quotes must not cost the recall the item-6 fix bought."""
    head = find_evaluative_head(text)
    assert head is not None, f"quoted head missed: {text!r}"
    assert head.head == expected_head


def test_possessive_apostrophe_is_not_fragmented():
    """Quote normalisation must preserve word-internal apostrophes."""
    head = find_evaluative_head("Lloyd's handling of the claim was a disgrace.")
    assert head is not None
    assert head.head == "disgrace"


# ── Regression: re-verification round 4 (2026-07-26) ───────────────────────
# The head-class split. Three attempts to police the nominal `to` case with a
# blocklist each admitted the shape the last one missed; the set of
# noun-phrase-initial words is open, so no list can close it.


@pytest.mark.parametrize(
    "text",
    [
        # Bare plurals — "to the farmers" was blocked while "to farmers" fired.
        "It is a disaster to farmers.",
        "It is a disaster to local businesses.",
        "It is a scandal to ordinary people.",
        "It was a betrayal to working families.",
        "It is a catastrophe to British agriculture.",
        # Pronouns.
        "It is a disaster to us.",
        "It was a scandal to me.",
        "It is a travesty to them.",
        "It was a disgrace to everyone involved.",
        # Possessives and unlisted quantifiers.
        "It is a betrayal to Britain's farmers.",
        "It was a disaster to several communities.",
        "It is a scandal to such an extent.",
        "It was a catastrophe to two entire villages.",
        "It is a disgrace to every taxpayer.",
        "It was a betrayal to countless workers.",
        "It is a triumph to fans everywhere.",
        # Comma-less coordination completing the `for … to` window across an
        # unrelated clause. The character class already bars commas, so this
        # list only ever mattered here.
        "It was a disaster for the region so ministers agreed to intervene.",
        "It was a disaster for the region while others moved to safety.",
        "It is a scandal for the club with players sold to rivals.",
        "It was a betrayal for staff yet unions declined to strike.",
        "It is a disaster for farmers after ministers refused to act.",
        "It was a catastrophe for insurers despite pledges to pay.",
    ],
)
def test_round4_nominal_to_phrase_never_fires(text):
    assert find_evaluative_head(text) is None, f"false fire on: {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "It is a disgrace to admit this now.",
        "It is a scandal to pretend otherwise.",
    ],
)
def test_round4_measured_recall_cost_of_the_head_class_split(text):
    """ACCEPTED COST, pinned so it stays visible rather than becoming folklore.

    A NOMINAL head with a genuine bare-`to` infinitive no longer fires, because
    the nominal frame drops the bare-`to` arm entirely. This is the price of
    closing the 16/16 false-fire class above, and it is the right way round: a
    miss is today's behaviour, a false fire is new behaviour that rewrites the
    user's claim set. Adjectival heads keep the bare-`to` arm and are unaffected.
    """
    assert find_evaluative_head(text) is None


def test_round4_smart_quotes_are_normalised():
    """`‘’` were missing while `“”` were handled — an unintended asymmetry, and
    smart quotes are ubiquitous in fetched HTML."""
    assert find_evaluative_head("The scheme is a ‘disaster’.") is not None
    assert find_evaluative_head("The scheme is a “disaster” relief fund.") is None
    # Smart apostrophes in possessives must survive normalisation.
    head = find_evaluative_head("Lloyd’s handling of it was a disgrace.")
    assert head is not None and head.head == "disgrace"


@pytest.mark.parametrize(
    "text",
    [
        'He said. "The thing is a disaster."',
        'The minister reported record figures. "The procurement round was a fiasco."',
    ],
)
def test_known_limitation_quoted_speech_after_attribution_still_fires(text):
    """KNOWN LIMITATION, pinned so it is visible rather than folklore.

    The quoted sentence is plausibly reported speech, so suppression would be
    correct — but the attribution sits in the PREVIOUS sentence and the guard is
    sentence-local by design (making it cross-sentence would suppress any
    article that quotes anyone). Round 5 tried to reach this by splitting before
    stripping quotes; that cost two safe behaviours and was reverted.

    Belongs to the already-open attribution-leak class, which is a category
    error (reported speech treated as authorial), NOT the over-correction risk
    that governs this module. Deliberately not chased at round 6 of a loop where
    every added cleverness has opened a new hole.
    """
    head = find_evaluative_head(text)
    assert head is not None  # documents current behaviour, not desired behaviour


# ── Regression: re-verification round 5 (2026-07-26) ───────────────────────
# The bare-`to` complement arm is GONE for both head classes. It asked "is the
# word after `to` a verb?", which a regex cannot decide; four attempts to police
# it each closed the witnessed instances and left the class open.


@pytest.mark.parametrize(
    "text",
    [
        # Experiencer PPs — these disproved the premise the head-class split
        # rested on: an adjectival head CAN take a `to`-PP after all.
        "It is outrageous to me.",
        "It is appalling to farmers.",
        "It is abhorrent to many.",
        "It is immoral to some.",
        "It is unethical to us.",
        "It is deplorable to them.",
        "It is indefensible to anyone paying attention.",
        # `_DET` restored as a narrowing lookahead inside `for … to`.
        "It is a disaster for farmers to the north.",
        "It is a scandal for the club to the tune of 20m.",
        "It is a disaster for the region to the east.",
        # Abbreviation + quote must not split and strand the attribution guard.
        'According to the NAO, the U.S. "rollout" was a disaster.',
        'Critics said the U.K. "response" has been a disaster.',
    ],
)
def test_round5_residuals_never_fire(text):
    assert find_evaluative_head(text) is None, f"false fire on: {text!r}"


@pytest.mark.parametrize(
    "text,expected_head,expected_shape",
    [
        # Both live witnesses survive the removal of the bare-`to` arm.
        (
            "It is indefensible for a government to fund homeopathy with public money.",
            "indefensible",
            "extraposed",
        ),
        ("The learning-styles theory is indefensible.", "indefensible", "predicative"),
        # `that` complements, both head classes, through the unified pattern.
        ("It is a disgrace that the fund was cut.", "disgrace", "extraposed"),
        ("It is scandalous that the fund was cut.", "scandalous", "extraposed"),
        (
            "It is unconscionable for a regulator to allow it.",
            "unconscionable",
            "extraposed",
        ),
    ],
)
def test_round5_must_fire_survives_the_arm_removal(text, expected_head, expected_shape):
    head = find_evaluative_head(text)
    assert head is not None, f"must-fire missed: {text!r}"
    assert head.head == expected_head
    assert head.shape == expected_shape


@pytest.mark.parametrize(
    "text",
    [
        "It is shameful to admit, but sales rose 4%.",
        "It is immoral to test cosmetics on animals.",
        "It is indefensible to withhold the findings.",
    ],
)
def test_round5_measured_recall_cost_of_removing_the_bare_to_arm(text):
    """ACCEPTED COST, pinned. A genuine bare-`to` infinitive now misses for BOTH
    head classes. Recall only — proved byte-for-byte in round 2 that a miss is
    identical to flag-OFF — and neither live witness uses this arm."""
    assert find_evaluative_head(text) is None


def test_prefix_sharing_heads_resolve_to_the_right_head():
    """`disgrace`/`disgraceful` and `scandal`/`scandalous` span both lists; the
    unified pattern must still pick the right one."""
    assert find_evaluative_head("The response is scandalous.").head == "scandalous"
    assert find_evaluative_head("The response was a scandal.").head == "scandal"
    assert (
        find_evaluative_head("It is scandalous that x happened.").head == "scandalous"
    )
    assert find_evaluative_head("It is a scandal that x happened.").head == "scandal"


# ── Regression: re-verification round 6 (2026-07-26) ───────────────────────
# The nominal frame now takes `that` ONLY. Its `for … to` arm leaked 2/10 on
# determiner-less objects, held up only by the `_DET` blocklist — the same
# open-set guard that failed three times. The nominal frame now contains no
# word-list dependency at all.


@pytest.mark.parametrize(
    "text",
    [
        "It is a scandal for people living next to landfill sites.",
        "It was a catastrophe for staff senior to middle management.",
        "It was a catastrophe for those closest to the blast.",
        "It is a scandal for people living close to the site.",
        "It was a disaster for communities next to the river.",
        "It is a triumph for athletes new to the sport.",
        "It was a betrayal for workers loyal to the firm.",
        "It is a disgrace for families adjacent to the works.",
        "It is a scandal for residents exposed to the fumes.",
        "It was a disaster for towns vulnerable to the surge.",
    ],
)
def test_round6_nominal_for_to_arm_never_fires(text):
    assert find_evaluative_head(text) is None, f"false fire on: {text!r}"


@pytest.mark.parametrize(
    "text",
    [
        "It is a scandal for ministers to ignore the findings.",
        "It is a disgrace for a regulator to sit on this.",
    ],
)
def test_round6_measured_recall_cost_of_nominal_that_only(text):
    """ACCEPTED COST. A genuine NOMINAL `for … to` infinitive now misses.
    Recall only, and no live witness uses it — P13 (b) is ADJECTIVAL `for … to`,
    which is untouched and pinned by criterion 2."""
    assert find_evaluative_head(text) is None


def test_round6_adjectival_for_to_still_carries_the_p13_witness():
    """The adjectival `for … to` arm is load-bearing for a LIVE witness, which
    is why it keeps `_DET` rather than being dropped like the nominal twin."""
    head = find_evaluative_head(
        "It is indefensible for a government to fund homeopathy with public money."
    )
    assert head == EvaluativeHead(head="indefensible", shape="extraposed")
