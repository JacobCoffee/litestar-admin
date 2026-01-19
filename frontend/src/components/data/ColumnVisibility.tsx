"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  useId,
  type KeyboardEvent,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";

// ============================================================================
// Types
// ============================================================================

/**
 * Configuration for a column that can be toggled.
 */
export interface ColumnConfig {
  /** Unique key for the column */
  key: string;
  /** Display label for the column */
  label: string;
  /** Whether the column can be hidden (some columns may be required) */
  canHide?: boolean;
}

/**
 * Props for the ColumnVisibility component.
 */
export interface ColumnVisibilityProps {
  /** List of columns that can be toggled */
  columns: ColumnConfig[];
  /** Set of currently visible column keys */
  visibleColumns: Set<string>;
  /** Callback when column visibility changes */
  onVisibilityChange: (visibleColumns: Set<string>) => void;
  /** Minimum number of columns that must remain visible */
  minVisibleColumns?: number;
  /** Additional CSS classes */
  className?: string;
  /** Custom trigger button content */
  trigger?: ReactNode;
  /** Alignment of the dropdown menu */
  align?: "left" | "right";
  /** Whether to show the "Show All" / "Hide All" actions */
  showBulkActions?: boolean;
  /** Label for the button (shown on larger screens) */
  buttonLabel?: string;
  /** Disabled state */
  disabled?: boolean;
}

// ============================================================================
// Icons
// ============================================================================

function ColumnsIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
      <line x1="12" y1="3" x2="12" y2="21" />
    </svg>
  );
}

function ChevronDownIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

// ============================================================================
// Subcomponents
// ============================================================================

interface ColumnCheckboxProps {
  column: ColumnConfig;
  isVisible: boolean;
  isDisabled: boolean;
  onToggle: () => void;
}

