"use client";

import { useState, useCallback, useRef, useEffect, type KeyboardEvent, type RefObject } from "react";

/**
 * Keyboard navigation options for tables.
 */
export interface TableKeyboardNavigationOptions {
  /** Total number of rows in the table */
  rowCount: number;
  /** Whether row selection is enabled */
  selectable?: boolean;
  /** Callback when selection changes (for Ctrl/Cmd+A) */
  onSelectAll?: () => void;
  /** Callback when row is activated via Enter/Space */
  onActivateRow?: (rowIndex: number) => void;
  /** Callback when row is toggled via Enter (when selectable) */
  onToggleRow?: (rowIndex: number) => void;
  /** Current page (1-indexed) for Page Up/Down support */
  page?: number;
  /** Total pages for Page Up/Down support */
  totalPages?: number;
  /** Callback to change page */
  onPageChange?: ((page: number) => void) | undefined;
  /** Whether navigation is enabled */
  enabled?: boolean;
}

/**
 * Return type for the useTableKeyboardNavigation hook.
 */
export interface TableKeyboardNavigationReturn {
  /** Currently focused row index (-1 if none) */
  focusedRowIndex: number;
  /** Set the focused row index */
  setFocusedRowIndex: (index: number) => void;
  /** Handle keyboard events on the table container */
  handleTableKeyDown: (e: KeyboardEvent<HTMLElement>) => void;
  /** Get props for a row to enable keyboard navigation */
  getRowProps: (rowIndex: number) => TableRowNavigationProps;
  /** Ref to attach to the table container for focus management */
  tableRef: RefObject<HTMLDivElement>;
  /** Whether the table has keyboard focus */
  isTableFocused: boolean;
}

/**
 * Props returned by getRowProps for keyboard navigation.
 */
export interface TableRowNavigationProps {
  /** Tab index for the row (-1 for non-focused, 0 for focused) */
  tabIndex: number;
  /** Data attribute for focused state */
  "data-focused": boolean;
  /** ARIA selected state */
  "aria-rowindex": number;
  /** Role for the row */
  role: "row";
  /** Handler for row focus */
  onFocus: () => void;
  /** Handler for row click */
  onClick: () => void;
  /** Handler for row keyboard events */
  onKeyDown: (e: KeyboardEvent<HTMLTableRowElement>) => void;
}

/**
 * Detect if running on macOS for modifier key handling.
 */
function isMacOS(): boolean {
  if (typeof window === "undefined") return false;
  return navigator.platform.toLowerCase().includes("mac");
}

/**
 * Hook for managing keyboard navigation in data tables.
 *
 * Provides:
 * - Arrow Up/Down: Navigate between rows
 * - Home/End: Go to first/last row
 * - Page Up/Page Down: Change pagination (if available)
 * - Ctrl/Cmd+A: Select all rows (if selectable)
 * - Enter/Space: Activate or toggle row
 * - Escape: Clear focus
 *
 * @example
 * ```tsx
 * const {
 *   focusedRowIndex,
 *   handleTableKeyDown,
 *   getRowProps,
 *   tableRef,
 * } = useTableKeyboardNavigation({
 *   rowCount: data.length,
 *   selectable: true,
 *   onSelectAll: handleSelectAll,
 *   onActivateRow: handleRowClick,
 * });
 * ```
 */
