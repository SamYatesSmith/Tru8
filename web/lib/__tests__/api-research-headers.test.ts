import { afterEach, expect, it, vi } from 'vitest';
import { apiClient } from '../api';

afterEach(() => vi.unstubAllGlobals());

it('preserves the same research idempotency key and auth header across retries', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ status: 'pending' }) });
  vi.stubGlobal('fetch', fetchMock);
  await apiClient.startElementResearch('check', 'claim', 'element', 'owner-token', 'same-operation');
  await apiClient.startElementResearch('check', 'claim', 'element', 'owner-token', 'same-operation');
  for (const call of fetchMock.mock.calls) {
    const options = call[1] as RequestInit;
    const headers = new Headers(options.headers);
    expect(headers.get('Idempotency-Key')).toBe('same-operation');
    expect(headers.get('Authorization')).toBe('Bearer owner-token');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(options.method).toBe('POST');
  }
});

it('encodes revision identities and authenticates read-only revision requests', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ revisions: [] }) });
  vi.stubGlobal('fetch', fetchMock);
  await apiClient.getReportRevision('check/id', 'revision/id', 'owner-token');
  expect(fetchMock.mock.calls[0][0]).toContain('/checks/check%2Fid/revisions/revision%2Fid');
  expect(new Headers(fetchMock.mock.calls[0][1].headers).get('Authorization')).toBe('Bearer owner-token');
});
