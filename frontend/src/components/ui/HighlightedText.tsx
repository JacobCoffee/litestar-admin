"use client";

import { useMemo, type ReactNode } from "react";
import { cn, getHighlightedSegments } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

export interface HighlightedTextProps {
  /** The text content to display */
  text: string;
  /** The search term to highlight within the text */
  searchTerm?: string;
  /** Additional CSS classes for the wrapper span */
  className?: string;
  /** Additional CSS classes for highlighted segments */
  highlightClassName?: string;
  /** Whether highlighting is enabled (default: true when searchTerm is provided) */
  enabled?: boolean;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Renders text with search term highlighting.
 * Highlights all occurrences of the search term within the text.
 * Matching is case-insensitive.
 *
 * @example
 * ```tsx
 * <HighlightedText text="Hello World" searchTerm="world" />
 * // Renders: Hello <mark>World</mark>
 * ```
 */
export function HighlightedText({
  text,
  searchTerm,
  className,
  highlightClassName,
  enabled = true,
}: HighlightedTextProps): ReactNode {
  const segments = useMemo(() => {
    // Skip processing if highlighting is disabled or no search term
    if (!enabled || !searchTerm?.trim()) {
      return null;
    }
    return getHighlightedSegments(text, searchTerm);
  }, [text, searchTerm, enabled]);

  // If no segments (no search term or disabled), render plain text
  if (!segments) {
    return <span className={className}>{text}</span>;
  }

  // Check if any segment is highlighted
  const hasHighlight = segments.some((s) => s.highlighted);
  if (!hasHighlight) {
    return <span className={className}>{text}</span>;
  }

  return (
    <span className={className}>
      {segments.map((segment, index) =>
        segment.highlighted ? (
          <mark
            key={index}
            className={cn(
              // Base highlight styles for dark theme
              "bg-[var(--color-warning)]/30",
              "text-[var(--color-foreground)]",
              "rounded-[var(--radius-sm)]",
              "px-0.5",
              // Ensure no default mark styling
              "decoration-none",
              highlightClassName,
            )}
          >
            {segment.text}
          </mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </span>
  );
}

HighlightedText.displayName = "HighlightedText";

export default HighlightedText;
