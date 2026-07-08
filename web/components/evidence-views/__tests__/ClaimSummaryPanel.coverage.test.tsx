import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

// Analytics is only invoked on interaction, but mock it so import side-effects
// (posthog) never touch the render.
vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));

import { ClaimSummaryPanel } from '../ClaimSummaryPanel';
import type { Claim, Evidence } from '@shared/types';

function ev(id: string, llm?: number, excluded = false): Evidence {
  return {
    id,
    source: 'example.com',
    url: `https://example.com/${id}`,
    title: `Source ${id}`,
    snippet: '...',
    relevanceScore: 0.5,
    llmRelevanceScore: llm,
    receiptStatus: excluded ? 'excluded' : 'shown',
  } as Evidence;
}

// elements: [] keeps the panel minimal (no ElementList / distribution bar) so
// the test targets only the F6 coverage line.
function claimWith(evidence: Evidence[]): Claim {
  return { id: 'c1', text: 'A claim.', evidence, claimMap: { elements: [] } } as unknown as Claim;
}

describe('ClaimSummaryPanel — F6 topical-relevance coverage', () => {
  it('counts sources that bear directly on the claim (score >= 4)', () => {
    const { getByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1', 5), ev('2', 4), ev('3', 2), ev('4', 5)])} position={0} />,
    );
    expect(getByText(/3 of 4 sources bear directly on the claim\./)).toBeTruthy();
  });

  it('excludes receipt-excluded sources from the denominator', () => {
    const { getByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1', 5), ev('2', 4), ev('3', 5, true)])} position={0} />,
    );
    expect(getByText(/2 of 2 sources bear directly on the claim\./)).toBeTruthy();
  });

  it('renders no coverage line when nothing is scored (older/pre-scorer checks)', () => {
    const { queryByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1'), ev('2')])} position={0} />,
    );
    expect(queryByText(/bear directly on the claim/)).toBeNull();
  });

  it('handles the singular and stays topical — no quality/credibility words', () => {
    const { getByText } = render(<ClaimSummaryPanel claim={claimWith([ev('1', 5)])} position={0} />);
    const line = getByText(/1 of 1 source bears directly on the claim\./);
    expect(line.textContent).not.toMatch(/quality|credib|strong|reliab|authorit|trust/i);
  });
});
