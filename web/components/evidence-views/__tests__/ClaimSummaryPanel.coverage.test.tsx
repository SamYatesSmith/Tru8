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
// the tests target only the merged stat line (C2 R2: sources · F6 direct count
// · element coverage only when partial).
function claimWith(evidence: Evidence[]): Claim {
  return { id: 'c1', text: 'A claim.', evidence, claimMap: { elements: [] } } as unknown as Claim;
}

describe('ClaimSummaryPanel — merged stat line (C2 R2, carries F6 coverage)', () => {
  it('counts sources that bear directly on the claim (score >= 4)', () => {
    const { getByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1', 5), ev('2', 4), ev('3', 2), ev('4', 5)])} position={0} />,
    );
    expect(getByText(/4 sources · 3 bear directly on the claim\./)).toBeTruthy();
  });

  it('excludes receipt-excluded sources from both counts', () => {
    const { getByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1', 5), ev('2', 4), ev('3', 5, true)])} position={0} />,
    );
    expect(getByText(/2 sources · 2 bear directly on the claim\./)).toBeTruthy();
  });

  it('renders no coverage clause when nothing is scored (older/pre-scorer checks)', () => {
    const { getByText, queryByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1'), ev('2')])} position={0} />,
    );
    expect(queryByText(/bear directly on the claim/)).toBeNull();
    // The source count still prints — the clause, not the line, is gated.
    expect(getByText(/2 sources\./)).toBeTruthy();
  });

  it('handles the singular and stays topical — no quality/credibility words', () => {
    const { getByText } = render(<ClaimSummaryPanel claim={claimWith([ev('1', 5)])} position={0} />);
    const line = getByText(/1 source · 1 bears directly on the claim\./);
    expect(line.textContent).not.toMatch(/quality|credib|strong|reliab|authorit|trust/i);
  });

  it('prints element coverage only when partial (full coverage says nothing)', () => {
    const partial = {
      id: 'c2',
      text: 'A claim.',
      evidence: [ev('1', 5)],
      claimMap: {
        elements: [
          { elementId: 'e1', description: 'covered', state: 'supported', evidenceRefs: [] },
          { elementId: 'e2', description: 'gap', state: 'unresolved', evidenceRefs: [] },
        ],
      },
    } as unknown as Claim;
    const { getByText } = render(<ClaimSummaryPanel claim={partial} position={0} />);
    expect(getByText(/1 of 2 elements covered\./)).toBeTruthy();

    const full = {
      ...partial,
      id: 'c3',
      claimMap: {
        elements: [{ elementId: 'e1', description: 'covered', state: 'supported', evidenceRefs: [] }],
      },
    } as unknown as Claim;
    // Scope to this render's container — both renders share document.body.
    const { container } = render(<ClaimSummaryPanel claim={full} position={0} />);
    expect(container.textContent).not.toMatch(/elements covered/);
  });
});
