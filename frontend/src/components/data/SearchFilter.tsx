"use client";

import {
  useState,
  useCallback,
  useId,
  useMemo,
  useRef,
  useEffect,
  type KeyboardEvent,
} from "react";
import { cn } from "@/lib/utils";
import { Input, Select, type SelectOption } from "@/components/ui/Form";
import { Button } from "@/components/ui/Button";
import {
  useSearchFilter,
  getOperatorsForType,
  getOperatorLabel,
  getDefaultOperator,
  operatorRequiresValue,
  type FilterableColumn,
  type FilterState,
  type ColumnFilter,
  type FilterOperator,
  type DateRangeValue,
  type UseSearchFilterOptions,
} from "@/hooks/useSearchFilter";

// ============================================================================
// Types
// ============================================================================

export interface SearchFilterProps {
  /** Columns available for filtering */
  columns: FilterableColumn[];
  /** Callback when filter state changes */
  onFilterChange: (filters: FilterState) => void;
  /** Initial filter state */
  initialFilters?: FilterState;
  /** Additional CSS classes */
  className?: string;
  /** Placeholder text for search input */
  searchPlaceholder?: string;
  /** Whether to show the add filter button */
  showAddFilter?: boolean;
  /** Debounce delay for search in milliseconds */
  debounceMs?: number;
  /** Whether to sync filters to URL */
  syncToUrl?: boolean;
}

// Re-export types for convenience
export type { FilterableColumn, FilterState, ColumnFilter, FilterOperator, DateRangeValue };

// ============================================================================
// Icons
// ============================================================================

function SearchIcon({ className }: { className?: string }) {
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
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.35-4.35" />
    </svg>
  );
}

function FilterIcon({ className }: { className?: string }) {
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
      <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
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
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
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
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

function CalendarIcon({ className }: { className?: string }) {
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
      <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
      <line x1="16" y1="2" x2="16" y2="6" />
      <line x1="8" y1="2" x2="8" y2="6" />
      <line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}

// ============================================================================
// Subcomponents
// ============================================================================

interface FilterBadgeProps {
  filter: ColumnFilter;
  column: FilterableColumn;
  onRemove: () => void;
}

function FilterBadge({ filter, column, onRemove }: FilterBadgeProps) {
  const displayValue = useMemo(() => {
    if (!operatorRequiresValue(filter.operator)) {
      return null;
    }

    if (Array.isArray(filter.value)) {
      return filter.value.length > 2
        ? `${filter.value.slice(0, 2).join(", ")} +${filter.value.length - 2}`
        : filter.value.join(", ");
    }

    if (typeof filter.value === "object" && filter.value !== null) {
      const range = filter.value as DateRangeValue;
      if (range.from && range.to) {
        return `${range.from} to ${range.to}`;
      }
      return range.from || range.to || "";
    }

    return String(filter.value);
  }, [filter.value, filter.operator]);

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5",
        "h-7 px-2 pr-1",
        "rounded-[var(--radius-md)]",
        "bg-[var(--color-primary)]/10",
        "border border-[var(--color-primary)]/20",
        "text-sm text-[var(--color-foreground)]",
      )}
    >
      <span className="font-medium text-[var(--color-primary)]">{column.label}</span>
      <span className="text-[var(--color-muted)]">
        {getOperatorLabel(filter.operator).toLowerCase()}
      </span>
      {displayValue && <span className="max-w-[150px] truncate">{displayValue}</span>}
      <button
        type="button"
        onClick={onRemove}
        className={cn(
          "ml-0.5 p-0.5 rounded-[var(--radius-sm)]",
          "hover:bg-[var(--color-primary)]/20",
          "transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2",
          "focus-visible:ring-[var(--color-accent)]",
        )}
        aria-label={`Remove ${column.label} filter`}
      >
        <XIcon className="h-3 w-3" />
      </button>
    </div>
  );
}

interface DateRangeInputProps {
  value: DateRangeValue;
  onChange: (value: DateRangeValue) => void;
  type: "date" | "datetime";
}

function DateRangeInput({ value, onChange, type }: DateRangeInputProps) {
  const inputType = type === "datetime" ? "datetime-local" : "date";

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1">
        <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted)]" />
        <Input
          type={inputType}
          value={value.from || ""}
          onChange={(e) => onChange({ ...value, from: e.target.value })}
          placeholder="From"
          className="pl-9 text-sm"
        />
      </div>
      <span className="text-[var(--color-muted)]">to</span>
      <div className="relative flex-1">
        <CalendarIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted)]" />
        <Input
          type={inputType}
          value={value.to || ""}
          onChange={(e) => onChange({ ...value, to: e.target.value })}
          placeholder="To"
          className="pl-9 text-sm"
        />
      </div>
    </div>
  );
}

