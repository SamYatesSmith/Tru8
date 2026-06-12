'use client';

import { openConsentBanner } from '@/lib/consent';

interface CookiePreferencesButtonProps {
  children?: React.ReactNode;
}

export function CookiePreferencesButton({ children = 'Cookie Preferences' }: CookiePreferencesButtonProps) {
  const handleClick = () => {
    openConsentBanner();
  };

  return (
    <button
      onClick={handleClick}
      className="text-accent hover:text-accent/80 underline"
    >
      {children}
    </button>
  );
}
