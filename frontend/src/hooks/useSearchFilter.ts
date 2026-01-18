'use client';

import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { useRouter, useSearchParams, usePathname } from 'next/navigation';
import { debounce } from '@/lib/utils';

// ============================================================================
// Types
// ============================================================================

/**
 * Filter operators for different column types.
 */
export type FilterOperator =
  | 'equals'
  | 'contains'
  | 'startsWith'
  | 'endsWith'
  | 'gt'
  | 'gte'
  | 'lt'
  | 'lte'
  | 'between'
  | 'in'
  | 'isNull'
  | 'isNotNull';

/**
 * Column type for filtering.
 */
export type FilterableColumnType =
  | 'string'
  | 'number'
  | 'date'
  | 'datetime'
  | 'enum'
  | 'boolean';

/**
 * Definition of a column that can be filtered.
 */
export interface FilterableColumn {
  key: string;
  label: string;
  type: FilterableColumnType;
  enumValues?: string[];
}

/**
 * A single column filter configuration.
 */
export interface ColumnFilter {
  column: string;
  operator: FilterOperator;
  value: string | string[] | DateRangeValue;
}

/**
 * Date range value for between operator.
 */
export interface DateRangeValue {
  from: string | undefined;
  to: string | undefined;
}

/**
 * Complete filter state including search and column filters.
 */
export interface FilterState {
  search: string;
  filters: ColumnFilter[];
}

/**
 * Options for the useSearchFilter hook.
 */
export interface UseSearchFilterOptions {
  /** Debounce delay for search input in milliseconds */
  debounceMs?: number;
  /** Whether to sync filters to URL query params */
  syncToUrl?: boolean;
  /** Initial filter state */
  initialState?: Partial<FilterState> | undefined;
  /** Callback when filters change */
  onFilterChange?: (state: FilterState) => void;
}

/**
 * Return type for the useSearchFilter hook.
 */
export interface UseSearchFilterReturn {
  /** Current filter state */
  filterState: FilterState;
  /** Current search value (may be different from filterState.search during typing) */
  searchValue: string;
  /** Set the search value (will be debounced) */
  setSearch: (value: string) => void;
  /** Add a new column filter */
  addFilter: (filter: ColumnFilter) => void;
  /** Remove a filter by column key */
  removeFilter: (column: string) => void;
  /** Update an existing filter */
  updateFilter: (column: string, filter: Partial<ColumnFilter>) => void;
  /** Clear all filters including search */
  clearAll: () => void;
  /** Clear only column filters, keep search */
  clearFilters: () => void;
  /** Whether any filters are active */
  hasActiveFilters: boolean;
  /** Count of active column filters */
  activeFilterCount: number;
  /** Get filter for a specific column */
  getFilter: (column: string) => ColumnFilter | undefined;
  /** Check if a filter exists for a column */
  hasFilter: (column: string) => boolean;
}

// ============================================================================
// Operator Helpers
// ============================================================================

/**
 * Get available operators for a column type.
 */
export function getOperatorsForType(type: FilterableColumnType): FilterOperator[] {
  switch (type) {
    case 'string':
      return ['equals', 'contains', 'startsWith', 'endsWith', 'isNull', 'isNotNull'];
    case 'number':
      return ['equals', 'gt', 'gte', 'lt', 'lte', 'between', 'isNull', 'isNotNull'];
    case 'date':
    case 'datetime':
      return ['equals', 'gt', 'gte', 'lt', 'lte', 'between', 'isNull', 'isNotNull'];
    case 'enum':
      return ['equals', 'in', 'isNull', 'isNotNull'];
    case 'boolean':
      return ['equals', 'isNull', 'isNotNull'];
    default:
      return ['equals'];
  }
}

/**
 * Get human-readable label for an operator.
 */
export function getOperatorLabel(operator: FilterOperator): string {
  const labels: Record<FilterOperator, string> = {
    equals: 'Equals',
    contains: 'Contains',
    startsWith: 'Starts with',
    endsWith: 'Ends with',
    gt: 'Greater than',
    gte: 'Greater than or equal',
    lt: 'Less than',
    lte: 'Less than or equal',
    between: 'Between',
    in: 'Is one of',
    isNull: 'Is empty',
    isNotNull: 'Is not empty',
  };
  return labels[operator];
}

/**
 * Get the default operator for a column type.
 */