function ColumnCheckbox({ column, isVisible, isDisabled, onToggle }: ColumnCheckboxProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!isDisabled) {
        onToggle();
      }
    }
  };

  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={isVisible}
      aria-disabled={isDisabled}
      onClick={() => !isDisabled && onToggle()}
      onKeyDown={handleKeyDown}
      className={cn(
        "w-full px-3 py-2",
        "flex items-center gap-3",
        "text-sm text-left",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
        isDisabled
          ? "cursor-not-allowed opacity-50"
          : "hover:bg-[var(--color-card-hover)] cursor-pointer",
      )}
    >
      {/* Checkbox indicator */}
      <span
        className={cn(
          "flex h-4 w-4 shrink-0 items-center justify-center",
          "rounded-[var(--radius-sm)]",
          "border transition-colors duration-150",
          isVisible
            ? "bg-[var(--color-primary)] border-[var(--color-primary)]"
            : "border-[var(--color-border)]",
          !isDisabled && !isVisible && "group-hover:border-[var(--color-muted)]",
        )}
      >
        {isVisible && <CheckIcon className="h-3 w-3 text-[var(--color-primary-foreground)]" />}
      </span>
      {/* Column label */}
      <span
        className={cn(
          "flex-1 truncate",
          isVisible ? "text-[var(--color-foreground)]" : "text-[var(--color-muted)]",
        )}
      >
        {column.label}
      </span>
      {/* Required indicator */}
      {column.canHide === false && (
        <span className="text-xs text-[var(--color-muted)]">Required</span>
      )}
    </button>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ColumnVisibility({
  columns,
  visibleColumns,
  onVisibilityChange,
  minVisibleColumns = 1,
  className,
  trigger,
  align = "right",
  showBulkActions = true,
  buttonLabel = "Columns",
  disabled = false,
}: ColumnVisibilityProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownId = useId();
  const dropdownRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Calculate which columns can be hidden
  const hidableColumns = columns.filter((col) => col.canHide !== false);
  const requiredColumns = columns.filter((col) => col.canHide === false);
  const visibleHidableCount = hidableColumns.filter((col) => visibleColumns.has(col.key)).length;

  // Check if we can hide more columns (respecting minimum)
  const canHideMore = visibleHidableCount > minVisibleColumns;

  // Check if a specific column can be hidden
  const canHideColumn = useCallback(
    (column: ColumnConfig) => {
      if (column.canHide === false) return false;
      if (!visibleColumns.has(column.key)) return true; // Already hidden, can toggle on
      return canHideMore;
    },
    [visibleColumns, canHideMore],
  );

  // Toggle a single column
  const handleToggleColumn = useCallback(
    (key: string) => {
      const column = columns.find((col) => col.key === key);
      if (!column) return;

      // Check if column can be hidden
      if (visibleColumns.has(key) && !canHideColumn(column)) return;

      const newVisible = new Set(visibleColumns);
      if (newVisible.has(key)) {
        newVisible.delete(key);
      } else {
        newVisible.add(key);
      }
      onVisibilityChange(newVisible);
    },
    [columns, visibleColumns, canHideColumn, onVisibilityChange],
  );

  // Show all columns
  const handleShowAll = useCallback(() => {
    const allKeys = new Set(columns.map((col) => col.key));
    onVisibilityChange(allKeys);
  }, [columns, onVisibilityChange]);

  // Hide all columns (except required and minimum)
  const handleHideAll = useCallback(() => {
    // Keep required columns and minimum number of hidable columns
    const newVisible = new Set(requiredColumns.map((col) => col.key));

    // Add minimum number of hidable columns if needed
    const remainingToAdd = Math.max(0, minVisibleColumns - newVisible.size);
    const hidableKeys = hidableColumns.map((col) => col.key);
    for (let i = 0; i < Math.min(remainingToAdd, hidableKeys.length); i++) {
      const key = hidableKeys[i];
      if (key !== undefined) {
        newVisible.add(key);
      }
    }

    onVisibilityChange(newVisible);
  }, [requiredColumns, hidableColumns, minVisibleColumns, onVisibilityChange]);

  // Close dropdown on click outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>) => {
      if (e.key === "Escape") {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    },
    [],
  );

  // Count visible columns for badge
  const visibleCount = visibleColumns.size;
  const totalCount = columns.length;

  return (
    <div ref={dropdownRef} className={cn("relative", className)} onKeyDown={handleKeyDown}>
      {/* Trigger button */}
      {trigger ? (
        <div onClick={() => !disabled && setIsOpen(!isOpen)}>{trigger}</div>
      ) : (
        <Button
          ref={buttonRef}
          variant="secondary"
          size="sm"
          onClick={() => setIsOpen(!isOpen)}
          disabled={disabled}
          aria-expanded={isOpen}
          aria-controls={dropdownId}
          aria-haspopup="menu"
        >
          <ColumnsIcon className="h-4 w-4" />
          <span className="hidden sm:inline">{buttonLabel}</span>
          {/* Column count badge */}
          <span
            className={cn(
              "hidden sm:inline-flex items-center justify-center",
              "min-w-[1.25rem] h-5 px-1.5",
              "rounded-full",
              "text-xs font-medium",
              "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
            )}
          >
            {visibleCount}/{totalCount}
          </span>
          <ChevronDownIcon
            className={cn("h-4 w-4 transition-transform duration-150", isOpen && "rotate-180")}
          />
        </Button>
      )}

      {/* Dropdown menu */}
      {isOpen && (
        <div
          id={dropdownId}
          role="menu"
          aria-label="Toggle column visibility"
          className={cn(
            "absolute top-full z-50 mt-1",
            "w-[240px] py-1",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "animate-[scaleIn_100ms_ease-out]",
            align === "right" ? "right-0" : "left-0",
          )}
        >
          {/* Header */}
          <div
            className={cn(
              "px-3 py-2",
              "border-b border-[var(--color-border)]",
              "flex items-center justify-between",
            )}
          >
            <span className="text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wide">
              Toggle columns
            </span>
            <span className="text-xs text-[var(--color-muted)]">
              {visibleCount} of {totalCount}
            </span>
          </div>

          {/* Bulk actions */}
          {showBulkActions && (
            <div className={cn("px-3 py-2", "flex items-center gap-2", "border-b border-[var(--color-border)]")}>
              <button
                type="button"
                onClick={handleShowAll}
                disabled={visibleCount === totalCount}
                className={cn(
                  "flex items-center gap-1.5 px-2 py-1",
                  "text-xs font-medium",
                  "rounded-[var(--radius-sm)]",
                  "transition-colors duration-150",
                  visibleCount === totalCount
                    ? "text-[var(--color-muted)] cursor-not-allowed"
                    : "text-[var(--color-foreground)] hover:bg-[var(--color-card-hover)]",
                )}
              >
                <EyeIcon className="h-3.5 w-3.5" />
                Show all
              </button>
              <button
                type="button"
                onClick={handleHideAll}
                disabled={visibleHidableCount <= minVisibleColumns}
                className={cn(
                  "flex items-center gap-1.5 px-2 py-1",
                  "text-xs font-medium",
                  "rounded-[var(--radius-sm)]",
                  "transition-colors duration-150",
                  visibleHidableCount <= minVisibleColumns
                    ? "text-[var(--color-muted)] cursor-not-allowed"
                    : "text-[var(--color-foreground)] hover:bg-[var(--color-card-hover)]",
                )}
              >
                <EyeOffIcon className="h-3.5 w-3.5" />
                Hide all
              </button>
            </div>
          )}

          {/* Column list */}
          <div className="max-h-[280px] overflow-y-auto">
            {columns.map((column) => {
              const isVisible = visibleColumns.has(column.key);
              const isDisabled = isVisible && !canHideColumn(column);

              return (
                <ColumnCheckbox
                  key={column.key}
                  column={column}
                  isVisible={isVisible}
                  isDisabled={isDisabled}
                  onToggle={() => handleToggleColumn(column.key)}
                />
              );
            })}
          </div>

          {/* Footer hint */}
          {minVisibleColumns > 0 && (
            <div className={cn("px-3 py-2", "border-t border-[var(--color-border)]")}>
              <p className="text-xs text-[var(--color-muted)]">
                At least {minVisibleColumns} column{minVisibleColumns !== 1 ? "s" : ""} must be
                visible
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

ColumnVisibility.displayName = "ColumnVisibility";

// ============================================================================
// Hook for managing column visibility state
// ============================================================================

export interface UseColumnVisibilityOptions {
  /** Initial set of visible column keys (defaults to all columns) */
  initialVisibleColumns?: Set<string> | string[];
  /** Column configurations */
  columns: ColumnConfig[];
  /** Storage key for persisting visibility state */
  storageKey?: string;
}

export interface UseColumnVisibilityReturn {
  /** Currently visible column keys */
  visibleColumns: Set<string>;
  /** Update visible columns */
  setVisibleColumns: (columns: Set<string>) => void;
  /** Toggle a single column's visibility */
  toggleColumn: (key: string) => void;
  /** Show all columns */
  showAll: () => void;
  /** Hide all columns (except required) */
  hideAll: () => void;
  /** Check if a column is visible */
  isVisible: (key: string) => boolean;
  /** Reset to initial state */
  reset: () => void;
}

export function useColumnVisibility({
  initialVisibleColumns,
  columns,
  storageKey,
}: UseColumnVisibilityOptions): UseColumnVisibilityReturn {
  // Compute initial visible columns
  const getInitialVisibleColumns = useCallback((): Set<string> => {
    // Try to load from storage first
    if (storageKey && typeof window !== "undefined") {
      try {
        const stored = localStorage.getItem(storageKey);
        if (stored) {
          const parsed = JSON.parse(stored) as string[];
          if (Array.isArray(parsed)) {
            return new Set(parsed);
          }
        }
      } catch {
        // Ignore storage errors
      }
    }

    // Use provided initial columns
    if (initialVisibleColumns) {
      if (initialVisibleColumns instanceof Set) {
        return initialVisibleColumns;
      }
      return new Set(initialVisibleColumns);
    }

    // Default to all columns visible
    return new Set(columns.map((col) => col.key));
  }, [initialVisibleColumns, columns, storageKey]);

  const [visibleColumns, setVisibleColumnsState] = useState<Set<string>>(getInitialVisibleColumns);

  // Persist to storage when visibility changes
  const setVisibleColumns = useCallback(
    (newVisible: Set<string>) => {
      setVisibleColumnsState(newVisible);

      if (storageKey && typeof window !== "undefined") {
        try {
          localStorage.setItem(storageKey, JSON.stringify(Array.from(newVisible)));
        } catch {
          // Ignore storage errors
        }
      }
    },
    [storageKey],
  );

  const toggleColumn = useCallback(
    (key: string) => {
      const next = new Set(visibleColumns);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      setVisibleColumns(next);
    },
    [visibleColumns, setVisibleColumns],
  );

  const showAll = useCallback(() => {
    setVisibleColumns(new Set(columns.map((col) => col.key)));
  }, [columns, setVisibleColumns]);

  const hideAll = useCallback(() => {
    // Keep only required columns
    const required = columns.filter((col) => col.canHide === false).map((col) => col.key);
    if (required.length > 0) {
      setVisibleColumns(new Set(required));
    } else {
      // If no required columns, keep at least the first column
      const firstKey = columns[0]?.key;
      setVisibleColumns(new Set(firstKey ? [firstKey] : []));
    }
  }, [columns, setVisibleColumns]);

  const isVisible = useCallback((key: string) => visibleColumns.has(key), [visibleColumns]);

  const reset = useCallback(() => {
    // Clear storage
    if (storageKey && typeof window !== "undefined") {
      try {
        localStorage.removeItem(storageKey);
      } catch {
        // Ignore storage errors
      }
    }
    // Reset to initial/default state
    setVisibleColumnsState(new Set(columns.map((col) => col.key)));
  }, [columns, storageKey]);

  return {
    visibleColumns,
    setVisibleColumns,
    toggleColumn,
    showAll,
    hideAll,
    isVisible,
    reset,
  };
}
