'use client';

import { ReactNode } from 'react';

interface GlowingBorderCardProps {
  children: ReactNode;
  className?: string;
  animated?: boolean;
}

export function GlowingBorderCard({
  children,
  className = '',
}: GlowingBorderCardProps) {
  return (
    <div className={`bg-white border border-zinc-200 ${className}`}>
      {children}
    </div>
  );
}
