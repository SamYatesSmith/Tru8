import { describe, expect, it } from 'vitest';
import { elementCaveatNote } from '../element-caveat';

/**
 * The fixture is the REAL corpus: every element `uncertainty` stored on the six
 * 2026 outreach records (TTE 11f54993, Viglione 441144ac, Seymour fa08cff7,
 * Tapper 5d69fc71, McSweeney 6fe1a7e8 + re-run e1e5de25), read from the live
 * public payloads on 2026-09-02. The gate must show every genuine limit and hide
 * every adjudication. If a rule change flips one of these, that is the signal.
 */
const SHOWN = [
  // Tapper — the two caveats the send note points at
  'The £22 million figure is an estimated loss, not official outturn data, and is based on modelled assumptions.',
  'The £53 million figure was a static forecast that did not account for behavioural responses from taxpayers.',
  'The actual revenue is an estimated loss of £22 million, which is significantly less than the static forecast of £53 million, but this is based on modelled assumptions rather than official outturn data.',
  // TTE — the provenance note the note had to relegate to "the downloadable record"
  'The evaluation behind the 29% statistic was an unpublished internal NHS England evaluation, and its methodology has been questioned.',
  // Viglione — the GWIS/Russia crux, on DISPUTED elements (why supported-only was rejected)
  'GWIS Europe totals include Russia, where activity was unusually low, whereas EU-specific data show 2026 among the highest on record.',
  "The margin described as 'by some distance' is an artifact of aggregate GWIS continental boundaries dominated by Russia.",
  // McSweeney re-run — the seam the note names
  'Longer-term and sub-regional pollution trends are not fully detailed in this specific source.',
  'The evidence indicates aerosol reduction is an amplifying mechanism rather than the sole direct trigger.',
  // McSweeney original e1 — conflicting-evidence note is a limit, not a verdict
  'There is conflicting evidence regarding whether declining air pollution in Europe is a cause of recent heatwaves, with some studies supporting the link and others disputing it.',
];

const HIDDEN = [
  // McSweeney re-run e3 — verdict word
  'The evidence consistently refutes this element, demonstrating greenhouse gas-induced climate change is the primary driver.',
  // Seymour — intensified adjudication restating the badge
  'The available evidence strongly suggests that 2026 is not the quietest year for wildfires in Europe, with several sources indicating the opposite.',
  'The available evidence strongly indicates that the intensity and area burned by wildfires in Europe during 2026 are not lower than in previous years.',
  // McSweeney original e2 — "strong evidence challenging"
  'There is strong evidence challenging the assertion that climate change is not a cause of recent heatwaves in Europe, with multiple sources attributing them to climate change.',
];

describe('elementCaveatNote — the roster shows limits, never adjudications', () => {
  it.each(SHOWN)('shows a genuine limit: %s', (s) => {
    expect(elementCaveatNote(s)).toBe(s);
  });

  it.each(HIDDEN)('hides an adjudication: %s', (s) => {
    expect(elementCaveatNote(s)).toBeNull();
  });

  it('nulls the mapper sentinel strings and empties (the Seeker filter, in one place)', () => {
    for (const v of ['null', 'None', 'N/A', 'n/a', '', '   ', 'undefined']) {
      expect(elementCaveatNote(v)).toBeNull();
    }
    expect(elementCaveatNote(null)).toBeNull();
    expect(elementCaveatNote(undefined)).toBeNull();
  });

  it('trims surrounding whitespace but never rewrites the sentence', () => {
    expect(elementCaveatNote('  The figure is a modelled estimate.  ')).toBe('The figure is a modelled estimate.');
  });

  it('hides verdict words wherever they sit in the sentence', () => {
    expect(elementCaveatNote('Several sources describe the figure as false.')).toBeNull();
    expect(elementCaveatNote('The claim is proven by the ONS release.')).toBeNull();
    expect(elementCaveatNote('A later fact-check confirmed the number.')).toBeNull();
  });

  it('keeps an unintensified "the evidence indicates" limit', () => {
    expect(elementCaveatNote('The evidence indicates the pilot ran in one region only.')).toBe(
      'The evidence indicates the pilot ran in one region only.',
    );
  });
});
