import { afterEach, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { getVerification } from '../report-verification';
import { ReportIdentityNotice } from '@/components/evidence-views/ReportIdentityNotice';

afterEach(() => vi.unstubAllGlobals());

it('verifies the requested revision and rejects an unrelated successful response', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ valid: true, checkId: 'check', revisionId: 'old' }) });
  vi.stubGlobal('fetch', fetchMock);
  expect((await getVerification('check', 'old'))?.valid).toBe(true);
  expect(fetchMock.mock.calls[0][0]).toContain('/verify/check/revisions/old');
  expect(await getVerification('check', 'different')).toBeNull();
});

it('exposes a retained identity without claiming a signature was verified', () => {
  render(<ReportIdentityNotice checkId="check" identity={{ basis: 'evidence_snapshot_v1', status: 'retained', revisionId: 'old', contentHash: 'a'.repeat(64) }} />);
  expect(screen.getByRole('link').getAttribute('href')).toBe('/verify/check?revision=old');
  expect(screen.getByText(/live report can change/)).toBeTruthy();
});

it('does not invent a retained revision for unmatched content', () => {
  render(<ReportIdentityNotice checkId="check" identity={{ basis: 'evidence_snapshot_v1', status: 'unretained', revisionId: null, contentHash: 'b'.repeat(64) }} />);
  expect(screen.getByText(/No matching retained revision/)).toBeTruthy();
  expect(screen.queryByRole('link')).toBeNull();
});

it('preserves a missing-revision result rather than reporting a network failure', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, json: async () => ({ valid: false, reason: 'not_found' }) }));
  expect((await getVerification('check', 'missing'))?.reason).toBe('not_found');
});
