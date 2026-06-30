'use client';

import type { ElementBasis } from '@shared/types';
import { evidenceQualityNote, QualityNote } from '@/lib/support-structure';

/**
 * Per-element source-quality note. Surfaces when the SUPPORTING or CHALLENGING
 * evidence for a sub-element looks thin or echoey, so weak sourcing is visible
 * instead of being taken at face value.
 *
 * No-verdict lock: grey only (never green/red/amber), and the wording describes
 * the SOURCES, never the claim's truth. Renders nothing when both sides are
 * healthy or the basis is absent (older checks).
 */
interface EvidenceQualityNoteProps {
  basis?: ElementBasis | null;
}

function NoteRow({ side, note }: { side: string; note: QualityNote }) {
  return (
    <span
      title={note.detail}
      className="inline-flex items-center gap-1.5 font-mono text-[10px] text-zinc-500"
    >
      <span aria-hidden className="text-zinc-400">
        &#9651;
      </span>
      <span className="text-zinc-400 uppercase tracking-wider">{side}</span>
      <span className="text-zinc-300">&middot;</span>
      <span>{note.label}</span>
    </span>
  );
}

export function EvidenceQualityNote({ basis }: EvidenceQualityNoteProps) {
  if (!basis) return null;

  const support = evidenceQualityNote(basis.support_structure);
  const challenge = evidenceQualityNote(basis.challenge_structure);
  if (!support && !challenge) return null;

  return (
    <div className="flex flex-col gap-0.5 mt-1.5">
      {support && <NoteRow side="Support" note={support} />}
      {challenge && <NoteRow side="Challenge" note={challenge} />}
    </div>
  );
}
