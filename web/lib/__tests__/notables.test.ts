import { describe, expect, it } from 'vitest';
import { isSecondhand, pickNotable } from '../notables';

type Rel = 'supports' | 'challenges' | 'context';
const ev = (id: string, url: string, tier: string, relevanceScore = 0, evidenceType = 'news_reporting') => ({
  id,
  evidenceId: id,
  url,
  tier,
  relevanceScore,
  evidenceType,
});
const el = (...refs: [string, Rel][]) => ({
  evidenceRefs: refs.map(([evidenceId, relationship]) => ({ evidenceId, relationship })),
});

describe('pickNotable (A− S3, 2026-09-28)', () => {
  it('prefers the source bearing on more elements over higher relevance', () => {
    // #14: bylinetimes (1 element, top relevance) vs FT (4 elements)
    const pool = [ev('byline', 'https://bylinetimes.com/x', 'reporting', 0.9), ev('ft', 'https://www.ft.com/y', 'reporting', 0.5)];
    const els = [el(['byline', 'supports'], ['ft', 'supports']), el(['ft', 'supports']), el(['ft', 'supports'])];
    expect(pickNotable(pool, els, 'supports')?.id).toBe('ft');
  });

  it('prefers primary over reporting at equal reach', () => {
    // #7: Washington Examiner vs Cook's own results page
    const pool = [ev('wex', 'https://www.washingtonexaminer.com/a', 'reporting', 0.9), ev('cook', 'https://www.cookpolitical.com/b', 'primary', 0.2)];
    expect(pickNotable(pool, [el(['wex', 'supports'], ['cook', 'supports'])], 'supports')?.id).toBe('cook');
  });

  it('never headlines a platform, rewrite or opinion page when another source exists', () => {
    // #4 Medium essay, #8 muckrack profile, #6 Fortune opinion
    const pool = [
      ev('medium', 'https://medium.com/p/essay', 'primary', 1, 'analysis'),
      ev('opinion', 'https://fortune.com/o', 'primary', 1, 'opinion'),
      ev('jod', 'https://www.journalofdemocracy.org/x', 'commentary', 0.1, 'analysis'),
    ];
    const els = [el(['medium', 'supports'], ['opinion', 'supports'], ['jod', 'supports'])];
    expect(pickNotable(pool, els, 'supports')?.id).toBe('jod');
  });

  it('still returns a secondhand source when it is the only one', () => {
    const pool = [ev('reddit', 'https://www.reddit.com/r/x', 'commentary')];
    expect(pickNotable(pool, [el(['reddit', 'supports'])], 'supports')?.id).toBe('reddit');
  });

  it('applies the same rule to challenges (invariant #7)', () => {
    // #18: an orbitalradar tracker vs NASA's own page, both challenging
    const pool = [ev('tracker', 'https://orbitalradar.com/jwst', 'reporting', 0.9), ev('nasa', 'https://science.nasa.gov/webb', 'primary', 0.3)];
    const els = [el(['tracker', 'challenges'], ['nasa', 'challenges'])];
    expect(pickNotable(pool, els, 'challenges')?.id).toBe('nasa');
  });

  it('counts an element once per source and ignores other directions', () => {
    const pool = [ev('a', 'https://a.org', 'reporting', 0.1), ev('b', 'https://b.org', 'reporting', 0.9)];
    const els = [el(['a', 'supports'], ['a', 'supports'], ['b', 'supports']), el(['a', 'context'], ['b', 'challenges'])];
    // a: 1 element (duplicate ref ignored); b: 1 element → relevance breaks the tie
    expect(pickNotable(pool, els, 'supports')?.id).toBe('b');
  });

  it('breaks an exact tie by the earlier publication', () => {
    // #14: memeburn (16 Sep) and FT (12 Sep): same reach, tier and relevance
    const meme = { ...ev('meme', 'https://memeburn.com/a', 'reporting', 0), publishedDate: '2026-09-16T00:00:00' };
    const ft = { ...ev('ft', 'https://www.ft.com/b', 'reporting', 0), publishedDate: '2026-09-12T00:00:00' };
    expect(pickNotable([meme, ft], [el(['meme', 'supports'], ['ft', 'supports'])], 'supports')?.id).toBe('ft');
  });

  it('returns undefined when nothing bears in that direction', () => {
    const pool = [ev('a', 'https://a.org', 'primary')];
    expect(pickNotable(pool, [el(['a', 'context'])], 'supports')).toBeUndefined();
  });

  it('recognises secondhand hosts by hostname, not substring', () => {
    expect(isSecondhand(ev('x', 'https://x.com/status/1', 'commentary'))).toBe(true);
    expect(isSecondhand(ev('vox', 'https://www.vox.com/a', 'reporting'))).toBe(false);
    expect(isSecondhand(ev('mx', 'https://x.company.org/a', 'reporting'))).toBe(false);
  });
});
