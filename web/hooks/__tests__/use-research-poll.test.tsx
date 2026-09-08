import { act, renderHook } from '@testing-library/react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { useResearchPoll } from '../use-research-poll';

const mocks = vi.hoisted(() => ({ getToken: vi.fn(), getStatus: vi.fn() }));
vi.mock('@clerk/nextjs', () => ({ useAuth: () => ({ getToken: mocks.getToken }) }));
vi.mock('@/lib/api', () => ({ apiClient: { getResearchStatus: mocks.getStatus } }));

beforeEach(() => {
  vi.useFakeTimers();
  mocks.getToken.mockReset().mockResolvedValue('fresh');
  mocks.getStatus.mockReset();
});
afterEach(() => vi.useRealTimers());

it('starts once, pins the operation and counts a bundled result once', async () => {
  const completed = vi.fn();
  const start = vi.fn().mockResolvedValue({ elementIds: ['e1', 'e2'], operationId: 'operation' });
  mocks.getStatus.mockResolvedValue({ operationId: 'operation', status: 'completed', newEvidenceCount: 3 });
  const { result } = renderHook(() => useResearchPoll({ checkId: 'c', claimId: 'cl', token: 'token', onComplete: completed }));
  await act(async () => { await Promise.all([result.current.run(start), result.current.run(start)]); });
  expect(start).toHaveBeenCalledTimes(1);
  expect(start.mock.calls[0][1]).toBeTruthy();
  await act(async () => { await vi.advanceTimersByTimeAsync(2500); });
  expect(mocks.getStatus).toHaveBeenCalledExactlyOnceWith('c', 'cl', 'e1', 'fresh', 'operation');
  expect(result.current.newCount).toBe(3);
  expect(completed).toHaveBeenCalledTimes(1);
});

it('does not overlap polls or apply an old response after reset', async () => {
  let finish!: (value: unknown) => void;
  mocks.getStatus.mockReturnValue(new Promise(resolve => { finish = resolve; }));
  const completed = vi.fn();
  const { result } = renderHook(() => useResearchPoll({ checkId: 'c', claimId: 'cl', token: 'token', onComplete: completed }));
  await act(async () => { await result.current.run(async () => ({ elementIds: ['e1'], operationId: 'old' })); });
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(mocks.getStatus).toHaveBeenCalledTimes(1);
  act(() => result.current.reset());
  await act(async () => { finish({ status: 'completed', newEvidenceCount: 5 }); });
  expect(result.current.status).toBe('idle');
  expect(completed).not.toHaveBeenCalled();
});

it('reuses the key after an uncertain start response', async () => {
  const start = vi.fn().mockRejectedValueOnce(new Error('Connection lost')).mockResolvedValueOnce({ elementIds: ['e1'], operationId: 'original' });
  const { result, unmount } = renderHook(() => useResearchPoll({ checkId: 'c', claimId: 'cl', token: 'token' }));
  await act(async () => { await result.current.run(start); });
  act(() => result.current.reset());
  await act(async () => { await result.current.run(start); });
  expect(start.mock.calls[0][1]).toBe(start.mock.calls[1][1]);
  unmount();
  await act(async () => { await vi.advanceTimersByTimeAsync(10000); });
  expect(mocks.getStatus).not.toHaveBeenCalled();
});
