"""Opt-in judgement instructions; these do not certify semantic correctness."""

APPLICABILITY_RULES = """
ELEMENT AND TIME APPLICABILITY:
- Judge each source against the specific element being mapped. Identify the
  proposition, measure, population, and time asserted by that element before
  choosing a relationship. A discrepancy about a sibling element is not a
  challenge to this element. Shared subject matter alone is context.
- Supports/challenges require evidence for/against this element's proposition.
  For challenges, explain the incompatible proposition actually stated by the
  source. Missing information is not contradiction. A quotation's exact presence
  proves text occurrence, not that it entails the chosen relationship.
- Preserve the element's quantifiers and full conclusion. Evidence that a
  mechanism reduces a problem does not support a claim that it eliminates all
  occurrences. Read the complete supplied excerpts before selecting a quote:
  an explicit exception can challenge a universal claim even when the preceding
  sentence describes the usual benefit. Do not quote the benefit as support for
  a universal conclusion while ignoring its stated exception. Explain how the
  quotation bears on the complete element, not just its premise or topic.
- For a time-qualified changing fact, distinguish when the fact applied from
  when the page was published, updated, retrieved, or displayed a clock. None of
  those page dates alone establishes the fact's effective date or interval.
  Undated current wording cannot establish a historical value merely because a
  nearby date matches, precedes, or follows the element's date. Do not silently
  carry a value forward or backward across an unestablished interval.
- Directional temporal evidence needs source wording that establishes the fact
  at the relevant time, or an explicitly applicable interval. A proposed or
  future change does not establish that it took effect; preserve negation and
  conditions. Publication precision and captured date candidates are not an
  applicability decision. If applicability is unestablished, use context and
  explain the missing temporal link rather than choosing supports/challenges.
- These limits apply symmetrically to support and challenge. Preserve direct
  evidence of an explicitly dated change and direct evidence about a timeless
  proposition; do not demand a date for an element that has no time constraint.
"""
