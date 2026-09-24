import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { EvidenceMetaStrip } from '../EvidenceMetaStrip';

function reviewed(container: HTMLElement): string | undefined {
  const label = Array.from(container.querySelectorAll('span')).find((s) => s.textContent === 'Sources Reviewed');
  return label?.nextElementSibling?.textContent ?? undefined;
}

// A− S6 (2026-09-24): "Reviewed 10 · Organised 14" — every organised source was
// reviewed, so Reviewed is never the smaller number.
describe('EvidenceMetaStrip — reviewed count', () => {
  it('never prints Reviewed below Organised', () => {
    const { container } = render(
      <EvidenceMetaStrip referenceId="26699bc7" claimsCount={1} sourcesCount={14} sourcesFoundCount={10} />,
    );
    expect(reviewed(container)).toBe('14');
  });

  it('keeps a larger search count as reported', () => {
    const { container } = render(
      <EvidenceMetaStrip referenceId="b8cf098b" claimsCount={1} sourcesCount={8} sourcesFoundCount={27} />,
    );
    expect(reviewed(container)).toBe('27');
  });

  it('falls back to the organised count when no search count exists', () => {
    const { container } = render(<EvidenceMetaStrip referenceId="x" claimsCount={1} sourcesCount={5} />);
    expect(reviewed(container)).toBe('5');
  });
});
