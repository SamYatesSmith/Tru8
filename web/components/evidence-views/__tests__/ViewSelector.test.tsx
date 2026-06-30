import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ViewSelector } from '../ViewSelector';

describe('ViewSelector', () => {
  const defaultProps = {
    mode: 'overview' as const,
    activeTab: 'cartographer',
    onTabChange: vi.fn(),
  };

  it('renders all 6 view tabs', () => {
    render(<ViewSelector {...defaultProps} />);
    // Plain-language labels lead (D-R1); the profession is the subtitle flavour.
    expect(screen.getByText('EVIDENCE')).toBeInTheDocument();
    expect(screen.getByText('SOURCES')).toBeInTheDocument();
    expect(screen.getByText('TIMELINE')).toBeInTheDocument();
    expect(screen.getByText('GAPS')).toBeInTheDocument();
    expect(screen.getByText('MAP')).toBeInTheDocument();
    expect(screen.getByText('VIDEO')).toBeInTheDocument();
  });

  it('calls onTabChange when a tab is clicked', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} onTabChange={onTabChange} />);

    // EVIDENCE is the relabelled Librarian tab — value string is unchanged.
    fireEvent.click(screen.getByText('EVIDENCE'));
    expect(onTabChange).toHaveBeenCalledWith('librarian');
  });

  it('disables seeker tab in overview mode', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="overview" onTabChange={onTabChange} />);

    // GAPS is the relabelled Seeker tab (detail-only).
    const seekerButton = screen.getByText('GAPS').closest('button')!;
    expect(seekerButton).toBeDisabled();

    fireEvent.click(seekerButton);
    expect(onTabChange).not.toHaveBeenCalled();
  });

  it('enables seeker tab in detail mode', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="detail" onTabChange={onTabChange} />);

    const seekerButton = screen.getByText('GAPS').closest('button')!;
    expect(seekerButton).not.toBeDisabled();

    fireEvent.click(seekerButton);
    expect(onTabChange).toHaveBeenCalledWith('seeker');
  });

  it('does not call onTabChange when clicking disabled tab', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="overview" onTabChange={onTabChange} />);

    // Click a live tab then the disabled one — only the live tab fires.
    fireEvent.click(screen.getByText('MAP'));   // cartographer — enabled
    fireEvent.click(screen.getByText('GAPS'));  // seeker — disabled in overview

    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('cartographer');
  });

  it('shows subtitles on desktop (hidden md:block)', () => {
    render(<ViewSelector {...defaultProps} />);
    // Subtitles are rendered but hidden on mobile via CSS.
    expect(screen.getByText('Shape of the debate?')).toBeInTheDocument();
    expect(screen.getByText('What does the evidence say?')).toBeInTheDocument();
  });
});
