"use client";

import { useState, useCallback, useMemo, useId, type ReactNode, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
  type SortDirection,
} from "@/components/ui/Table";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Loading";

// ============================================================================
// Types
// ============================================================================

export interface Column<T> {
  /** Column key - can be a key of T or a custom string for computed columns */
  key: keyof T | string;
  /** Column header text */
  header: string;
  /** Whether this column can be sorted */
  sortable?: boolean;
  /** Custom render function for cell content */
  render?: (value: unknown, row: T, rowIndex: number) => ReactNode;
  /** Column width (CSS value) */
  width?: string;
  /**
   * Responsive priority for column visibility
   * 1 = always show
   * 2 = hide on tablet and below (< 1024px)
   * 3 = hide on mobile (< 768px)
   */
  priority?: 1 | 2 | 3;
  /** Custom cell className */
  className?: string;
  /** Text alignment */
  align?: "left" | "center" | "right";
}

export interface DataTableProps<T> {
  /** Column definitions */
  columns: Column<T>[];
  /** Data rows */
  data: T[];
  /** Loading state */
  isLoading?: boolean;
  /** Current page (1-indexed) */
  page?: number;
  /** Items per page */
  pageSize?: number;
  /** Total items across all pages */
  totalItems?: number;
  /** Page change callback */
  onPageChange?: (page: number) => void;
  /** Page size change callback */
  onPageSizeChange?: (size: number) => void;
  /** Available page size options */
  pageSizeOptions?: number[];
  /** Current sort column key */
  sortBy?: string;
  /** Current sort order */
  sortOrder?: "asc" | "desc";
  /** Sort change callback */
  onSort?: (column: string) => void;
  /** Enable row selection */
  selectable?: boolean;
  /** Currently selected row IDs */
  selectedIds?: Set<string | number>;
  /** Selection change callback */
  onSelectionChange?: (ids: Set<string | number>) => void;
  /** Function to get unique ID from a row */
  getRowId?: (row: T) => string | number;
  /** Row click callback */
  onRowClick?: (row: T, rowIndex: number) => void;
  /** Message to show when data is empty */
  emptyMessage?: string;
  /** Enable column visibility toggle */
  showColumnToggle?: boolean;
  /** Custom className for the table wrapper */
  className?: string;
  /** Enable striped rows */
  striped?: boolean;
  /** Number of skeleton rows to show when loading */
  skeletonRows?: number;
}

// ============================================================================
// Icons
// ============================================================================

