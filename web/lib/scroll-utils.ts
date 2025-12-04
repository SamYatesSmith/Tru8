/**
 * Scroll Utilities
 *
 * Shared scroll behavior functions for smooth navigation.
 */

/**
 * Smoothly scrolls to a section by its ID.
 *
 * @param sectionId - The ID of the element to scroll to (without #)
 */
export function scrollToSection(sectionId: string): void {
  const element = document.getElementById(sectionId);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
}