export function useTableKeyboardNavigation({
  rowCount,
  selectable = false,
  onSelectAll,
  onActivateRow,
  onToggleRow,
  page = 1,
  totalPages = 1,
  onPageChange,
  enabled = true,
}: TableKeyboardNavigationOptions): TableKeyboardNavigationReturn {
  const [focusedRowIndex, setFocusedRowIndex] = useState<number>(-1);
  const [isTableFocused, setIsTableFocused] = useState(false);
  const tableRef = useRef<HTMLDivElement>(null!);
  const rowRefs = useRef<Map<number, HTMLTableRowElement>>(new Map());

  // Reset focus when row count changes
  useEffect(() => {
    if (focusedRowIndex >= rowCount) {
      setFocusedRowIndex(rowCount > 0 ? rowCount - 1 : -1);
    }
  }, [rowCount, focusedRowIndex]);

  // Scroll focused row into view
  const scrollRowIntoView = useCallback((index: number) => {
    const row = rowRefs.current.get(index);
    if (row) {
      row.scrollIntoView({ block: "nearest", behavior: "smooth" });
      row.focus();
    }
  }, []);

  // Navigate to a specific row
  const navigateToRow = useCallback(
    (index: number) => {
      if (index < 0 || index >= rowCount) return;
      setFocusedRowIndex(index);
      scrollRowIntoView(index);
    },
    [rowCount, scrollRowIntoView],
  );

  // Move focus by a delta amount
  const moveFocus = useCallback(
    (delta: number) => {
      if (rowCount === 0) return;

      let newIndex: number;
      if (focusedRowIndex === -1) {
        // If no row focused, start from first or last based on direction
        newIndex = delta > 0 ? 0 : rowCount - 1;
      } else {
        newIndex = Math.max(0, Math.min(rowCount - 1, focusedRowIndex + delta));
      }

      navigateToRow(newIndex);
    },
    [focusedRowIndex, rowCount, navigateToRow],
  );

  // Handle table-level keyboard events
  const handleTableKeyDown = useCallback(
    (e: KeyboardEvent<HTMLElement>) => {
      if (!enabled || rowCount === 0) return;

      const isMac = isMacOS();
      const isModifierPressed = isMac ? e.metaKey : e.ctrlKey;

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          moveFocus(1);
          break;

        case "ArrowUp":
          e.preventDefault();
          moveFocus(-1);
          break;

        case "Home":
          e.preventDefault();
          if (isModifierPressed) {
            // Ctrl/Cmd+Home: Go to first row and first page
            if (onPageChange && page > 1) {
              onPageChange(1);
            }
          }
          navigateToRow(0);
          break;

        case "End":
          e.preventDefault();
          if (isModifierPressed) {
            // Ctrl/Cmd+End: Go to last row and last page
            if (onPageChange && page < totalPages) {
              onPageChange(totalPages);
            }
          }
          navigateToRow(rowCount - 1);
          break;

        case "PageDown":
          e.preventDefault();
          if (onPageChange && page < totalPages) {
            onPageChange(page + 1);
            // Focus first row on new page after navigation
            setTimeout(() => navigateToRow(0), 100);
          } else {
            // Move down by visible rows (estimate ~10)
            moveFocus(10);
          }
          break;

        case "PageUp":
          e.preventDefault();
          if (onPageChange && page > 1) {
            onPageChange(page - 1);
            // Focus last row on previous page after navigation
            setTimeout(() => navigateToRow(rowCount - 1), 100);
          } else {
            // Move up by visible rows (estimate ~10)
            moveFocus(-10);
          }
          break;

        case "a":
        case "A":
          // Ctrl/Cmd+A: Select all
          if (isModifierPressed && selectable && onSelectAll) {
            e.preventDefault();
            onSelectAll();
          }
          break;

        case "Escape":
          // Clear focus
          setFocusedRowIndex(-1);
          tableRef.current?.focus();
          break;

        case "Enter":
        case " ":
          // Activate or toggle the focused row
          if (focusedRowIndex >= 0) {
            e.preventDefault();
            if (selectable && onToggleRow) {
              onToggleRow(focusedRowIndex);
            } else if (onActivateRow) {
              onActivateRow(focusedRowIndex);
            }
          }
          break;
      }
    },
    [
      enabled,
      rowCount,
      moveFocus,
      navigateToRow,
      focusedRowIndex,
      selectable,
      onSelectAll,
      onActivateRow,
      onToggleRow,
      onPageChange,
      page,
      totalPages,
    ],
  );

  // Handle row-level keyboard events
  const handleRowKeyDown = useCallback(
    (rowIndex: number, e: KeyboardEvent<HTMLTableRowElement>) => {
      // Delegate to table handler but with row context
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (selectable && onToggleRow) {
          onToggleRow(rowIndex);
        } else if (onActivateRow) {
          onActivateRow(rowIndex);
        }
      } else {
        // Let table handler deal with navigation keys
        handleTableKeyDown(e as unknown as KeyboardEvent<HTMLElement>);
      }
    },
    [handleTableKeyDown, selectable, onActivateRow, onToggleRow],
  );

  // Get props for a table row
  const getRowProps = useCallback(
    (rowIndex: number): TableRowNavigationProps => {
      const isFocused = focusedRowIndex === rowIndex && isTableFocused;

      return {
        tabIndex: isFocused ? 0 : -1,
        "data-focused": isFocused,
        "aria-rowindex": rowIndex + 1, // 1-indexed for ARIA
        role: "row" as const,
        onFocus: () => {
          setFocusedRowIndex(rowIndex);
          setIsTableFocused(true);
        },
        onClick: () => {
          setFocusedRowIndex(rowIndex);
          if (onActivateRow) {
            onActivateRow(rowIndex);
          }
        },
        onKeyDown: (e: KeyboardEvent<HTMLTableRowElement>) => handleRowKeyDown(rowIndex, e),
      };
    },
    [focusedRowIndex, isTableFocused, onActivateRow, handleRowKeyDown],
  );

  // Track table focus state
  useEffect(() => {
    const table = tableRef.current;
    if (!table) return;

    const handleFocusIn = () => setIsTableFocused(true);
    const handleFocusOut = (e: FocusEvent) => {
      // Only unfocus if focus is leaving the table entirely
      if (!table.contains(e.relatedTarget as Node)) {
        setIsTableFocused(false);
      }
    };

    table.addEventListener("focusin", handleFocusIn);
    table.addEventListener("focusout", handleFocusOut);

    return () => {
      table.removeEventListener("focusin", handleFocusIn);
      table.removeEventListener("focusout", handleFocusOut);
    };
  }, []);

  return {
    focusedRowIndex,
    setFocusedRowIndex,
    handleTableKeyDown,
    getRowProps,
    tableRef,
    isTableFocused,
  };
}

/**
 * Format keyboard shortcut hints for table navigation.
 */
export function getTableNavigationHints(): Array<{ keys: string; description: string }> {
  const isMac = typeof window !== "undefined" && navigator.platform.toLowerCase().includes("mac");
  const modKey = isMac ? "\u2318" : "Ctrl";

  return [
    { keys: "\u2191 \u2193", description: "Navigate rows" },
    { keys: "Home / End", description: "First / last row" },
    { keys: "Page Up / Down", description: "Previous / next page" },
    { keys: `${modKey}+A`, description: "Select all" },
    { keys: "Enter / Space", description: "Activate row" },
    { keys: "Esc", description: "Clear focus" },
  ];
}
