'use client';

import { ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useFeatureDetection } from '@/hooks/useFeatureDetection';
import { ProgressiveCard } from './progressive-card';

/**
 * Progressive feature grid with fallbacks
 * Phase 02: Progressive Enhancement Strategy
 */
interface Feature {
  id: string;
  icon: ReactNode;
  title: string;
  description: string;
}

interface ProgressiveFeatureGridProps {
  features: Feature[];
  className?: string;
}

function FeatureContent({ feature }: { feature: Feature }) {
  return (
    <>
      <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
        {feature.icon}
      </div>
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        {feature.title}
      </h3>
      <p className="text-gray-600">
        {feature.description}
      </p>
    </>
  );
}

export function ProgressiveFeatureGrid({ features, className }: ProgressiveFeatureGridProps) {
  const { cssGrid } = useFeatureDetection();

  return (
    <div className={cn(
      'features-container',
      cssGrid ? 'features-grid-modern' : 'features-grid-legacy',
      className
    )}>
      {features.map(feature => (
        <ProgressiveCard key={feature.id} variant="glass" className="text-center">
          <FeatureContent feature={feature} />
        </ProgressiveCard>
      ))}
    </div>
  );
}