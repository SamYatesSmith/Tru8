'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useFeatureDetection } from '@/hooks/useFeatureDetection';

/**
 * Progressive enhancement card component with fallbacks
 * Phase 02: Progressive Enhancement Strategy
 */
interface ProgressiveCardProps {
  children: ReactNode;
  variant?: 'basic' | 'enhanced' | 'glass';
  className?: string;
}

export function ProgressiveCard({ children, variant = 'enhanced', className }: ProgressiveCardProps) {
  const { backdropFilter } = useFeatureDetection();

  const getCardClasses = () => {
    const baseClasses = 'card';

    if (variant === 'glass' && backdropFilter) {
      return cn(baseClasses, 'glass-enhanced', className);
    }

    if (variant === 'enhanced') {
      return cn(baseClasses, 'card-enhanced', className);
    }

    return cn(baseClasses, className);
  };

  return (
    <div className={getCardClasses()}>
      {children}
    </div>
  );
}