export function getDefaultOperator(type: FilterableColumnType): FilterOperator {
  switch (type) {
    case 'string':
      return 'contains';
    case 'enum':
      return 'in';
    case 'date':
    case 'datetime':
      return 'equals';
    default:
      return 'equals';
  }
}

/**
 * Check if an operator requires a value input.
 */
export function operatorRequiresValue(operator: FilterOperator): boolean {
  return operator !== 'isNull' && operator !== 'isNotNull';
}

// ============================================================================
// URL Serialization
// ============================================================================

/**
 * Serialize filter state to URL query params.
 * Format: ?search=query&filter[email][contains]=john&filter[created_at][between]=2024-01-01,2024-12-31
 */
export function serializeFiltersToUrl(state: FilterState): URLSearchParams {
  const params = new URLSearchParams();

  if (state.search) {
    params.set('search', state.search);
  }

  for (const filter of state.filters) {
    const key = `filter[${filter.column}][${filter.operator}]`;

    if (Array.isArray(filter.value)) {
      params.set(key, filter.value.join(','));
    } else if (typeof filter.value === 'object' && filter.value !== null) {
      const rangeValue = filter.value as DateRangeValue;
      const parts: string[] = [];
      if (rangeValue.from) parts.push(rangeValue.from);
      if (rangeValue.to) parts.push(rangeValue.to);
      params.set(key, parts.join(','));
    } else {
      params.set(key, String(filter.value));
    }
  }

  return params;
}

/**
 * Parse URL query params to filter state.
 */
export function parseFiltersFromUrl(searchParams: URLSearchParams): FilterState {
  const state: FilterState = {
    search: searchParams.get('search') || '',
    filters: [],
  };

  // Parse filter params using regex pattern: filter[column][operator]
  const filterPattern = /^filter\[([^\]]+)\]\[([^\]]+)\]$/;

  searchParams.forEach((value, key) => {
    const match = key.match(filterPattern);
    if (match) {
      const columnMatch = match[1];
      const operatorMatch = match[2];

      // Guard against undefined matches
      if (!columnMatch || !operatorMatch) return;

      const validOperator = operatorMatch as FilterOperator;

      // Determine value type based on operator
      let parsedValue: string | string[] | DateRangeValue = value;

      if (validOperator === 'in') {
        parsedValue = value.split(',').filter(Boolean);
      } else if (validOperator === 'between') {
        const parts = value.split(',');
        const fromValue = parts[0];
        const toValue = parts[1];
        const rangeValue: DateRangeValue = {
          from: fromValue && fromValue.length > 0 ? fromValue : undefined,
          to: toValue && toValue.length > 0 ? toValue : undefined,
        };
        parsedValue = rangeValue;
      }

      state.filters.push({
        column: columnMatch,
        operator: validOperator,
        value: parsedValue,
      });
    }
  });

  return state;
}

/**
 * Validate a filter value against its column type.
 */
export function validateFilterValue(
  value: string | string[] | DateRangeValue,
  type: FilterableColumnType,
  operator: FilterOperator
): boolean {
  // No validation needed for null operators
  if (!operatorRequiresValue(operator)) {
    return true;
  }

  // Check for empty values
  if (Array.isArray(value)) {
    return value.length > 0;
  }

  if (typeof value === 'object' && value !== null) {
    const rangeValue = value as DateRangeValue;
    return Boolean(rangeValue.from || rangeValue.to);
  }

  if (typeof value === 'string') {
    if (!value.trim()) return false;

    // Type-specific validation
    if (type === 'number') {
      return !isNaN(Number(value));
    }

    if (type === 'date' || type === 'datetime') {
      const date = new Date(value);
      return !isNaN(date.getTime());
    }

    if (type === 'boolean') {
      return value === 'true' || value === 'false';
    }
  }

  return true;
}

// ============================================================================
// Hook Implementation
// ============================================================================

const DEFAULT_STATE: FilterState = {
  search: '',
  filters: [],
};

/**
 * Hook for managing search and filter state with URL synchronization.
 *
 * @example
 * ```tsx
 * const {
 *   filterState,
 *   searchValue,
 *   setSearch,
 *   addFilter,
 *   clearAll,
 *   hasActiveFilters
 * } = useSearchFilter({
 *   debounceMs: 300,
 *   syncToUrl: true,
 *   onFilterChange: (state) => refetch({ filters: state })
 * });
 * ```
 */