interface MultiSelectProps {
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
  placeholder?: string;
}

function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Select values...",
}: MultiSelectProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleOption = (option: string) => {
    if (selected.includes(option)) {
      onChange(selected.filter((s) => s !== option));
    } else {
      onChange([...selected, option]);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  };

  const displayText =
    selected.length === 0
      ? placeholder
      : selected.length === 1
        ? selected[0]
        : `${selected.length} selected`;

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-controls={dropdownId}
        aria-haspopup="listbox"
        className={cn(
          "w-full h-10 px-3",
          "flex items-center justify-between gap-2",
          "rounded-[var(--radius-md)]",
          "bg-[var(--color-card)] text-[var(--color-foreground)]",
          "border border-[var(--color-border)]",
          "text-sm text-left",
          "transition-colors duration-150",
          "hover:border-[var(--color-muted)]",
          "focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]",
          "focus:outline-none",
          selected.length === 0 && "text-[var(--color-muted)]",
        )}
      >
        <span className="truncate">{displayText}</span>
        <ChevronDownIcon
          className={cn("h-4 w-4 shrink-0 transition-transform", isOpen && "rotate-180")}
        />
      </button>

      {isOpen && (
        <div
          id={dropdownId}
          role="listbox"
          aria-multiselectable="true"
          className={cn(
            "absolute z-50 w-full mt-1",
            "max-h-[200px] overflow-auto",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "py-1",
          )}
        >
          {options.map((option) => {
            const isSelected = selected.includes(option);
            return (
              <button
                key={option}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => toggleOption(option)}
                className={cn(
                  "w-full px-3 py-2",
                  "flex items-center gap-2",
                  "text-sm text-left",
                  "transition-colors duration-150",
                  "hover:bg-[var(--color-card-hover)]",
                  "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
                )}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 items-center justify-center shrink-0",
                    "rounded-[var(--radius-sm)]",
                    "border border-[var(--color-border)]",
                    "transition-colors duration-150",
                    isSelected && "bg-[var(--color-primary)] border-[var(--color-primary)]",
                  )}
                >
                  {isSelected && (
                    <svg
                      className="h-3 w-3 text-white"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="3"
                      aria-hidden="true"
                    >
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  )}
                </span>
                <span>{option}</span>
              </button>
            );
          })}
          {options.length === 0 && (
            <div className="px-3 py-2 text-sm text-[var(--color-muted)]">No options available</div>
          )}
        </div>
      )}
    </div>
  );
}

interface FilterEditorProps {
  columns: FilterableColumn[];
  filter: Partial<ColumnFilter>;
  onChange: (filter: ColumnFilter) => void;
  onCancel: () => void;
  existingFilters: string[];
}

