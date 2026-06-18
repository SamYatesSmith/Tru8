/**
 * SheetHeader — the document grammar of the homepage (Phase 1, art-direction plan
 * `audit/2026-06-18_homepage_art_direction.md`, Device 2).
 *
 * Every marketing section is a numbered "sheet" in one specification document.
 * A full-measure 1px top rule + a title block: orange registration glyph · sheet
 * number · sheet name (left) · a mono datasheet ref (right). Repeated identically
 * across sections, this is what converts "7 templates" into "one calibrated
 * document". The rotated square is the brand's single registration glyph at ONE
 * fixed size — the only orange in the header (accent discipline).
 */
interface SheetHeaderProps {
  /** Two-digit sheet number, e.g. "00". */
  number: string;
  /** Sheet name, uppercased visually (e.g. "PROBLEM"). */
  label: string;
  /** Right-aligned mono datasheet reference (e.g. "claimMap · _meta · _manifest"). */
  refText?: string;
  /** Dark sections (e.g. the API band) invert the rule/text tones. */
  tone?: 'light' | 'dark';
}

export function SheetHeader({
  number,
  label,
  refText,
  tone = 'light',
}: SheetHeaderProps) {
  const isDark = tone === 'dark';
  const rule = isDark ? 'border-zinc-800' : 'border-zinc-200';
  const numberTone = isDark ? 'text-zinc-500' : 'text-zinc-400';
  const labelTone = isDark ? 'text-zinc-300' : 'text-zinc-500';
  const refTone = isDark ? 'text-zinc-500' : 'text-zinc-500';

  return (
    <div
      className={`flex items-center gap-3 border-t ${rule} pt-4 mb-10 md:mb-12`}
    >
      <span
        aria-hidden="true"
        className="w-2 h-2 bg-accent rotate-45 shrink-0"
      />
      <span className={`font-mono text-[10px] tracking-[0.3em] ${numberTone}`}>
        {number}
      </span>
      <span
        className={`font-mono text-[10px] tracking-[0.3em] uppercase ${labelTone}`}
      >
        {label}
      </span>
      {refText ? (
        <span
          className={`font-mono text-[10px] tracking-[0.2em] ${refTone} ml-auto hidden sm:block`}
        >
          {refText}
        </span>
      ) : null}
    </div>
  );
}
