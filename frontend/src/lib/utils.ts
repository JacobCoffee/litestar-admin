import { type ClassValue, clsx } from "clsx";

/**
 * Combines class names using clsx.
 * Provides a consistent way to merge Tailwind classes.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

/**
 * Formats a date for display.
 */
export function formatDate(
  date: Date | string,
  options: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
  },
): string {
  const dateObj = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat("en-US", options).format(dateObj);
}

/**
 * Formats a number for display with locale-aware formatting.
 */
export function formatNumber(value: number, options: Intl.NumberFormatOptions = {}): string {
  return new Intl.NumberFormat("en-US", options).format(value);
}

/**
 * Truncates a string to a maximum length.
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) {
    return str;
  }
  return `${str.slice(0, maxLength - 3)}...`;
}

/**
 * Capitalizes the first letter of a string.
 */
export function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Converts a string to title case.
 */
export function toTitleCase(str: string): string {
  return str
    .toLowerCase()
    .split(" ")
    .map((word) => capitalize(word))
    .join(" ");
}

/**
 * Debounces a function call.
 */
export function debounce<T extends (...args: Parameters<T>) => ReturnType<T>>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Represents a segment of text, either highlighted or not.
 */
export interface TextSegment {
  text: string;
  highlighted: boolean;
}

/**
 * Splits text into segments based on search term matches.
 * Returns an array of segments with highlighted flag for matching parts.
 * Matching is case-insensitive.
 *
 * @param text - The text to search within
 * @param searchTerm - The term to highlight
 * @returns Array of text segments with highlighted flags
 */
export function getHighlightedSegments(text: string, searchTerm: string): TextSegment[] {
  if (!searchTerm || !text) {
    return [{ text, highlighted: false }];
  }

  const segments: TextSegment[] = [];
  const lowerText = text.toLowerCase();
  const lowerSearch = searchTerm.toLowerCase().trim();

  if (!lowerSearch) {
    return [{ text, highlighted: false }];
  }

  let lastIndex = 0;
  let matchIndex = lowerText.indexOf(lowerSearch);

  while (matchIndex !== -1) {
    // Add non-matching text before the match
    if (matchIndex > lastIndex) {
      segments.push({
        text: text.slice(lastIndex, matchIndex),
        highlighted: false,
      });
    }

    // Add the matching text
    segments.push({
      text: text.slice(matchIndex, matchIndex + lowerSearch.length),
      highlighted: true,
    });

    lastIndex = matchIndex + lowerSearch.length;
    matchIndex = lowerText.indexOf(lowerSearch, lastIndex);
  }

  // Add remaining non-matching text
  if (lastIndex < text.length) {
    segments.push({
      text: text.slice(lastIndex),
      highlighted: false,
    });
  }

  return segments.length > 0 ? segments : [{ text, highlighted: false }];
}
