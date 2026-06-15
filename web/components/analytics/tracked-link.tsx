'use client';

/**
 * TrackedLink — a next/link that fires a PostHog event on click.
 *
 * Lets server components (which can't use onClick) instrument their CTAs:
 * import this client component and drop it in place of <Link>. Capture is
 * fire-and-forget and never blocks navigation.
 */
import Link from 'next/link';
import type { ComponentProps } from 'react';
import { capture, type AnalyticsEvent } from '@/lib/analytics';

type TrackedLinkProps = ComponentProps<typeof Link> & {
  event: AnalyticsEvent;
  eventProps?: Record<string, unknown>;
};

export function TrackedLink({
  event,
  eventProps,
  onClick,
  ...linkProps
}: TrackedLinkProps) {
  return (
    <Link
      {...linkProps}
      onClick={(e) => {
        try {
          capture(event, eventProps);
        } catch {
          /* never block navigation on analytics */
        }
        onClick?.(e);
      }}
    />
  );
}
