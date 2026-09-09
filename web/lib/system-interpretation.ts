/**
 * Public gate for "System interpretation" text — the mapper's per-reference
 * `reasoning` and the scope review's `reasoning`. Both are model-written and
 * undefined by their prompts, so, like the element caveat (Fix 1,
 * lib/element-caveat.ts), they mix genuine explanations with adjudications
 * ("the evidence consistently refutes…"). Verdict language must never reach
 * the public record.
 *
 * FAIL-CLOSED on the public page (readOnly): a sentence that trips the shared
 * verdict test is withheld and the reader is told so — never rewritten, never
 * silently dropped as "no explanation was saved". The owner's dashboard shows
 * the sentence unchanged; the owner is judging the system, not being told a
 * verdict by it. Founder decision 2026-09-09.
 */
import { containsVerdictLanguage } from './element-caveat';

export const WITHHELD_NOTE = 'withheld from the public record (adjudicating wording).';
export const MISSING_NOTE = 'No relationship explanation was saved for this record.';

export function interpretationNote(
  reasoning: string | null | undefined,
  readOnly: boolean | undefined
): string {
  const text = typeof reasoning === 'string' ? reasoning.trim() : '';
  if (!text) return MISSING_NOTE;
  if (readOnly && containsVerdictLanguage(text)) return WITHHELD_NOTE;
  return text;
}
