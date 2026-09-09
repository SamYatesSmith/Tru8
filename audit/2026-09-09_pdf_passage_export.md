# Passage-backed PDF export — 9 September 2026

Track Q step 8, scoped by the founder on 2026-09-09 to **export only**: no new UI state, no database change. Astra's acceptance for the step: "a reviewer can move from a directional label to its exact basis in one interaction … a paraphrase is never rendered as a quotation … old records must not be retroactively described as having passage verification they never received."

## What the JSON already carries

There is no separate JSON export; the check response (`GET /checks/{id}`, and the public variant behind `/r/`) is the JSON, and since Track Q it carries `citations` on each reference, `textProvenance` on each evidence item (captured passages with offsets and the extraction hash), and every scope receipt in the element `basis`. Nothing was added there.

## What the PDF gains

Under each element, after the caveat and quality notes:

- **Quoted basis.** For a reference whose `citations` re-validate against the captured extraction they name (same `extraction_sha256`, passage id in the retained set, quote literally present), the quote prints in grey with its source number and relationship, labelled "quoted from the captured extraction". The check is the backend's own `validate_citations` plus a hash comparison, the same rule the web's `citationText` applies. A paraphrase, an invented quote, a citation against an older extraction, or a record captured before passages existed prints nothing; the relationship stays a system interpretation.
- **Scope notes.** Every reference a mechanical gate or the scope review re-labelled to context, with the receipt's reason in plain words: "Source 2 retained as context — read as supports; another host of a study already counted (counted as source 1)". Labels come from a fixed table keyed on the receipt key; the only model-written text that can reach the page is the scope review's `reasoning`, and it passes the verdict-language rule.

## Verdict language, parity-locked

The PDF used to print every note unfiltered, which was acceptable while it printed only mechanical receipts. Now that it prints scope-review reasoning it applies the Fix 1 rule: `app/utils/verdict_language.py` carries the two regexes from `web/lib/element-caveat.ts` and `tests/unit/test_verdict_language_parity.py` reads both files and fails if either side drifts. An adjudicating sentence prints as "withheld from the public record (adjudicating wording)." and is never rewritten.

## Evidence

`tests/unit/test_pdf_report_render.py`: a validated quote renders with its source number; a paraphrase and a stale-hash citation render nothing; scope receipts render as neutral notes and a verdict-worded scope-review reason is withheld. The standing PDF guards (no verdict colours, neutral glyphs, brand chassis) still pass. Whole backend suite in the commit message.

## Not done

Nothing in the PDF names which passages were *inspected* and found unrelated (the pair coverage counts stay in the app's Gaps view), and the source ledger entries themselves do not repeat the quotes. Both are small follow-ups if a reader asks for them.