function FilterEditor({ columns, filter, onChange, onCancel, existingFilters }: FilterEditorProps) {
  const [selectedColumn, setSelectedColumn] = useState<string>(filter.column || "");
  const [selectedOperator, setSelectedOperator] = useState<FilterOperator>(
    filter.operator || "equals",
  );
  const [value, setValue] = useState<string | string[] | DateRangeValue>(filter.value || "");

  // Get available columns (exclude already filtered columns)
  const availableColumns = useMemo(
    () => columns.filter((col) => !existingFilters.includes(col.key) || col.key === filter.column),
    [columns, existingFilters, filter.column],
  );

  // Get selected column definition
  const column = useMemo(
    () => columns.find((c) => c.key === selectedColumn),
    [columns, selectedColumn],
  );

  // Get operators for selected column type
  const operators = useMemo(() => (column ? getOperatorsForType(column.type) : []), [column]);

  // Reset operator and value when column changes
  const handleColumnChange = (key: string) => {
    setSelectedColumn(key);
    const newColumn = columns.find((c) => c.key === key);
    if (newColumn) {
      const defaultOp = getDefaultOperator(newColumn.type);
      setSelectedOperator(defaultOp);
      // Reset value based on type
      if (newColumn.type === "enum") {
        setValue([]);
      } else if (newColumn.type === "date" || newColumn.type === "datetime") {
        const emptyRange: DateRangeValue = { from: undefined, to: undefined };
        setValue(emptyRange);
      } else {
        setValue("");
      }
    }
  };

  // Handle operator change
  const handleOperatorChange = (op: FilterOperator) => {
    setSelectedOperator(op);
    // Reset value for between operator
    if (op === "between" && column) {
      const emptyRange: DateRangeValue = { from: undefined, to: undefined };
      setValue(emptyRange);
    } else if (op === "in" && column?.type === "enum") {
      setValue([]);
    } else if (
      (op === "isNull" || op === "isNotNull") &&
      (Array.isArray(value) || typeof value === "object")
    ) {
      setValue("");
    }
  };

  // Apply filter
  const handleApply = () => {
    if (!selectedColumn || !selectedOperator) return;

    onChange({
      column: selectedColumn,
      operator: selectedOperator,
      value,
    });
  };

  // Check if filter is valid
  const isValid = useMemo(() => {
    if (!selectedColumn || !selectedOperator) return false;
    if (!operatorRequiresValue(selectedOperator)) return true;

    if (Array.isArray(value)) {
      return value.length > 0;
    }
    if (typeof value === "object" && value !== null) {
      const range = value as DateRangeValue;
      return Boolean(range.from || range.to);
    }
    return Boolean(value);
  }, [selectedColumn, selectedOperator, value]);

  // Render value input based on column type and operator
  const renderValueInput = () => {
    if (!column || !operatorRequiresValue(selectedOperator)) {
      return null;
    }

    if (column.type === "enum" && selectedOperator === "in") {
      return (
        <MultiSelect
          options={column.enumValues || []}
          selected={Array.isArray(value) ? value : []}
          onChange={(selected) => setValue(selected)}
          placeholder="Select values..."
        />
      );
    }

    if ((column.type === "date" || column.type === "datetime") && selectedOperator === "between") {
      const rangeValue: DateRangeValue =
        typeof value === "object" && !Array.isArray(value)
          ? (value as DateRangeValue)
          : { from: undefined, to: undefined };
      return (
        <DateRangeInput
          value={rangeValue}
          onChange={(newValue) => setValue(newValue)}
          type={column.type as "date" | "datetime"}
        />
      );
    }

    if (column.type === "date" || column.type === "datetime") {
      const inputType = column.type === "datetime" ? "datetime-local" : "date";
      return (
        <Input
          type={inputType}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => setValue(e.target.value)}
          className="text-sm"
        />
      );
    }

    if (column.type === "number") {
      return (
        <Input
          type="number"
          value={typeof value === "string" ? value : ""}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Enter value..."
          className="text-sm"
        />
      );
    }

    if (column.type === "boolean") {
      return (
        <Select
          options={[
            { value: "true", label: "True" },
            { value: "false", label: "False" },
          ]}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Select..."
        />
      );
    }

    if (column.type === "enum" && selectedOperator === "equals") {
      return (
        <Select
          options={(column.enumValues || []).map((v) => ({ value: v, label: v }))}
          value={typeof value === "string" ? value : ""}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Select value..."
        />
      );
    }

    // Default: text input
    return (
      <Input
        type="text"
        value={typeof value === "string" ? value : ""}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Enter value..."
        className="text-sm"
      />
    );
  };

  const columnOptions: SelectOption[] = availableColumns.map((col) => ({
    value: col.key,
    label: col.label,
  }));

  const operatorOptions: SelectOption[] = operators.map((op) => ({
    value: op,
    label: getOperatorLabel(op),
  }));

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <Select
          options={columnOptions}
          value={selectedColumn}
          onChange={(e) => handleColumnChange(e.target.value)}
          placeholder="Select column..."
        />
        <Select
          options={operatorOptions}
          value={selectedOperator}
          onChange={(e) => handleOperatorChange(e.target.value as FilterOperator)}
          placeholder="Select operator..."
          disabled={!selectedColumn}
        />
      </div>

      {column && operatorRequiresValue(selectedOperator) && <div>{renderValueInput()}</div>}

      <div className="flex items-center justify-end gap-2">
        <Button variant="ghost" size="sm" onClick={onCancel}>
          Cancel
        </Button>
        <Button size="sm" onClick={handleApply} disabled={!isValid}>
          Apply
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Search and filter component for DataTable.
 *
 * Features:
 * - Global text search with debounce
 * - Column-specific filters with operators
 * - Date range picker for date/datetime columns
 * - Multi-select for enum columns
 * - URL state persistence
 * - Clear all filters button
 *
 * @example
 * ```tsx
 * <SearchFilter
 *   columns={[
 *     { key: 'email', label: 'Email', type: 'string' },
 *     { key: 'created_at', label: 'Created', type: 'datetime' },
 *     { key: 'status', label: 'Status', type: 'enum', enumValues: ['active', 'inactive'] },
 *   ]}
 *   onFilterChange={(filters) => refetch({ filters })}
 *   syncToUrl={true}
 * />
 * ```
 */
