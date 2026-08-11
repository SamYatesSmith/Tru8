/**
 * Every refusal case is drawn from a real external check in the 2026-08-11
 * usage audit; every pass case is an input the pipeline served well.
 */
import { describe, expect, it } from 'vitest';

import { triageText, triageUrl } from '../input-triage';

describe('triageUrl — refusals, each from a real failed check', () => {
  it('refuses a bare homepage (kpkbot.com, hellointerview.com)', () => {
    expect(triageUrl('https://kpkbot.com/').ok).toBe(false);
    expect(triageUrl('https://hellointerview.com').ok).toBe(false);
  });

  it('refuses video and social platforms', () => {
    expect(triageUrl('https://www.youtube.com/watch?v=abc123').ok).toBe(false);
    expect(triageUrl('https://youtu.be/abc123').ok).toBe(false);
    expect(triageUrl('https://www.tiktok.com/@user/video/123').ok).toBe(false);
    expect(triageUrl('https://x.com/user/status/123').ok).toBe(false);
  });

  it('refuses reliably-paywalled publishers (the Wiley paper, tried twice)', () => {
    expect(
      triageUrl('https://onlinelibrary.wiley.com/doi/10.1111/csp2.70189').ok
    ).toBe(false);
    expect(triageUrl('https://doi.org/10.1111/csp2.70189').ok).toBe(false);
    expect(triageUrl('https://www.sciencedirect.com/science/article/pii/S1').ok).toBe(
      false
    );
  });
});

describe('triageUrl — passes', () => {
  it('passes news articles (the checks that reached the gate)', () => {
    expect(triageUrl('https://www.politico.eu/article/farage-polling/').ok).toBe(true);
    expect(triageUrl('https://edition.cnn.com/2026/03/05/politics/texas').ok).toBe(true);
  });

  it('passes gov and open-access academic pages', () => {
    expect(triageUrl('https://www.gov.uk/government/publications/strategy').ok).toBe(
      true
    );
    expect(triageUrl('https://elifesciences.org/articles/12345').ok).toBe(true);
    expect(triageUrl('https://journals.plos.org/plosone/article?id=10.1371').ok).toBe(
      true
    );
  });

  it('passes a homepage-looking URL that carries a query (WordPress ?p=)', () => {
    expect(triageUrl('https://example.com/?p=1234').ok).toBe(true);
  });

  it('does not swallow invalid URLs — the existing validator owns those', () => {
    expect(triageUrl('not a url').ok).toBe(true);
  });

  it('is not fooled by lookalike hostnames', () => {
    // "notdoi.org" must not match the doi.org rule.
    expect(triageUrl('https://notdoi.org/some/article').ok).toBe(true);
  });
});

describe('triageText', () => {
  it('refuses a bare topic (the failed "pink salt diet" check)', () => {
    expect(triageText('pink salt diet').ok).toBe(false);
  });

  it('passes the same words asked as a question', () => {
    expect(triageText('pink salt diet?').ok).toBe(true);
  });

  it('passes real claims from the audit', () => {
    expect(triageText('coronavirus can be cured by drinking hot water').ok).toBe(true);
    expect(triageText('Are UK sofas toxic and do they cause cancer?').ok).toBe(true);
  });

  it('passes four words and refuses three', () => {
    expect(triageText('sofas cause cancer often').ok).toBe(true);
    expect(triageText('sofas cause cancer').ok).toBe(false);
  });
});
