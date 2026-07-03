/**
 * F2 Phase B — evidence date provenance helpers.
 *
 * Suspect = the search engine's date merely echoed a /YYYY/MM/ URL upload
 * path (backend labels it url_inferred_suspect). Surfaces hint it; the
 * timeline treats it as undated. Everything else renders plain.
 */

import { describe, it, expect } from 'vitest';
import {
  isSuspectDate,
  timelineDate,
  DATE_HINT_TEXT,
  DATE_HINT_TOOLTIP,
} from '../evidence-date';

describe('isSuspectDate', () => {
  it('is true only for url_inferred_suspect', () => {
    expect(isSuspectDate({ dateBasis: 'url_inferred_suspect' })).toBe(true);
    expect(isSuspectDate({ dateBasis: 'page_metadata' })).toBe(false);
    expect(isSuspectDate({ dateBasis: 'engine' })).toBe(false);
    expect(isSuspectDate({ dateBasis: 'api_adapter' })).toBe(false);
    expect(isSuspectDate({ dateBasis: undefined })).toBe(false);
    expect(isSuspectDate({})).toBe(false);
  });
});

describe('timelineDate', () => {
  it('returns a Date for a confirmed date', () => {
    const d = timelineDate({
      publishedDate: '2020-01-15',
      dateBasis: 'page_metadata',
    });
    expect(d).not.toBeNull();
    expect(d!.getFullYear()).toBe(2020);
  });

  it('returns a Date for an engine date (unlabelled but plotted)', () => {
    expect(
      timelineDate({ publishedDate: '2026-04-04', dateBasis: 'engine' })
    ).not.toBeNull();
  });

  it('treats a suspect date as undated — off the axis', () => {
    expect(
      timelineDate({
        publishedDate: '2026-04-04',
        dateBasis: 'url_inferred_suspect',
      })
    ).toBeNull();
  });

  it('handles pre-F2 rows with no basis (plots them, as before)', () => {
    expect(
      timelineDate({ publishedDate: '2026-04-04', dateBasis: undefined })
    ).not.toBeNull();
  });

  it('returns null for missing or unparseable dates', () => {
    expect(timelineDate({ publishedDate: undefined })).toBeNull();
    expect(timelineDate({ publishedDate: 'not a date' })).toBeNull();
  });
});

describe('copy locks', () => {
  it('hint copy is neutral, UK-English, and stable', () => {
    expect(DATE_HINT_TEXT).toBe('reported by host');
    expect(DATE_HINT_TOOLTIP).toBe(
      'Date reported by the hosting site — not confirmed by the document itself.'
    );
  });
});
