import { act, renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { useState } from 'react';
const mocks = vi.hoisted(() => ({ getToken: vi.fn().mockResolvedValue('fresh-token'), getCheckById: vi.fn() }));
vi.mock('@clerk/nextjs', () => ({ useAuth: () => ({ getToken: mocks.getToken }) }));
vi.mock('@/lib/api', () => ({ apiClient: { getCheckById: mocks.getCheckById } }));
import { useReportRefresh } from '@/hooks/use-report-refresh';

describe('completed research refresh', () => {
  it('replaces client report data and retains the last report on a failed refresh, with retry', async () => {
    mocks.getCheckById.mockResolvedValueOnce({ revision: 2 }).mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ revision: 3 });
    const { result } = renderHook(() => {
      const [report, setReport] = useState({ revision: 1 });
      return { report, ...useReportRefresh('check', setReport) };
    });
    await act(() => result.current.refresh());
    expect(result.current.report.revision).toBe(2);
    expect(mocks.getCheckById).toHaveBeenCalledWith('check', 'fresh-token');
    await act(() => result.current.refresh());
    expect(result.current.report.revision).toBe(2);
    expect(result.current.error).toContain('could not be loaded');
    await act(() => result.current.refresh());
    expect(result.current.report.revision).toBe(3);
    expect(result.current.error).toBeNull();
  });

  it('ignores an older response that arrives after a newer refresh', async () => {
    let resolveOld!: (value: unknown) => void;
    mocks.getCheckById.mockImplementationOnce(() => new Promise(resolve => { resolveOld = resolve; })).mockResolvedValueOnce({ revision: 3 });
    const update = vi.fn();
    const { result } = renderHook(() => useReportRefresh('check', update));
    let old!: Promise<void>;
    await act(async () => { old = result.current.refresh(); await Promise.resolve(); });
    await act(() => result.current.refresh());
    await act(async () => { resolveOld({ revision: 2 }); await old; });
    expect(update).toHaveBeenCalledTimes(1);
    expect(update).toHaveBeenCalledWith({ revision: 3 });
  });
});
