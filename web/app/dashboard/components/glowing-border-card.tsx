'use client';

import { ReactNode } from 'react';

interface GlowingBorderCardProps {
  children: ReactNode;
  className?: string;
  /** Set to false to disable the animation */
  animated?: boolean;
}

export function GlowingBorderCard({
  children,
  className = '',
  animated = true
}: GlowingBorderCardProps) {
  if (!animated) {
    return (
      <div className={`bg-[#1a1f2e] border border-slate-700 rounded-xl ${className}`}>
        {children}
      </div>
    );
  }

  return (
    <div className={`glowing-border-wrapper ${className}`}>
      <div className="glowing-border-content">
        {children}
      </div>
    </div>
  );
}
