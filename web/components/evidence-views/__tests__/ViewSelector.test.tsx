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
    expect(screen.getByText('CARTOGRAPHER')).toBeInTheDocument();
    expect(screen.getByText('LIBRARIAN')).toBeInTheDocument();
    expect(screen.getByText('CORRESPONDENT')).toBeInTheDocument();
    expect(screen.getByText('SEEKER')).toBeInTheDocument();
    expect(screen.getByText('PROJECTIONIST')).toBeInTheDocument();
    expect(screen.getByText('CHRONOLOGIST')).toBeInTheDocument();
  });

  it('calls onTabChange when a tab is clicked', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} onTabChange={onTabChange} />);

    fireEvent.click(screen.getByText('LIBRARIAN'));
    expect(onTabChange).toHaveBeenCalledWith('librarian');
  });

  it('disables seeker tab in overview mode', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="overview" onTabChange={onTabChange} />);

    const seekerButton = screen.getByText('SEEKER').closest('button')!;
    expect(seekerButton).toBeDisabled();

    fireEvent.click(seekerButton);
    expect(onTabChange).not.toHaveBeenCalled();
  });

  it('enables seeker tab in detail mode', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="detail" onTabChange={onTabChange} />);

    const seekerButton = screen.getByText('SEEKER').closest('button')!;
    expect(seekerButton).not.toBeDisabled();

    fireEvent.click(seekerButton);
    expect(onTabChange).toHaveBeenCalledWith('seeker');
  });

  it('does not call onTabChange when clicking disabled tab', () => {
    const onTabChange = vi.fn();
    render(<ViewSelector {...defaultProps} mode="overview" onTabChange={onTabChange} />);

    // Click all tabs — only non-disabled ones should fire
    fireEvent.click(screen.getByText('CARTOGRAPHER'));
    fireEvent.click(screen.getByText('SEEKER'));

    // Cartographer fires, Seeker does not
    expect(onTabChange).toHaveBeenCalledTimes(1);
    expect(onTabChange).toHaveBeenCalledWith('cartographer');
  });

  it('shows subtitles on desktop (hidden md:block)', () => {
    render(<ViewSelector {...defaultProps} />);
    // Subtitles are rendered but hidden on mobile via CSS
    expect(screen.getByText('Shape of the conversation')).toBeInTheDocument();
    expect(screen.getByText('Full evidence set, classified')).toBeInTheDocument();
  });
});
