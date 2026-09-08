export interface VerifyResult {
  valid: boolean;
  checkId?: string;
  revisionId?: string;
  signedAt?: string;
  kid?: string;
  executedTier?: string;
  pipelineFingerprint?: string;
  reason?: string;
}

export async function getVerification(id: string, revision?: string): Promise<VerifyResult | null> {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const path = `/verify/${encodeURIComponent(id)}${revision ? `/revisions/${encodeURIComponent(revision)}` : ''}`;
  try {
    const res = await fetch(`${apiUrl}${path}`, { cache: 'no-store' });
    if (!res.ok) return null;
    const result: VerifyResult = await res.json();
    if (revision && (result.checkId !== id || result.revisionId !== revision)
        && !(result.valid === false && result.reason === 'not_found'
          && !result.checkId && !result.revisionId)) return null;
    return result;
  } catch { return null; }
}
