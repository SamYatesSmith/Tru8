import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Utility function to merge Tailwind CSS classes
 * Uses clsx for conditional classes and tailwind-merge to handle conflicts
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Parse a date string from the API into a Date, correcting for naive UTC.
 *
 * The backend stores timestamps as *naive UTC* (created_at/completed_at use
 * `datetime.now(timezone.utc).replace(tzinfo=None)`), so `.isoformat()` emits a
 * string with no `Z`/offset — e.g. "2025-07-20T14:30:00". `new Date()` reads a
 * timezone-less datetime as *local* time, skewing relative times by the local
 * UTC offset (under BST, +1h → a brand-new check shows "1 hour ago"). We treat
 * a timezone-less datetime as UTC by appending `Z`. Date-only strings
 * ("2024-01-15", already UTC per spec) and offset-bearing strings are untouched.
 */
export function parseServerDate(dateString: string): Date {
  const hasTime = /\d{2}:\d{2}/.test(dateString);
  const hasTz = /(Z|[+-]\d{2}:?\d{2})$/.test(dateString.trim());
  if (hasTime && !hasTz) {
    return new Date(`${dateString.trim()}Z`);
  }
  return new Date(dateString);
}

/**
 * Format date string for display
 * Shows relative time for recent dates, absolute date for older dates
 * Uses calendar day comparison (not 24-hour periods)
 */
export function formatDate(dateString: string): string {
  const date = parseServerDate(dateString);
  const now = new Date();

  // Compare by calendar date (ignore time component)
  const dateDay = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const nowDay = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diffDays = Math.round((nowDay.getTime() - dateDay.getTime()) / (1000 * 60 * 60 * 24));

  // Relative time for recent dates
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;

  // Absolute date for older dates
  return date.toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

/**
 * Format date with fine-grained relative time
 * Shows "X minutes ago", "X hours ago", etc.
 * Used for check metadata timestamps
 */
export function formatRelativeTime(dateString: string): string {
  const date = parseServerDate(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins} minute${diffMins !== 1 ? 's' : ''} ago`;
  if (diffHours < 24) return `${diffHours} hour${diffHours !== 1 ? 's' : ''} ago`;

  // Fall back to standard formatDate for older dates
  return formatDate(dateString);
}

/**
 * Format date as "Month Year" (e.g., "Jan 2024")
 * Used for evidence publication dates
 */
export function formatMonthYear(dateString: string | null): string {
  if (!dateString) return 'Date unknown';

  try {
    const date = parseServerDate(dateString);
    return date.toLocaleDateString('en-GB', {
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return 'Date unknown';
  }
}