export function SearchFilter({
  columns,
  onFilterChange,
  initialFilters,
  className,
  searchPlaceholder = "Search...",
  showAddFilter = true,
  debounceMs = 300,
  syncToUrl = true,
}: SearchFilterProps) {
  const searchInputId = useId();
  const filterPanelId = useId();

  // Filter panel state
  const [showFilterPanel, setShowFilterPanel] = useState(false);
  const filterPanelRef = useRef<HTMLDivElement>(null);

  // Use the search filter hook
  const hookOptions = useMemo(
    (): UseSearchFilterOptions => ({
      debounceMs,
      syncToUrl,
      initialState: initialFilters ?? undefined,
      onFilterChange,
    }),
    [debounceMs, syncToUrl, initialFilters, onFilterChange],
  );

  const {
    filterState,
    searchValue,
    setSearch,
    addFilter,
    removeFilter,
    clearAll,
    hasActiveFilters,
    activeFilterCount,
  } = useSearchFilter(hookOptions);

  // Close filter panel on outside click
  useEffect(() => {
    if (!showFilterPanel) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (filterPanelRef.current && !filterPanelRef.current.contains(event.target as Node)) {
        setShowFilterPanel(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showFilterPanel]);

  // Handle keyboard navigation
  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Escape") {
      setSearch("");
    }
  };

  // Handle filter apply
  const handleApplyFilter = useCallback(
    (filter: ColumnFilter) => {
      addFilter(filter);
      setShowFilterPanel(false);
    },
    [addFilter],
  );

  // Get column definition for filter badge
  const getColumn = (key: string) => columns.find((c) => c.key === key);

  // Existing filter columns
  const existingFilterColumns = filterState.filters.map((f) => f.column);

  return (
    <div className={cn("space-y-3", className)}>
      {/* Search and filter controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Search input */}
        <div className="relative flex-1">
          <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted)]" />
          <Input
            id={searchInputId}
            type="search"
            value={searchValue}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={searchPlaceholder}
            className="pl-9 pr-9"
            aria-label="Search"
          />
          {searchValue && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className={cn(
                "absolute right-3 top-1/2 -translate-y-1/2",
                "p-0.5 rounded-[var(--radius-sm)]",
                "text-[var(--color-muted)]",
                "hover:text-[var(--color-foreground)]",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
                "focus-visible:outline-none focus-visible:ring-2",
                "focus-visible:ring-[var(--color-accent)]",
              )}
              aria-label="Clear search"
            >
              <XIcon className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Filter controls */}
        <div className="flex items-center gap-2">
          {showAddFilter && columns.length > 0 && (
            <div className="relative" ref={filterPanelRef}>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setShowFilterPanel(!showFilterPanel)}
                aria-expanded={showFilterPanel}
                aria-controls={filterPanelId}
              >
                <FilterIcon className="h-4 w-4" />
                <span className="hidden sm:inline">Filter</span>
                {activeFilterCount > 0 && (
                  <span
                    className={cn(
                      "flex items-center justify-center",
                      "h-5 min-w-[20px] px-1.5",
                      "rounded-full",
                      "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
                      "text-xs font-medium",
                    )}
                  >
                    {activeFilterCount}
                  </span>
                )}
              </Button>

              {/* Filter panel dropdown */}
              {showFilterPanel && (
                <div
                  id={filterPanelId}
                  className={cn(
                    "absolute right-0 top-full z-50 mt-2",
                    "w-[360px] p-4",
                    "rounded-[var(--radius-lg)]",
                    "border border-[var(--color-border)]",
                    "bg-[var(--color-card)]",
                    "shadow-lg shadow-black/20",
                  )}
                >
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-[var(--color-foreground)]">
                      Add Filter
                    </h3>
                    <button
                      type="button"
                      onClick={() => setShowFilterPanel(false)}
                      className={cn(
                        "p-1 rounded-[var(--radius-sm)]",
                        "text-[var(--color-muted)]",
                        "hover:text-[var(--color-foreground)]",
                        "hover:bg-[var(--color-card-hover)]",
                        "transition-colors duration-150",
                      )}
                      aria-label="Close filter panel"
                    >
                      <XIcon className="h-4 w-4" />
                    </button>
                  </div>

                  <FilterEditor
                    columns={columns}
                    filter={{}}
                    onChange={handleApplyFilter}
                    onCancel={() => setShowFilterPanel(false)}
                    existingFilters={existingFilterColumns}
                  />
                </div>
              )}
            </div>
          )}

          {/* Clear all button */}
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={clearAll}>
              <XIcon className="h-4 w-4" />
              <span className="hidden sm:inline">Clear all</span>
            </Button>
          )}
        </div>
      </div>

      {/* Active filter badges */}
      {filterState.filters.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs text-[var(--color-muted)] uppercase tracking-wide">
            Filters:
          </span>
          {filterState.filters.map((filter) => {
            const column = getColumn(filter.column);
            if (!column) return null;
            return (
              <FilterBadge
                key={filter.column}
                filter={filter}
                column={column}
                onRemove={() => removeFilter(filter.column)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

SearchFilter.displayName = "SearchFilter";

export default SearchFilter;
