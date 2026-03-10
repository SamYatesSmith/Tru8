import Link from 'next/link';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  ctaText?: string;
  ctaHref?: string;
}

export function PageHeader({
  title,
  subtitle,
  ctaText,
  ctaHref,
}: PageHeaderProps) {
  return (
    <div className="mb-6 md:mb-12 py-4 md:py-8">
      <div className="font-mono text-[11px] tracking-[0.3em] uppercase text-zinc-400 mb-3">
        Dashboard — Overview
      </div>
      <h1 className="text-3xl md:text-4xl font-bold text-zinc-900 mb-2">
        {title}
      </h1>
      <p className="text-base text-zinc-500 mb-6">
        {subtitle}
      </p>
      {ctaText && ctaHref && (
        <Link
          href={ctaHref}
          className="relative inline-flex items-center gap-2 bg-zinc-900 hover:bg-zinc-800 text-white text-xs font-bold uppercase tracking-[0.2em] h-12 px-6 transition-colors"
        >
          {ctaText}
          <div className="w-2.5 h-2.5 bg-accent absolute right-0 top-1/2 -translate-y-1/2 translate-x-1 rotate-45" />
        </Link>
      )}
    </div>
  );
}
