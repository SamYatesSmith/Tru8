/**
 * Element caveat gate — decides whether the mapper's per-element `uncertainty`
 * sentence may be shown on a reader-facing surface (the ELEMENTS EXAMINED
 * roster on /r/ and the dashboard).
 *
 * The field is model-written and undefined by the prompt ("one sentence or
 * null"), so it mixes two kinds of sentence: a genuine limit on the evidence
 * ("an estimated loss, not official outturn data") and an adjudication that
 * restates the badge ("the evidence consistently refutes this element").
 * The second kind is verdict language and must never reach a public page.
 *
 * FAIL-CLOSED by design: hiding a real caveat leaves the page as it was;
 * printing an adjudication breaks the no-verdict lock. Every rule here errs
 * towards hiding. Suppression is total — we never rewrite the sentence.
 * The PDF continues to print every note unfiltered.
 *
 * Known residual: an adjudication phrased without a listed word passes. The
 * source fix is a prompt definition of the field (pipeline work). The corpus
 * of real stored sentences is pinned in element-caveat.test.ts so drift in
 * either direction fails a test.
 *
 * Design: audit/2026-09-02_fix1_element_caveat_render_design.md
 */

const SENTINELS = new Set(['null', 'none', 'n/a', 'na', 'nil', 'undefined']);

/** Words that adjudicate the claim rather than describe a limit of the evidence. */
const VERDICT_WORD_RE =
  /\b(refut\w*|false|true|prove[sdn]?|proven|confirm\w*|debunk\w*|verdict|incorrect|correct|wrong|fact-?check\w*)\b/i;

/**
 * "evidence strongly suggests…", "sources clearly show…" — an intensifier
 * attached to the evidence noun is the model summarising the direction it
 * has just assigned. A plain "the evidence indicates X is an amplifying
 * mechanism" has no intensifier and is a limit, so it passes.
 */
const INTENSIFIED_EVIDENCE_RE =
  /\b(evidence|sources?|data|studies|research)\b[^.;]{0,40}?\b(strongly|consistently|clearly|overwhelmingly|conclusively|decisively|unambiguously)\b|\b(strong|overwhelming|conclusive|clear|decisive|unambiguous)\s+(evidence|support|challenge)\b/i;

/**
 * Returns the caveat sentence to display, or null when it must not be shown.
 */
export function elementCaveatNote(uncertainty: string | null | undefined): string | null {
  if (typeof uncertainty !== 'string') return null;
  const text = uncertainty.trim();
  if (!text) return null;
  if (SENTINELS.has(text.toLowerCase())) return null;
  if (VERDICT_WORD_RE.test(text)) return null;
  if (INTENSIFIED_EVIDENCE_RE.test(text)) return null;
  return text;
}
