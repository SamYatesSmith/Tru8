import { describe, it, expect } from 'vitest';
import { cleanTitle } from '../shared-utils';

describe('cleanTitle', () => {
  it('strips a trailing ellipsis + orphaned site suffix', () => {
    expect(cleanTitle('Very-long-range dynamic triggering of mud volcano unrest ... - Science')).toBe(
      'Very-long-range dynamic triggering of mud volcano unrest'
    );
    expect(cleanTitle('Is there a relationship between the number of earthquakes ... - Quora')).toBe(
      'Is there a relationship between the number of earthquakes'
    );
  });

  it('strips a bare trailing ellipsis (ASCII or unicode)', () => {
    expect(cleanTitle('Fault-mediated magma propagation and triggered seismicity ...')).toBe(
      'Fault-mediated magma propagation and triggered seismicity'
    );
    expect(cleanTitle('Seismological observations of the 2011 Nabro eruption…')).toBe(
      'Seismological observations of the 2011 Nabro eruption'
    );
  });

  it('leaves clean titles untouched, including internal separators and real site suffixes', () => {
    expect(cleanTitle('Plate tectonics | Definition, Theory, Facts, & Evidence - Britannica')).toBe(
      'Plate tectonics | Definition, Theory, Facts, & Evidence - Britannica'
    );
    expect(cleanTitle('Volcano - Plate Boundaries, Magma, Eruptions - Britannica')).toBe(
      'Volcano - Plate Boundaries, Magma, Eruptions - Britannica'
    );
  });

  it('handles empty / null / undefined', () => {
    expect(cleanTitle('')).toBe('');
    expect(cleanTitle(null)).toBe('');
    expect(cleanTitle(undefined)).toBe('');
  });
});
