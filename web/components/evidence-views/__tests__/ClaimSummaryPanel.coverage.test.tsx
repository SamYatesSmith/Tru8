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

type Rel = 'supports' | 'challenges' | 'context';
function el(id: string, state: string, refs: [string, Rel][]) {
  return {
    elementId: id,
    description: id,
    state,
    evidenceRefs: refs.map(([evidenceId, relationship]) => ({ evidenceId, relationship })),
  };
}
function claimWith(evidence: Evidence[], elements: unknown[] = []): Claim {
  return { id: 'c1', text: 'A claim.', evidence, claimMap: { elements } } as unknown as Claim;
}

// A− S6 (2026-09-24): every count on the digest must reconcile with the bar
// beside it and the Gaps lens it links to.
describe('ClaimSummaryPanel — stat line counts reconcile', () => {
  it('"bear directly" counts sources filed supports/challenges, not the relevance score', () => {
    // Relevance scores deliberately disagree with the mapping: 1 and 4 are
    // scored 5 but only 2 and 3 are directional.
    const evidence = [ev('1', 5), ev('2', 2), ev('3', 1), ev('4', 5)];
    const elements = [el('e1', 'supported', [['1', 'context'], ['2', 'supports'], ['3', 'challenges']])];
    const { getByText } = render(<ClaimSummaryPanel claim={claimWith(evidence, elements)} position={0} />);
    expect(getByText(/4 sources · 2 bear directly on the claim\./)).toBeTruthy();
    expect(getByText(/3 of 4 sources mapped/i)).toBeTruthy();
  });

  it('a source that both supports and challenges counts once', () => {
    const elements = [el('e1', 'supported', [['1', 'supports']]), el('e2', 'disputed', [['1', 'challenges']])];
    const { getByText } = render(<ClaimSummaryPanel claim={claimWith([ev('1')], elements)} position={0} />);
    expect(getByText(/1 source · 1 bears directly on the claim\./)).toBeTruthy();
  });

  it('excludes receipt-excluded sources', () => {
    const elements = [el('e1', 'supported', [['1', 'supports'], ['2', 'supports'], ['3', 'supports']])];
    const { getByText } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1'), ev('2'), ev('3', undefined, true)], elements)} position={0} />,
    );
    expect(getByText(/2 sources · 2 bear directly on the claim\./)).toBeTruthy();
  });

  it('renders no directional clause when nothing is mapped', () => {
    const { getByText, queryByText } = render(<ClaimSummaryPanel claim={claimWith([ev('1'), ev('2')])} position={0} />);
    expect(queryByText(/bear directly on the claim/)).toBeNull();
    expect(getByText(/2 sources\./)).toBeTruthy();
  });

  it('stays a count — no quality/credibility words', () => {
    const elements = [el('e1', 'supported', [['1', 'supports']])];
    const { getByText } = render(<ClaimSummaryPanel claim={claimWith([ev('1')], elements)} position={0} />);
    const line = getByText(/1 source · 1 bears directly on the claim\./);
    expect(line.textContent).not.toMatch(/quality|credib|strong|reliab|authorit|trust/i);
  });

  it('element coverage uses the Gaps lens definition (evidence present), only when partial', () => {
    // e2 is UNRESOLVED but has evidence: the lens calls that "needs review",
    // not a gap, so coverage is full and the clause is silent.
    const elements = [el('e1', 'supported', [['1', 'supports']]), el('e2', 'unresolved', [['1', 'context']])];
    const { container } = render(<ClaimSummaryPanel claim={claimWith([ev('1')], elements)} position={0} />);
    expect(container.textContent).not.toMatch(/elements have evidence/);

    const partial = [el('e1', 'supported', [['1', 'supports']]), el('e2', 'unresolved', [])];
    const r2 = render(<ClaimSummaryPanel claim={claimWith([ev('1')], partial)} position={0} />);
    expect(r2.container.textContent).toMatch(/1 of 2 elements have evidence\./);
  });

  it('the Gaps link counts gaps and needs-review exactly as the lens does', () => {
    const elements = [
      el('e1', 'supported', [['1', 'supports']]),
      el('e2', 'unresolved', [['1', 'context']]), // needs review
      el('e3', 'unresolved', []), // gap
    ];
    const { getByRole } = render(
      <ClaimSummaryPanel claim={claimWith([ev('1')], elements)} position={0} onNavigate={() => {}} />,
    );
    expect(getByRole('button', { name: 'Open Gaps lens' }).textContent).toMatch(/^1 gap · 1 needs review — open the Gaps lens/);
  });
});
