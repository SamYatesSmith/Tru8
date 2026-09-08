// Stored snapshots deliberately retain the backend's original snake_case fields.
export interface RevisionSummary {
  id: string;
  operationId: string;
  phase: 'before' | 'after';
  createdAt: string;
  signedAt: string | null;
}

export interface RevisionRef {
  evidence_id: string;
  relationship: string;
  reasoning?: string | null;
  citations?: { quote: string }[];
}

export interface RevisionElement {
  element_id: string;
  description: string;
  state?: string;
  uncertainty?: string | null;
  evidence_refs?: RevisionRef[];
}

export interface RevisionSnapshot {
  format_version: number;
  check: { id: string };
  manifest?: Record<string, unknown> | null;
  claims: {
    id: string;
    text: string;
    claimMap?: { elements?: RevisionElement[] } | null;
    evidence: { id?: string; evidence_id?: string; title?: string; url?: string }[];
  }[];
}

export interface ReportRevision {
  id: string;
  phase: 'before' | 'after';
  snapshot: RevisionSnapshot;
}

export function revisionChanges(before: RevisionSnapshot, after: RevisionSnapshot): string[] {
  const changes: string[] = [];
  const oldClaims = new Map(before.claims.map(c => [c.id, c]));
  const newClaims = new Map(after.claims.map(c => [c.id, c]));
  for (const id of Array.from(new Set([...Array.from(oldClaims.keys()), ...Array.from(newClaims.keys())]))) {
    const oldClaim = oldClaims.get(id), newClaim = newClaims.get(id);
    if (!oldClaim || !newClaim) {
      changes.push(`${oldClaim ? 'Removed' : 'Added'} claim: ${(newClaim || oldClaim)!.text}`);
      continue;
    }
    if (oldClaim.text !== newClaim.text) changes.push(`Claim wording changed: “${oldClaim.text}” → “${newClaim.text}”.`);
    const oldElements = new Map((oldClaim.claimMap?.elements || []).map(e => [e.element_id, e]));
    const newElements = new Map((newClaim.claimMap?.elements || []).map(e => [e.element_id, e]));
    for (const eid of Array.from(new Set([...Array.from(oldElements.keys()), ...Array.from(newElements.keys())]))) {
      const old = oldElements.get(eid), next = newElements.get(eid);
      const label = (next || old)!.description;
      if (!old || !next) { changes.push(`${old ? 'Removed' : 'Added'} element: ${label}`); continue; }
      if (old.description !== next.description) changes.push(`Element wording: “${old.description}” → “${next.description}”.`);
      if (old.state !== next.state) changes.push(`${label}: state ${old.state || 'unavailable'} → ${next.state || 'unavailable'}.`);
      if (old.uncertainty !== next.uncertainty) changes.push(`${label}: uncertainty note changed.`);
      const oldRefs = new Map((old.evidence_refs || []).map(r => [r.evidence_id, r]));
      const newRefs = new Map((next.evidence_refs || []).map(r => [r.evidence_id, r]));
      for (const sourceId of Array.from(new Set([...Array.from(oldRefs.keys()), ...Array.from(newRefs.keys())]))) {
        const previous = oldRefs.get(sourceId), current = newRefs.get(sourceId);
        const source = newClaim.evidence.find(e => (e.evidence_id || e.id) === sourceId)
          || oldClaim.evidence.find(e => (e.evidence_id || e.id) === sourceId);
        const sourceName = source?.title || sourceId;
        if (!previous || !current || previous.relationship !== current.relationship) {
          changes.push(`${label} — ${sourceName}: ${previous?.relationship || 'not linked'} → ${current?.relationship || 'not linked'}.`);
        } else if (previous.reasoning !== current.reasoning || JSON.stringify(previous.citations) !== JSON.stringify(current.citations)) {
          changes.push(`${label} — ${sourceName}: explanation or quotation changed; relationship remains ${current.relationship}.`);
        }
      }
    }
  }
  return changes;
}

export function safeSourceUrl(url?: string): string | undefined {
  try {
    const parsed = new URL(url || '');
    return ['https:', 'http:'].includes(parsed.protocol) ? parsed.href : undefined;
  } catch { return undefined; }
}
