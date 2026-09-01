import { beforeEach, describe, expect, it } from 'vitest';
import {
  CLAIM_INTENT_KEY,
  INTENT_TTL_MS,
  clearClaimIntent,
  consumeClaimIntent,
  saveClaimIntent,
} from '../claim-intent';

describe('claim intent — the homepage field hands a claim to the console form', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it('round-trips a text claim and is single-use', () => {
    expect(saveClaimIntent('text', 'UK inflation fell below 2% in September 2024', 1_000)).toBe(true);
    const first = consumeClaimIntent(2_000);
    expect(first).toEqual({ kind: 'text', value: 'UK inflation fell below 2% in September 2024', ts: 1_000 });
    expect(consumeClaimIntent(3_000)).toBeNull();
    expect(window.sessionStorage.getItem(CLAIM_INTENT_KEY)).toBeNull();
  });

  it('round-trips a url claim', () => {
    saveClaimIntent('url', 'https://example.com/article', 10);
    expect(consumeClaimIntent(20)).toMatchObject({ kind: 'url', value: 'https://example.com/article' });
  });

  it('expires after the TTL and clears the slot', () => {
    saveClaimIntent('text', 'a claim typed this morning', 0);
    expect(consumeClaimIntent(INTENT_TTL_MS + 1)).toBeNull();
    expect(window.sessionStorage.getItem(CLAIM_INTENT_KEY)).toBeNull();
  });

  it('is still valid just inside the TTL', () => {
    saveClaimIntent('text', 'a claim typed just now', 0);
    expect(consumeClaimIntent(INTENT_TTL_MS - 1)).not.toBeNull();
  });

  it('rejects malformed or tampered payloads (and clears them)', () => {
    for (const bad of [
      'not json',
      '{}',
      '{"kind":"image","value":"x","ts":1}',
      '{"kind":"text","value":"","ts":1}',
      '{"kind":"text","value":42,"ts":1}',
      '{"kind":"text","value":"x","ts":"1"}',
      '{"kind":"text","value":"x","ts":9999999999999}',
      'null',
    ]) {
      window.sessionStorage.setItem(CLAIM_INTENT_KEY, bad);
      expect(consumeClaimIntent(1_000), bad).toBeNull();
      expect(window.sessionStorage.getItem(CLAIM_INTENT_KEY), bad).toBeNull();
    }
  });

  it('never leaves anything in the URL or localStorage', () => {
    saveClaimIntent('text', 'private claim', 1);
    expect(window.localStorage.getItem(CLAIM_INTENT_KEY)).toBeNull();
    expect(window.location.search).not.toContain('private');
    clearClaimIntent();
    expect(window.sessionStorage.getItem(CLAIM_INTENT_KEY)).toBeNull();
  });
});
