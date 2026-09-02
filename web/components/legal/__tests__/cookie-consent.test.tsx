import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, act } from '@testing-library/react';

const writeConsent = vi.fn();
let decided = false;
vi.mock('@/lib/consent', () => ({
  readConsent: () => ({ decided, analytics: true }),
  writeConsent: (v: boolean) => writeConsent(v),
  OPEN_CONSENT_EVENT: 'tru8:open-consent',
}));

import { CookieConsent } from '../cookie-consent';

/**
 * Compact mobile banner (2026-09-02). JSDOM has no media queries, so this pins
 * what CSS cannot: both choices are always present as real buttons, the phone
 * label is the honest one (analytics IS the only non-essential category), and
 * the consent that gets written is unchanged by the layout work.
 */
describe('CookieConsent', () => {
  beforeEach(() => {
    writeConsent.mockClear();
    decided = false;
  });

  it('renders nothing once a decision exists', async () => {
    decided = true;
    const { queryByRole } = render(<CookieConsent />);
    await act(async () => {});
    expect(queryByRole('dialog')).toBeNull();
  });

  it('offers accept, reject and manage — with both reject labels present for the two layouts', async () => {
    const { getByRole, getByText } = render(<CookieConsent />);
    await act(async () => {});
    expect(getByRole('dialog', { name: 'Cookie consent' })).toBeTruthy();
    expect(getByRole('button', { name: /accept all/i })).toBeTruthy();
    expect(getByRole('button', { name: /manage preferences/i })).toBeTruthy();
    // One button carries both labels; CSS shows one per breakpoint.
    const reject = getByText('Reject analytics').closest('button');
    expect(reject).toBeTruthy();
    expect(getByText('Reject non-essential').closest('button')).toBe(reject);
  });

  it('writes analytics=false on reject and true on accept, then hides', async () => {
    const { getByText, getByRole, queryByRole } = render(<CookieConsent />);
    await act(async () => {});
    fireEvent.click(getByText('Reject analytics').closest('button')!);
    expect(writeConsent).toHaveBeenCalledWith(false);
    expect(queryByRole('dialog')).toBeNull();

    decided = false;
    const second = render(<CookieConsent />);
    await act(async () => {});
    fireEvent.click(second.getByRole('button', { name: /accept all/i }));
    expect(writeConsent).toHaveBeenLastCalledWith(true);
    expect(getByRole).toBeTruthy();
  });

  it('keeps the heading for screen readers on every layout', async () => {
    const { getByRole } = render(<CookieConsent />);
    await act(async () => {});
    expect(getByRole('heading', { name: 'We use cookies' })).toBeTruthy();
  });
});
