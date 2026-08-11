'use client';

import { useEffect } from 'react';
import { usePathname, useSearchParams } from 'next/navigation';
import { captureAttribution } from '@/lib/attribution';

/**
 * Stores a ?src= / ?utm_source= tag first-touch on any page load, so an
 * outreach link's tag survives the walk to signup (lib/attribution.ts).
 * Renders nothing; mounted once in the root layout.
 */
export function AttributionCapture() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  useEffect(() => {
    const search = searchParams.toString();
    if (search) captureAttribution(`?${search}`);
    // Re-run on client-side navigations too — a tagged link can be an
    // internal one (e.g. /r/<id>?src=... shared into a thread).
  }, [pathname, searchParams]);

  return null;
}
