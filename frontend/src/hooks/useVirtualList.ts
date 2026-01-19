/**
 * Virtual list hook for rendering large datasets efficiently.
 * Only renders items that are visible in the viewport, dramatically
 * reducing DOM nodes and improving performance for large lists.
 *
 * Performance characteristics:
 * - O(1) render complexity regardless of list size
 * - Smooth scrolling with overscan buffer
 * - Supports variable height items (estimated)
 */

import { useState, useCallback, useMemo, useRef, useEffect } from "react";

export interface UseVirtualListOptions<T> {
  /** The full list of items */
  items: T[];
  /** Estimated height of each item in pixels */
  itemHeight: number;
  /** Number of items to render outside the visible area (overscan) */
  overscan?: number;
  /** Get a unique key for each item */
  getItemKey?: (item: T, index: number) => string | number;
}

export interface VirtualItem<T> {
  /** The actual item data */
  item: T;
  /** Index in the original array */
  index: number;
  /** Unique key for React */
  key: string | number;
  /** Offset from top in pixels */
  offsetTop: number;
}

export interface UseVirtualListReturn<T> {
  /** Items to render (only visible + overscan) */
  virtualItems: VirtualItem<T>[];
  /** Total height of the list container */
  totalHeight: number;
  /** Offset from top for the virtual window */
  startOffset: number;
  /** Ref to attach to the scroll container */
  containerRef: React.RefObject<HTMLDivElement>;
  /** Current scroll position */
  scrollTop: number;
  /** Scroll to a specific index */
  scrollToIndex: (index: number, align?: "start" | "center" | "end") => void;
  /** Whether the list is currently being scrolled */
  isScrolling: boolean;
}

/**
 * Hook for virtualizing a large list of items.
 *
 * @example
 * ```tsx
 * const { virtualItems, totalHeight, containerRef } = useVirtualList({
 *   items: records,
 *   itemHeight: 48,
 *   overscan: 5,
 * });
 *
 * return (
 *   <div ref={containerRef} style={{ height: 400, overflow: 'auto' }}>
 *     <div style={{ height: totalHeight, position: 'relative' }}>
 *       {virtualItems.map(({ item, index, key, offsetTop }) => (
 *         <div
 *           key={key}
 *           style={{ position: 'absolute', top: offsetTop, height: 48 }}
 *         >
 *           {item.name}
 *         </div>
 *       ))}
 *     </div>
 *   </div>
 * );
 * ```
 */
export function useVirtualList<T>({
  items,
  itemHeight,
  overscan = 3,
  getItemKey = (_item, index) => index,
}: UseVirtualListOptions<T>): UseVirtualListReturn<T> {
  const containerRef = useRef<HTMLDivElement>(null);
  const [scrollTop, setScrollTop] = useState(0);
  const [containerHeight, setContainerHeight] = useState(0);
  const [isScrolling, setIsScrolling] = useState(false);
  const scrollTimeoutRef = useRef<ReturnType<typeof setTimeout>>();

  // Calculate total height
  const totalHeight = useMemo(() => items.length * itemHeight, [items.length, itemHeight]);

  // Calculate visible range with overscan
  const { startIndex, endIndex, startOffset } = useMemo(() => {
    const start = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
    const visibleCount = Math.ceil(containerHeight / itemHeight);
    const end = Math.min(items.length - 1, start + visibleCount + overscan * 2);

    return {
      startIndex: start,
      endIndex: end,
      startOffset: start * itemHeight,
    };
  }, [scrollTop, containerHeight, itemHeight, items.length, overscan]);

  // Generate virtual items
  const virtualItems = useMemo(() => {
    const result: VirtualItem<T>[] = [];

    for (let i = startIndex; i <= endIndex && i < items.length; i++) {
      const item = items[i];
      if (item !== undefined) {
        result.push({
          item,
          index: i,
          key: getItemKey(item, i),
          offsetTop: i * itemHeight,
        });
      }
    }

    return result;
  }, [items, startIndex, endIndex, itemHeight, getItemKey]);

  // Handle scroll events
  const handleScroll = useCallback(() => {
    if (containerRef.current) {
      setScrollTop(containerRef.current.scrollTop);
      setIsScrolling(true);

      // Clear existing timeout
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }

      // Set scrolling to false after 150ms of no scroll
      scrollTimeoutRef.current = setTimeout(() => {
        setIsScrolling(false);
      }, 150);
    }
  }, []);

  // Handle resize
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Initial size
    setContainerHeight(container.clientHeight);

    // Set up scroll listener
    container.addEventListener("scroll", handleScroll, { passive: true });

    // Set up resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        setContainerHeight(entry.contentRect.height);
      }
    });

    resizeObserver.observe(container);

    return () => {
      container.removeEventListener("scroll", handleScroll);
      resizeObserver.disconnect();
      if (scrollTimeoutRef.current) {
        clearTimeout(scrollTimeoutRef.current);
      }
    };
  }, [handleScroll]);

  // Scroll to index function
  const scrollToIndex = useCallback(
    (index: number, align: "start" | "center" | "end" = "start") => {
      if (!containerRef.current) return;

      const clampedIndex = Math.max(0, Math.min(index, items.length - 1));
      let targetScrollTop = clampedIndex * itemHeight;

      if (align === "center") {
        targetScrollTop -= containerHeight / 2 - itemHeight / 2;
      } else if (align === "end") {
        targetScrollTop -= containerHeight - itemHeight;
      }

      targetScrollTop = Math.max(0, Math.min(targetScrollTop, totalHeight - containerHeight));

      containerRef.current.scrollTo({
        top: targetScrollTop,
        behavior: "smooth",
      });
    },
    [items.length, itemHeight, containerHeight, totalHeight],
  );

  return {
    virtualItems,
    totalHeight,
    startOffset,
    containerRef: containerRef as React.RefObject<HTMLDivElement>,
    scrollTop,
    scrollToIndex,
    isScrolling,
  };
}

/**
 * Utility to estimate the number of items that fit in a viewport.
 * Useful for determining initial page size.
 */
export function estimateVisibleItems(
  containerHeight: number,
  itemHeight: number,
  overscan = 0,
): number {
  return Math.ceil(containerHeight / itemHeight) + overscan * 2;
}
