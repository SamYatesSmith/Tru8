import { describe, it, expect } from 'vitest';
import { cleanTitle } from '../shared-utils';

describe('cleanTitle', () => {
  it('drops the orphaned site suffix but KEEPS the truncation marker', () => {
    expect(cleanTitle('Very-long-range dynamic triggering of mud volcano unrest ... - Science')).toBe(
      'Very-long-range dynamic triggering of mud volcano unrest…'
    );
    expect(cleanTitle('Is there a relationship between the number of earthquakes ... - Quora')).toBe(
      'Is there a relationship between the number of earthquakes…'
    );
  });

  it('normalises a bare trailing ellipsis (ASCII or unicode) to one tight "…"', () => {
    expect(cleanTitle('Fault-mediated magma propagation and triggered seismicity ...')).toBe(
      'Fault-mediated magma propagation and triggered seismicity…'
    );
    expect(cleanTitle('Seismological observations of the 2011 Nabro eruption…')).toBe(
      'Seismological observations of the 2011 Nabro eruption…'
    );
  });

  it('keeps a cut title visibly cut — the reader must be able to tell', () => {
    // The exact shapes from the reporting-sources screenshot (2026-08-25):
    // provider-truncated at ~54 chars, ending on a function word. Without the
    // marker these read as complete headlines, which is the defect.
    expect(cleanTitle('Britain braces for unprecedented water restrictions as...')).toBe(
      'Britain braces for unprecedented water restrictions as…'
    );
    expect(cleanTitle('UK planners warn water restrictions could be extended to ...')).toBe(
      'UK planners warn water restrictions could be extended to…'
    );
  });

  it('is idempotent — cleaning an already-cleaned title changes nothing', () => {
    const once = cleanTitle('Trump says he has ended six wars in six months. As a ...');
    expect(cleanTitle(once)).toBe(once);
    expect(once).toBe('Trump says he has ended six wars in six months. As a…');
  });

  it('leaves clean titles untouched, including internal separators and real site suffixes', () => {
    expect(cleanTitle('Plate tectonics | Definition, Theory, Facts, & Evidence - Britannica')).toBe(
      'Plate tectonics | Definition, Theory, Facts, & Evidence - Britannica'
    );
    expect(cleanTitle('Volcano - Plate Boundaries, Magma, Eruptions - Britannica')).toBe(
      'Volcano - Plate Boundaries, Magma, Eruptions - Britannica'
    );
    // A full sentence ending in a real full stop is not a truncation.
    expect(cleanTitle('Could England and Wales ever run out of water?')).toBe(
      'Could England and Wales ever run out of water?'
    );
  });

  it('handles empty / null / undefined / punctuation-only', () => {
    expect(cleanTitle('')).toBe('');
    expect(cleanTitle(null)).toBe('');
    expect(cleanTitle(undefined)).toBe('');
    // Nothing but a marker carries no information — caller falls back.
    expect(cleanTitle('...')).toBe('');
    expect(cleanTitle('…')).toBe('');
  });
});
