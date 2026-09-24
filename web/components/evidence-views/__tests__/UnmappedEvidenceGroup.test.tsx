import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));

import { UnmappedEvidenceGroup } from '../librarian/UnmappedEvidenceGroup';
import { ClaimSummaryPanel } from '../ClaimSummaryPanel';
import type { Claim, Evidence } from '@shared/types';

const ev = (id: string, tier: string, title = `Source ${id}`) =>
  ({ id, evidenceId: id, url: `https://example.com/${id}`, title, tier, receiptStatus: 'shown' } as unknown as Evidence);

// A− H4 (2026-09-24): unmapped sources leave the tier bands but stay visible.
describe('UnmappedEvidenceGroup', () => {
  it('lists every unmapped source with its count and says "not mapped", never "not related"', () => {
    const { getByTestId } = render(
      <UnmappedEvidenceGroup evidence={[ev('wb', 'primary', 'Trade (% of GDP) - United States'), ev('x', 'commentary')]} />,
    );
    const text = getByTestId('unmapped-evidence').textContent || '';
    expect(text).toMatch(/not mapped to any part of the claim \(2\)/);
    expect(text).toMatch(/Trade \(% of GDP\)/);
    expect(text).not.toMatch(/not related/i);
  });

  it('renders nothing when every source is mapped', () => {
    const { container } = render(<UnmappedEvidenceGroup evidence={[]} />);
    expect(container.textContent).toBe('');
  });
});

describe('ClaimSummaryPanel footer tier mix', () => {
  it('counts tiers over mapped sources and names the unmapped ones separately', () => {
    const claim = {
      id: 'c1',
      text: 'A claim.',
      evidence: [ev('a', 'reporting'), ev('wb', 'primary')],
      claimMap: { elements: [{ elementId: 'e1', description: 'x', state: 'supported', evidenceRefs: [{ evidenceId: 'a', relationship: 'supports' }] }] },
    } as unknown as Claim;
    const { container } = render(<ClaimSummaryPanel claim={claim} position={0} />);
    expect(container.textContent).toMatch(/0 primary.*1 reporting.*0 commentary.*1 not mapped/);
  });
});