export function useSearchFilter(
  options: UseSearchFilterOptions = {}
): UseSearchFilterReturn {
  const {
    debounceMs = 300,
    syncToUrl = true,
    initialState,
    onFilterChange,
  } = options;

  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Track if we've initialized from URL
  const initializedRef = useRef(false);

  // Parse initial state from URL or use provided initial state
  const getInitialState = useCallback((): FilterState => {
    if (syncToUrl && searchParams) {
      const parsed = parseFiltersFromUrl(searchParams);
      // Only use parsed state if it has any values
      if (parsed.search || parsed.filters.length > 0) {
        return parsed;
      }
    }
    return {
      search: initialState?.search ?? DEFAULT_STATE.search,
      filters: initialState?.filters ?? DEFAULT_STATE.filters,
    };
  }, [syncToUrl, searchParams, initialState]);

  // Main filter state
  const [filterState, setFilterState] = useState<FilterState>(getInitialState);

  // Separate state for search input (to allow immediate display while debouncing)
  const [searchValue, setSearchValue] = useState(filterState.search);

  // Initialize from URL on mount
  useEffect(() => {
    if (!initializedRef.current) {
      const state = getInitialState();
      setFilterState(state);
      setSearchValue(state.search);
      initializedRef.current = true;
    }
  }, [getInitialState]);

  // Debounced search update
  const debouncedSearchUpdate = useMemo(
    () =>
      debounce((value: string) => {
        setFilterState((prev) => ({
          ...prev,
          search: value,
        }));
      }, debounceMs),
    [debounceMs]
  );

  // Sync filter state to URL
  useEffect(() => {
    if (!syncToUrl || !initializedRef.current) return;

    const newParams = serializeFiltersToUrl(filterState);
    const newUrl = `${pathname}${newParams.toString() ? `?${newParams.toString()}` : ''}`;

    // Only update if URL actually changed
    const currentUrl = `${pathname}${searchParams?.toString() ? `?${searchParams.toString()}` : ''}`;
    if (newUrl !== currentUrl) {
      router.replace(newUrl, { scroll: false });
    }
  }, [filterState, pathname, router, syncToUrl, searchParams]);

  // Notify parent of changes
  useEffect(() => {
    if (onFilterChange && initializedRef.current) {
      onFilterChange(filterState);
    }
  }, [filterState, onFilterChange]);

  // Set search value (with debounce)
  const setSearch = useCallback(
    (value: string) => {
      setSearchValue(value);
      debouncedSearchUpdate(value);
    },
    [debouncedSearchUpdate]
  );

  // Add a new filter
  const addFilter = useCallback((filter: ColumnFilter) => {
    setFilterState((prev) => {
      // Remove existing filter for the same column
      const existingFilters = prev.filters.filter((f) => f.column !== filter.column);
      return {
        ...prev,
        filters: [...existingFilters, filter],
      };
    });
  }, []);

  // Remove a filter by column
  const removeFilter = useCallback((column: string) => {
    setFilterState((prev) => ({
      ...prev,
      filters: prev.filters.filter((f) => f.column !== column),
    }));
  }, []);

  // Update an existing filter
  const updateFilter = useCallback(
    (column: string, updates: Partial<ColumnFilter>) => {
      setFilterState((prev) => ({
        ...prev,
        filters: prev.filters.map((f) =>
          f.column === column ? { ...f, ...updates } : f
        ),
      }));
    },
    []
  );

  // Clear all filters and search
  const clearAll = useCallback(() => {
    setFilterState(DEFAULT_STATE);
    setSearchValue('');
  }, []);

  // Clear only column filters
  const clearFilters = useCallback(() => {
    setFilterState((prev) => ({
      ...prev,
      filters: [],
    }));
  }, []);

  // Get filter for a specific column
  const getFilter = useCallback(
    (column: string) => filterState.filters.find((f) => f.column === column),
    [filterState.filters]
  );

  // Check if filter exists for column
  const hasFilter = useCallback(
    (column: string) => filterState.filters.some((f) => f.column === column),
    [filterState.filters]
  );

  // Computed values
  const hasActiveFilters =
    filterState.search.length > 0 || filterState.filters.length > 0;
  const activeFilterCount = filterState.filters.length;

  return {
    filterState,
    searchValue,
    setSearch,
    addFilter,
    removeFilter,
    updateFilter,
    clearAll,
    clearFilters,
    hasActiveFilters,
    activeFilterCount,
    getFilter,
    hasFilter,
  };
}

export default useSearchFilter;
