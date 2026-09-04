import { describe, it, expect, vi } from 'vitest';
import { render } from '@testing-library/react';

vi.mock('@/lib/analytics', () => ({ capture: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock('@/components/evidence-views/seeker/BountyField', () => ({ BountyField: () => null }));

import { UnknownElementCard } from '../seeker/UnknownElementCard';
import type { ClaimElement, Evidence } from '@shared/types';

/**
 * 2026-09-04 — the GAPS lens showed raw `ev-…` ids on every unresolved element.
 *
 * Claim Map evidence_refs carry the stable `evidenceId` (`ev-48f5e9ce5d8b`);
 * the Evidence row's `id` is a UUID. The card built its title lookup on `id`
 * alone, so the lookup never hit and the chip fell back to the ref id. Seen
 * live on both 2026-09-02 outreach records (TRU-1BBF-008A, TRU-4BE2-8CD1),
 * the first send records with an unresolved element. A reader must see the
 * source, never an internal id.
 */

const element = {
  elementId: 'e3',
  description: 'The deployment of the AI triage system directly caused the decrease in phone queuing volume.',
  state: 'unresolved',
  uncertainty: null,
  evidenceRefs: [
    { evidenceId: 'ev-48f5e9ce5d8b', relationship: 'context', reasoning: '' },
    { evidenceId: 'ev-rec-e3_2_8d770090', relationship: 'supports', reasoning: '' },
  ],
} as unknown as ClaimElement;

const evidence = [
  {
    id: 'f5c0f606-e2ca-40b5-9bb3-9108e7ef66a6',
    evidenceId: 'ev-48f5e9ce5d8b',
    title: 'The Miracle Statistic Revisited',
    url: 'https://trusttheevidence.substack.com/p/the-miracle-statistic-revisited',
    source: 'trusttheevidence.substack.com',
  },
  {
    id: '7643f965-3b52-4d9a-a369-440cca621761',
    evidenceId: 'ev-rec-e3_2_8d770090',
    title: 'Health AI Chronicle — Edition 242 - Lucien Engelen',
    url: 'https://lucienengelen.com/Blog-daily-chronicle-2026-08-31.dc.html',
    source: 'lucienengelen.com',
  },
] as unknown as Evidence[];

describe('UnknownElementCard evidence chips', () => {
  it('shows source titles, never the internal ev-… ids, when refs carry evidenceId', () => {
    const { container } = render(
      <UnknownElementCard element={element} index={2} evidence={evidence} readOnly />
    );
    const text = container.textContent || '';
    expect(text).toContain('The Miracle Statistic Revisited');
    expect(text).toContain('Health AI Chronicle');
    expect(text).not.toContain('ev-48f5e9ce5d8b');
    expect(text).not.toContain('ev-rec-e3_2_8d770090');
  });

  it('still resolves a ref whose evidence row has no evidenceId (legacy rows keyed by id)', () => {
    const legacy = [
      { id: 'ev-legacy-1', title: 'Legacy row', url: 'https://example.org/legacy', source: 'example.org' },
    ] as unknown as Evidence[];
    const legacyElement = {
      ...element,
      evidenceRefs: [{ evidenceId: 'ev-legacy-1', relationship: 'context', reasoning: '' }],
    } as unknown as ClaimElement;
    const { container } = render(
      <UnknownElementCard element={legacyElement} index={0} evidence={legacy} readOnly />
    );
    expect(container.textContent).toContain('Legacy row');
  });
});