function ChevronLeftIcon({ className }: { className?: string }) {
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
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
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
      <path d="M9 18l6-6-6-6" />
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

function MinusIcon({ className }: { className?: string }) {
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
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

// ============================================================================
// Subcomponents
// ============================================================================

interface CheckboxProps {
  checked: boolean;
  indeterminate?: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
  id?: string;
}

function Checkbox({
  checked,
  indeterminate = false,
  onChange,
  disabled = false,
  label,
  id,
}: CheckboxProps) {
  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (!disabled) {
        onChange(!checked);
      }
    }
  };

  return (
    <button
      id={id}
      type="button"
      role="checkbox"
      aria-checked={indeterminate ? "mixed" : checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      onKeyDown={handleKeyDown}
      className={cn(
        "h-4 w-4 shrink-0",
        "rounded-[var(--radius-sm)]",
        "border border-[var(--color-border)]",
        "transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2",
        "focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2",
        "focus-visible:ring-offset-[var(--color-background)]",
        "disabled:cursor-not-allowed disabled:opacity-50",
        (checked || indeterminate) && [
          "bg-[var(--color-primary)] border-[var(--color-primary)]",
          "text-[var(--color-primary-foreground)]",
        ],
        !checked && !indeterminate && "hover:border-[var(--color-muted)]",
      )}
    >
      {checked && !indeterminate && <CheckIcon className="h-3 w-3" />}
      {indeterminate && <MinusIcon className="h-3 w-3" />}
    </button>
  );
}

interface ColumnVisibilityDropdownProps<T> {
  columns: Column<T>[];
  visibleColumns: Set<string>;
  onToggleColumn: (key: string) => void;
}

function ColumnVisibilityDropdown<T>({
  columns,
  visibleColumns,
  onToggleColumn,
}: ColumnVisibilityDropdownProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownId = useId();

  return (
    <div className="relative">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={dropdownId}
        aria-haspopup="menu"
      >
        <EyeIcon className="h-4 w-4" />
        <span className="hidden sm:inline">Columns</span>
        <ChevronDownIcon className={cn("h-4 w-4 transition-transform", isOpen && "rotate-180")} />
      </Button>
      {isOpen && (
        <>
          {/* Backdrop */}
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} aria-hidden="true" />
          {/* Dropdown menu */}
          <div
            id={dropdownId}
            role="menu"
            className={cn(
              "absolute right-0 top-full z-50 mt-1",
              "min-w-[180px] py-1",
              "rounded-[var(--radius-md)]",
              "border border-[var(--color-border)]",
              "bg-[var(--color-card)]",
              "shadow-lg shadow-black/20",
            )}
          >
            <div className="px-3 py-2 text-xs font-semibold text-[var(--color-muted)] uppercase tracking-wide">
              Toggle columns
            </div>
            {columns.map((column) => {
              const key = String(column.key);
              const isVisible = visibleColumns.has(key);
              return (
                <button
                  key={key}
                  role="menuitemcheckbox"
                  aria-checked={isVisible}
                  onClick={() => onToggleColumn(key)}
                  className={cn(
                    "w-full px-3 py-2",
                    "flex items-center gap-2",
                    "text-sm text-left",
                    "hover:bg-[var(--color-card-hover)]",
                    "transition-colors duration-150",
                    "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
                  )}
                >
                  <span
                    className={cn(
                      "flex h-4 w-4 items-center justify-center",
                      "rounded-[var(--radius-sm)]",
                      "border border-[var(--color-border)]",
                      isVisible && "bg-[var(--color-primary)] border-[var(--color-primary)]",
                    )}
                  >
                    {isVisible && <CheckIcon className="h-3 w-3 text-white" />}
                  </span>
                  <span className={cn(!isVisible && "text-[var(--color-muted)]")}>
                    {column.header}
                  </span>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}

interface PaginationProps {
  page: number;
  pageSize: number;
  totalItems: number;
  pageSizeOptions: number[];
  onPageChange: (page: number) => void;
  onPageSizeChange: (size: number) => void;
}

function Pagination({
  page,
  pageSize,
  totalItems,
  pageSizeOptions,
  onPageChange,
  onPageSizeChange,
}: PaginationProps) {
  const totalPages = Math.ceil(totalItems / pageSize);
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, totalItems);

  return (
    <div
      className={cn(
        "flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between",
        "px-4 py-3",
        "border-t border-[var(--color-border)]",
        "bg-[var(--color-card)]/50",
      )}
    >
      {/* Page info */}
      <div className="text-sm text-[var(--color-muted)]">
        {totalItems > 0 ? (
          <>
            Showing <span className="font-medium text-[var(--color-foreground)]">{startItem}</span>
            {" to "}
            <span className="font-medium text-[var(--color-foreground)]">{endItem}</span>
            {" of "}
            <span className="font-medium text-[var(--color-foreground)]">{totalItems}</span>
            {" results"}
          </>
        ) : (
          "No results"
        )}
      </div>

      <div className="flex items-center gap-4">
        {/* Page size selector */}
        <div className="flex items-center gap-2">
          <label
            htmlFor="page-size"
            className="text-sm text-[var(--color-muted)] whitespace-nowrap"
          >
            Per page:
          </label>
          <select
            id="page-size"
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className={cn(
              "h-8 px-2 pr-7",
              "rounded-[var(--radius-md)]",
              "border border-[var(--color-border)]",
              "bg-[var(--color-card)]",
              "text-sm text-[var(--color-foreground)]",
              "transition-colors duration-150",
              "hover:border-[var(--color-muted)]",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[var(--color-accent)]",
              "appearance-none cursor-pointer",
            )}
            style={{
              backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%238b949e'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E")`,
              backgroundRepeat: "no-repeat",
              backgroundPosition: "right 0.5rem center",
              backgroundSize: "1rem",
            }}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size}
              </option>
            ))}
          </select>
        </div>

        {/* Navigation buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page <= 1}
            aria-label="Previous page"
          >
            <ChevronLeftIcon className="h-4 w-4" />
          </Button>
          <span className="px-2 text-sm text-[var(--color-muted)] min-w-[80px] text-center">
            Page {page} of {totalPages || 1}
          </span>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page >= totalPages}
            aria-label="Next page"
          >
            <ChevronRightIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function DataTable<T>({
  columns,
  data,
  isLoading = false,
  page = 1,
  pageSize = 10,
  totalItems,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 25, 50, 100],
  sortBy,
  sortOrder = "asc",
  onSort,
  selectable = false,
  selectedIds = new Set(),
  onSelectionChange,
  getRowId = (row: T) => (row as { id?: string | number }).id ?? 0,
  onRowClick,
  emptyMessage = "No data available",
  showColumnToggle = false,
  className,
  striped = false,
  skeletonRows = 5,
}: DataTableProps<T>) {
  const tableId = useId();

  // Track manually hidden columns (via toggle dropdown)
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set());

  // Compute visible columns based on manual toggle and responsive priority
  const visibleColumns = useMemo(() => {
    const visible = new Set<string>();
    columns.forEach((col) => {
      const key = String(col.key);
      if (!hiddenColumns.has(key)) {
        visible.add(key);
      }
    });
    return visible;
  }, [columns, hiddenColumns]);

  // Filter columns for display
  const displayColumns = useMemo(() => {
    return columns.filter((col) => visibleColumns.has(String(col.key)));
  }, [columns, visibleColumns]);

  // Selection handlers
  const handleSelectAll = useCallback(
    (checked: boolean) => {
      if (!onSelectionChange) return;
      if (checked) {
        const allIds = new Set(data.map(getRowId));
        onSelectionChange(allIds);
      } else {
        onSelectionChange(new Set());
      }
    },
    [data, getRowId, onSelectionChange],
  );

  const handleSelectRow = useCallback(
    (row: T, checked: boolean) => {
      if (!onSelectionChange) return;
      const id = getRowId(row);
      const newSelection = new Set(selectedIds);
      if (checked) {
        newSelection.add(id);
      } else {
        newSelection.delete(id);
      }
      onSelectionChange(newSelection);
    },
    [getRowId, selectedIds, onSelectionChange],
  );

  // Sort handler
  const handleSort = useCallback(
    (columnKey: string) => {
      if (onSort) {
        onSort(columnKey);
      }
    },
    [onSort],
  );

  // Column toggle handler
  const handleToggleColumn = useCallback((key: string) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  // Row click handler
  const handleRowClick = useCallback(
    (row: T, index: number) => {
      if (onRowClick) {
        onRowClick(row, index);
      }
    },
    [onRowClick],
  );

  // Row keyboard handler
  const handleRowKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTableRowElement>, row: T, index: number) => {
      if (onRowClick && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        onRowClick(row, index);
      }
    },
    [onRowClick],
  );

  // Compute selection state
  const allSelected = data.length > 0 && data.every((row) => selectedIds.has(getRowId(row)));
  const someSelected = !allSelected && data.some((row) => selectedIds.has(getRowId(row)));

  // Get cell value by key (supports nested paths like "user.name")
  const getCellValue = useCallback((row: T, key: string): unknown => {
    const keys = key.split(".");
    let value: unknown = row;
    for (const k of keys) {
      if (value && typeof value === "object" && k in value) {
        value = (value as Record<string, unknown>)[k];
      } else {
        return undefined;
      }
    }
    return value;
  }, []);

  // Responsive column classes
  const getResponsiveClass = (priority?: number) => {
    switch (priority) {
      case 2:
        return "hidden lg:table-cell";
      case 3:
        return "hidden md:table-cell";
      default:
        return "";
    }
  };

  // Alignment classes
  const getAlignClass = (align?: "left" | "center" | "right") => {
    switch (align) {
      case "center":
        return "text-center";
      case "right":
        return "text-right";
      default:
        return "text-left";
    }
  };

  // Get sort direction for column
  const getSortDirection = (columnKey: string): SortDirection => {
    if (sortBy !== columnKey) return null;
    return sortOrder;
  };

  // Effective total items (for pagination)
  const effectiveTotalItems = totalItems ?? data.length;
  const showPagination = onPageChange && onPageSizeChange && effectiveTotalItems > 0;

  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)]",
        "border border-[var(--color-border)]",
        "overflow-hidden",
        className,
      )}
    >
      {/* Toolbar */}
      {(showColumnToggle || selectable) && (
        <div
          className={cn(
            "flex items-center justify-between gap-4",
            "px-4 py-2",
            "border-b border-[var(--color-border)]",
            "bg-[var(--color-card)]/50",
          )}
        >
          <div className="flex items-center gap-4">
            {selectable && selectedIds.size > 0 && (
              <span className="text-sm text-[var(--color-muted)]">
                <span className="font-medium text-[var(--color-foreground)]">
                  {selectedIds.size}
                </span>
                {" selected"}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {showColumnToggle && (
              <ColumnVisibilityDropdown
                columns={columns}
                visibleColumns={visibleColumns}
                onToggleColumn={handleToggleColumn}
              />
            )}
          </div>
        </div>
      )}

      {/* Live region for screen reader announcements */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        id={`${tableId}-status`}
      >
        {isLoading
          ? "Loading data..."
          : data.length === 0
            ? emptyMessage
            : `Showing ${data.length} rows. ${selectedIds.size > 0 ? `${selectedIds.size} rows selected.` : ""}`}
      </div>

      {/* Table */}
      <Table
        striped={striped}
        aria-labelledby={`${tableId}-caption`}
        aria-describedby={`${tableId}-status`}
      >
        <caption id={`${tableId}-caption`} className="sr-only">
          Data table with {displayColumns.length} columns{selectable ? ", with row selection" : ""}
        </caption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {/* Selection header */}
            {selectable && (
              <TableHead className="w-[52px]">
                <Checkbox
                  checked={allSelected}
                  indeterminate={someSelected}
                  onChange={handleSelectAll}
                  label="Select all rows"
                  disabled={isLoading || data.length === 0}
                />
              </TableHead>
            )}
            {/* Column headers */}
            {displayColumns.map((column) => {
              const key = String(column.key);
              const isSortable = column.sortable === true;
              const sortProps = isSortable
                ? {
                    sortable: true as const,
                    sortDirection: getSortDirection(key),
                    onSort: () => handleSort(key),
                  }
                : {};
              return (
                <TableHead
                  key={key}
                  {...sortProps}
                  className={cn(
                    getResponsiveClass(column.priority),
                    getAlignClass(column.align),
                    column.className,
                  )}
                  style={column.width ? { width: column.width } : undefined}
                >
                  {column.header}
                </TableHead>
              );
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {/* Loading state */}
          {isLoading && (
            <>
              {Array.from({ length: skeletonRows }).map((_, rowIndex) => (
                <TableRow key={`skeleton-${rowIndex}`} className="hover:bg-transparent">
                  {selectable && (
                    <TableCell>
                      <Skeleton variant="rectangular" width={16} height={16} />
                    </TableCell>
                  )}
                  {displayColumns.map((column, colIndex) => (
                    <TableCell
                      key={`skeleton-${rowIndex}-${colIndex}`}
                      className={cn(
                        getResponsiveClass(column.priority),
                        getAlignClass(column.align),
                      )}
                    >
                      <Skeleton variant="text" width={colIndex === 0 ? "80%" : "60%"} />
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </>
          )}

          {/* Empty state */}
          {!isLoading && data.length === 0 && (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={displayColumns.length + (selectable ? 1 : 0)}
                className="h-32 text-center"
              >
                <div className="flex flex-col items-center justify-center gap-2 text-[var(--color-muted)]">
                  <svg
                    className="h-10 w-10 opacity-50"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    aria-hidden="true"
                  >
                    <path d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
                  </svg>
                  <p className="text-sm">{emptyMessage}</p>
                </div>
              </TableCell>
            </TableRow>
          )}

          {/* Data rows */}
          {!isLoading &&
            data.map((row, rowIndex) => {
              const rowId = getRowId(row);
              const isSelected = selectedIds.has(rowId);

              return (
                <TableRow
                  key={rowId}
                  onClick={() => handleRowClick(row, rowIndex)}
                  onKeyDown={(e) => handleRowKeyDown(e, row, rowIndex)}
                  tabIndex={onRowClick ? 0 : undefined}
                  role={onRowClick ? "button" : undefined}
                  aria-selected={selectable ? isSelected : undefined}
                  className={cn(
                    isSelected && "bg-[var(--color-primary)]/10",
                    onRowClick && "cursor-pointer",
                  )}
                >
                  {/* Selection checkbox */}
                  {selectable && (
                    <TableCell onClick={(e) => e.stopPropagation()} className="w-[52px]">
                      <Checkbox
                        checked={isSelected}
                        onChange={(checked) => handleSelectRow(row, checked)}
                        label={`Select row ${rowIndex + 1}`}
                      />
                    </TableCell>
                  )}
                  {/* Data cells */}
                  {displayColumns.map((column) => {
                    const key = String(column.key);
                    const value = getCellValue(row, key);
                    const content = column.render
                      ? column.render(value, row, rowIndex)
                      : String(value ?? "");

                    return (
                      <TableCell
                        key={key}
                        className={cn(
                          getResponsiveClass(column.priority),
                          getAlignClass(column.align),
                          column.className,
                        )}
                      >
                        {content}
                      </TableCell>
                    );
                  })}
                </TableRow>
              );
            })}
        </TableBody>
      </Table>

      {/* Pagination */}
      {showPagination && (
        <Pagination
          page={page}
          pageSize={pageSize}
          totalItems={effectiveTotalItems}
          pageSizeOptions={pageSizeOptions}
          onPageChange={onPageChange}
          onPageSizeChange={onPageSizeChange}
        />
      )}
    </div>
  );
}

DataTable.displayName = "DataTable";

// ============================================================================
// Hook for managing DataTable state
// ============================================================================

export interface UseDataTableOptions<T> {
  initialPage?: number;
  initialPageSize?: number;
  initialSortBy?: string;
  initialSortOrder?: "asc" | "desc";
  getRowId?: (row: T) => string | number;
}

export interface UseDataTableReturn<T> {
  page: number;
  pageSize: number;
  sortBy: string | undefined;
  sortOrder: "asc" | "desc";
  selectedIds: Set<string | number>;
  setPage: (page: number) => void;
  setPageSize: (size: number) => void;
  handleSort: (column: string) => void;
  setSelectedIds: (ids: Set<string | number>) => void;
  clearSelection: () => void;
  selectAll: (rows: T[], getRowId?: (row: T) => string | number) => void;
}

export function useDataTable<T>({
  initialPage = 1,
  initialPageSize = 10,
  initialSortBy,
  initialSortOrder = "asc",
  getRowId = (row: T) => (row as { id?: string | number }).id ?? 0,
}: UseDataTableOptions<T> = {}): UseDataTableReturn<T> {
  const [page, setPage] = useState(initialPage);
  const [pageSize, setPageSize] = useState(initialPageSize);
  const [sortBy, setSortBy] = useState<string | undefined>(initialSortBy);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">(initialSortOrder);
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set());

  const handleSort = useCallback(
    (column: string) => {
      if (sortBy === column) {
        // Toggle order if same column
        setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
      } else {
        // New column, default to ascending
        setSortBy(column);
        setSortOrder("asc");
      }
    },
    [sortBy],
  );

  const handlePageSizeChange = useCallback((newSize: number) => {
    setPageSize(newSize);
    setPage(1); // Reset to first page when page size changes
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const selectAll = useCallback(
    (rows: T[], customGetRowId?: (row: T) => string | number) => {
      const getId = customGetRowId ?? getRowId;
      setSelectedIds(new Set(rows.map(getId)));
    },
    [getRowId],
  );

  return {
    page,
    pageSize,
    sortBy,
    sortOrder,
    selectedIds,
    setPage,
    setPageSize: handlePageSizeChange,
    handleSort,
    setSelectedIds,
    clearSelection,
    selectAll,
  };
}
