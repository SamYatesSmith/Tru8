import type { Evidence, PassageCitation } from '@shared/types';

/** Check against THIS retained source version; offsets use Unicode code points. */
export function citationText(evidence: Evidence, citation: PassageCitation): string | null {
  const capture = evidence.textProvenance;
  if (!capture || capture.version !== 1 || citation.extraction_sha256 !== capture.extraction_sha256) return null;
  const passage = capture.passages.find(p => p.id === citation.passage_id);
  if (!passage || !citation.quote?.trim() || !Number.isInteger(citation.start) || !Number.isInteger(citation.end)) return null;
  if (citation.start < passage.start || citation.end > passage.end || citation.end <= citation.start) return null;
  const text = Array.from(passage.text).slice(citation.start - passage.start, citation.end - passage.start).join('');
  return text === citation.quote ? text : null;
}
