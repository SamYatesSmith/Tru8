/**
 * Smooth scroll utility for accessibility-compliant navigation
 * Phase 03: Accessibility Compliance
 *
 * FOUNDATION: Ready for future marketing anchor navigation implementation
 * Usage: Import and use with marketing navigation links that target #sections
 */

export function smoothScrollToSection(event: React.MouseEvent<HTMLAnchorElement>, href: string) {
  // Check if user prefers reduced motion
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (href.startsWith('#')) {
    event.preventDefault();

    const targetId = href.substring(1);
    const targetElement = document.getElementById(targetId);

    if (targetElement) {
      targetElement.scrollIntoView({
        behavior: prefersReducedMotion ? 'auto' : 'smooth',
        block: 'start'
      });

      // Focus the target element for screen readers
      targetElement.focus();
    }
  }
}

export function handleKeyboardNavigation(
  event: React.KeyboardEvent<HTMLAnchorElement>,
  href: string
) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    smoothScrollToSection(event as any, href);
  }
}