/**
 * First-touch capture rules. The backend re-validates everything; these pin
 * the client-side behaviour that decides what is remembered at all.
 */
import { beforeEach, describe, expect, it } from 'vitest';

import {
  captureAttribution,
  clearAttribution,
  normaliseSource,
  pendingAttribution,
  sourceFromSearch,
} from '../attribution';

beforeEach(() => localStorage.clear());

describe('sourceFromSearch', () => {
  it('reads ?src=', () => {
    expect(sourceFromSearch('?src=outreach-jane')).toBe('outreach-jane');
  });

  it('falls back to utm_source', () => {
    expect(sourceFromSearch('?utm_source=smithery')).toBe('smithery');
  });

  it('prefers src over utm_source when both are present', () => {
    expect(sourceFromSearch('?utm_source=b&src=a')).toBe('a');
  });

  it('returns null when untagged — never a default', () => {
    expect(sourceFromSearch('')).toBeNull();
    expect(sourceFromSearch('?utm_campaign=x')).toBeNull();
  });
});

describe('normaliseSource', () => {
  it('lowercases and trims', () => {
    expect(normaliseSource('  Outreach-Jane ')).toBe('outreach-jane');
  });

  it('refuses tags outside the minted charset', () => {
    expect(normaliseSource('has space')).toBeNull();
    expect(normaliseSource('<script>')).toBeNull();
    expect(normaliseSource('-leading')).toBeNull();
    expect(normaliseSource('x'.repeat(65))).toBeNull();
  });
});

describe('captureAttribution — first touch wins', () => {
  it('stores a tag and holds it pending', () => {
    captureAttribution('?src=hn-post');
    expect(pendingAttribution()).toBe('hn-post');
  });

  it('does not overwrite an earlier tag with a later one', () => {
    captureAttribution('?src=first-channel');
    captureAttribution('?src=second-channel');
    expect(pendingAttribution()).toBe('first-channel');
  });

  it('stores nothing for an untagged visit', () => {
    captureAttribution('');
    expect(pendingAttribution()).toBeNull();
  });

  it('clears on demand', () => {
    captureAttribution('?src=x1');
    clearAttribution();
    expect(pendingAttribution()).toBeNull();
  });
});
