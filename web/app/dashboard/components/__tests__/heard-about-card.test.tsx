import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi, beforeEach } from 'vitest';

const mocks = vi.hoisted(() => ({
  getToken: vi.fn(async () => 'tok'),
  recordHeardAbout: vi.fn(async () => ({ recorded: true, reason: null })),
}));
vi.mock('@clerk/nextjs', () => ({ useAuth: () => ({ getToken: mocks.getToken }) }));
vi.mock('@/lib/api', () => ({ apiClient: { recordHeardAbout: mocks.recordHeardAbout } }));
import { HeardAboutCard } from '../heard-about-card';

describe('HeardAboutCard', () => {
  beforeEach(() => mocks.recordHeardAbout.mockClear());

  it('sends nothing until an answer is chosen', () => {
    render(<HeardAboutCard />);
    expect((screen.getByRole('button', { name: 'Send' }) as HTMLButtonElement).disabled).toBe(true);
  });

  it('sends the chosen code and thanks the user', async () => {
    render(<HeardAboutCard />);
    fireEvent.change(screen.getByLabelText('How did you hear about Tru8?'), { target: { value: 'linkedin' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(screen.getByRole('status')).toBeTruthy());
    expect(mocks.recordHeardAbout).toHaveBeenCalledWith('linkedin', null, 'tok');
  });

  it('asks where only for "other" and sends that text', async () => {
    render(<HeardAboutCard />);
    expect(screen.queryByLabelText('Where did you hear about Tru8?')).toBeNull();
    fireEvent.change(screen.getByLabelText('How did you hear about Tru8?'), { target: { value: 'other' } });
    fireEvent.change(screen.getByLabelText('Where did you hear about Tru8?'), { target: { value: 'a podcast' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(mocks.recordHeardAbout).toHaveBeenCalledWith('other', 'a podcast', 'tok'));
  });

  it('skip records "skipped" and hides the card', async () => {
    const { container } = render(<HeardAboutCard />);
    fireEvent.click(screen.getByRole('button', { name: 'Skip' }));
    await waitFor(() => expect(container.innerHTML).toBe(''));
    expect(mocks.recordHeardAbout).toHaveBeenCalledWith('skipped', null, 'tok');
  });

  it('a failed save hides the card instead of nagging', async () => {
    mocks.recordHeardAbout.mockRejectedValueOnce(new Error('down'));
    const { container } = render(<HeardAboutCard />);
    fireEvent.change(screen.getByLabelText('How did you hear about Tru8?'), { target: { value: 'search' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send' }));
    await waitFor(() => expect(container.innerHTML).toBe(''));
  });
});
