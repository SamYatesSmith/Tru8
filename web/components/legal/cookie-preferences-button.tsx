'use client';

interface CookiePreferencesButtonProps {
  children?: React.ReactNode;
}

export function CookiePreferencesButton({ children = 'Cookie Preferences' }: CookiePreferencesButtonProps) {
  const handleClick = () => {
    if (typeof window !== 'undefined' && (window as any).cookieyes) {
      (window as any).cookieyes.showBanner();
    }
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
