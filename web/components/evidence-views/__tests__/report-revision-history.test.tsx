import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ReportRevisionHistory } from '../ReportRevisionHistory';
import { revisionChanges, safeSourceUrl } from '@/lib/report-revisions';
import type { ReportRevision, RevisionSnapshot } from '@/lib/report-revisions';

const mocks = vi.hoisted(() => ({ token: vi.fn(), list: vi.fn(), read: vi.fn() }));
vi.mock('@clerk/nextjs', () => ({ useAuth: () => ({ getToken: mocks.token }) }));
vi.mock('@/lib/api', () => ({ apiClient: { getReportRevisions: mocks.list, getReportRevision: mocks.read } }));

function snapshot(relationship = 'supports'): RevisionSnapshot {
  return { format_version: 1, check: { id: 'check' }, claims: [{ id: 'c1', text: 'A test claim',
    claimMap: { elements: [{ element_id: 'e1', description: 'Test element', state: 'unresolved',
      evidence_refs: [{ evidence_id: 's1', relationship, reasoning: 'Stored explanation' }] }] },
    evidence: [{ evidence_id: 's1', title: 'Saved source', url: 'https://example.invalid/source' },
      { evidence_id: 'unlinked', title: 'Unlinked source' }],
  }] };
}

const summaries = [
  { id: 'before', operationId: 'op', phase: 'before', createdAt: '2030-04-02T10:00:00', signedAt: null },
  { id: 'after', operationId: 'op', phase: 'after', createdAt: '2030-04-02T10:00:01', signedAt: null },
];

beforeEach(() => {
  mocks.token.mockReset().mockResolvedValue('owner-token');
  mocks.list.mockReset().mockResolvedValue({ revisions: summaries });
  mocks.read.mockReset().mockImplementation(async (_check: string, id: string): Promise<ReportRevision> => ({
    id, phase: id === 'after' ? 'after' : 'before', snapshot: snapshot(id === 'after' ? 'context' : 'supports'),
  }));
});

async function open() {
  fireEvent.click(screen.getByRole('button', { name: 'Revision history' }));
  await screen.findByLabelText('Revision to inspect');
}

it('loads owner history on demand and compares the matching strengthening snapshots', async () => {
  render(<ReportRevisionHistory checkId="check" />);
  expect(mocks.list).not.toHaveBeenCalled();
  await open();
  fireEvent.change(screen.getByLabelText('Revision to inspect'), { target: { value: 'after' } });
  expect(await screen.findByText('Retained revision: after')).toBeTruthy();
  expect(screen.getByText(/Saved source: supports → context/)).toBeTruthy();
  expect(screen.getByText('Unlinked source')).toBeTruthy();
  expect(screen.getByText(/No signature was stored/)).toBeTruthy();
  expect(mocks.read).toHaveBeenCalledWith('check', 'before', 'owner-token');
});

it('does not manufacture missing history', async () => {
  mocks.list.mockResolvedValue({ revisions: [] });
  render(<ReportRevisionHistory checkId="check" />);
  fireEvent.click(screen.getByRole('button', { name: 'Revision history' }));
  expect(await screen.findByText(/Earlier versions cannot be reconstructed/)).toBeTruthy();
});

it('retries failed details without treating the signature as verified', async () => {
  mocks.read.mockRejectedValueOnce(new Error('offline'));
  render(<ReportRevisionHistory checkId="check" />);
  await open();
  fireEvent.change(screen.getByLabelText('Revision to inspect'), { target: { value: 'before' } });
  fireEvent.click(await screen.findByRole('button', { name: 'Retry revision' }));
  expect(await screen.findByText('Retained revision: before')).toBeTruthy();
});

it('ignores a late response for a previously selected revision', async () => {
  let resolveOld!: (value: ReportRevision) => void;
  mocks.read.mockImplementation((_check: string, id: string) => id === 'before'
    ? new Promise(resolve => { resolveOld = resolve; })
    : Promise.resolve({ id, phase: 'after', snapshot: snapshot('context') }));
  render(<ReportRevisionHistory checkId="check" />);
  await open();
  fireEvent.change(screen.getByLabelText('Revision to inspect'), { target: { value: 'before' } });
  await waitFor(() => expect(mocks.read).toHaveBeenCalledWith('check', 'before', 'owner-token'));
  fireEvent.change(screen.getByLabelText('Revision to inspect'), { target: { value: 'after' } });
  fireEvent.change(screen.getByLabelText('Compare from'), { target: { value: '' } });
  await screen.findByText('Retained revision: after');
  await act(async () => resolveOld({ id: 'before', phase: 'before', snapshot: snapshot() }));
  expect(screen.queryByText('Retained revision: before')).toBeNull();
  expect(screen.getByText('Retained revision: after')).toBeTruthy();
});

it('rejects a mismatched report response', async () => {
  mocks.read.mockResolvedValue({ id: 'before', phase: 'before', snapshot: { ...snapshot(), check: { id: 'other' } } });
  render(<ReportRevisionHistory checkId="check" />);
  await open();
  fireEvent.change(screen.getByLabelText('Revision to inspect'), { target: { value: 'before' } });
  expect(await screen.findByRole('alert')).toBeTruthy();
  expect(screen.queryByText('A test claim')).toBeNull();
});

it('compares claim and element identities rather than array position', () => {
  const old = snapshot();
  const next = structuredClone(old);
  next.claims.unshift({ id: 'new', text: 'Added claim', evidence: [] });
  next.claims[1].claimMap!.elements![0].evidence_refs = [];
  const changes = revisionChanges(old, next);
  expect(changes).toContain('Added claim: Added claim');
  expect(changes).toContain('Test element — Saved source: supports → not linked.');
});

it('records explanation-only changes and refuses unsafe source links', () => {
  const old = snapshot(), next = snapshot();
  next.claims[0].claimMap!.elements![0].evidence_refs![0].reasoning = 'New reason';
  expect(revisionChanges(old, next)[0]).toContain('explanation or quotation changed');
  expect(safeSourceUrl('javascript:alert(1)')).toBeUndefined();
  expect(safeSourceUrl('https://example.invalid')).toBe('https://example.invalid/');
});
