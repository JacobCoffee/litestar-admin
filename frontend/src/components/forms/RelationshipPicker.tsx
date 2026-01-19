"use client";

import {
  useState,
  useRef,
  useEffect,
  useCallback,
  useId,
  type KeyboardEvent,
  type ChangeEvent,
} from "react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { Spinner } from "@/components/ui/Loading";
import type { RelationshipOption, RelationshipSearchResponse } from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface RelationshipPickerProps {
  /** The source model name */
  modelName: string;
  /** The relationship field name */
  fieldName: string;
  /** Current selected value (primary key of related record) */
  value: string | number | null;
  /** Callback when value changes */
  onChange: (value: string | number | null) => void;
  /** Placeholder text for the input */
  placeholder?: string;
  /** Whether the picker is disabled */
  disabled?: boolean;
  /** Minimum characters before search triggers */
  minChars?: number;
  /** Debounce delay in milliseconds */
  debounceMs?: number;
  /** Maximum number of results to show */
  maxResults?: number;
  /** Whether the field has an error */
  error?: boolean;
  /** Additional CSS classes */
  className?: string;
}

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

// ============================================================================
// Hook: useRelationshipSearch
// ============================================================================

function useRelationshipSearch(
  modelName: string,
  fieldName: string,
  searchTerm: string,
  enabled: boolean,
  limit: number,
) {
  return useQuery<RelationshipSearchResponse>({
    queryKey: ["relationship-search", modelName, fieldName, searchTerm, limit],
    queryFn: () =>
      api.searchRelationship(modelName, fieldName, {
        q: searchTerm,
        limit,
      }),
    enabled: enabled && !!modelName && !!fieldName,
    staleTime: 30 * 1000, // Cache results for 30 seconds
    gcTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
  });
}

function useRelationshipOptions(
  modelName: string,
  fieldName: string,
  ids: (string | number)[],
  enabled: boolean,
) {
  return useQuery<RelationshipSearchResponse>({
    queryKey: ["relationship-options", modelName, fieldName, ids],
    queryFn: () => api.getRelationshipOptions(modelName, fieldName, ids),
    enabled: enabled && ids.length > 0 && !!modelName && !!fieldName,
    staleTime: 5 * 60 * 1000, // Options are more stable
    gcTime: 10 * 60 * 1000,
  });
}

// ============================================================================
// Debounce Hook
// ============================================================================

function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(timer);
    };
  }, [value, delay]);

  return debouncedValue;
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Select2-style autocomplete component for relationship/FK fields.
 *
 * Features:
 * - Debounced search with configurable delay
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Loading state indicator
 * - Error state display
 * - Clear button
 * - Dark theme dropdown styling
 *
 * @example
 * ```tsx
 * <RelationshipPicker
 *   modelName="Post"
 *   fieldName="author_id"
 *   value={authorId}
 *   onChange={(id) => setAuthorId(id)}
 *   placeholder="Select an author..."
 * />
 * ```
 */
export function RelationshipPicker({
  modelName,
  fieldName,
  value,
  onChange,
  placeholder = "Search...",
  disabled = false,
  minChars = 1,
  debounceMs = 300,
  maxResults = 20,
  error = false,
  className,
}: RelationshipPickerProps) {
  const inputId = useId();
  const listboxId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Local state
  const [isOpen, setIsOpen] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const [selectedOption, setSelectedOption] = useState<RelationshipOption | null>(null);

  // Debounced search term
  const debouncedSearch = useDebounce(inputValue, debounceMs);
  const shouldSearch = debouncedSearch.length >= minChars;

  // Fetch search results
  const {
    data: searchData,
    isLoading: isSearching,
    isError: searchError,
  } = useRelationshipSearch(modelName, fieldName, debouncedSearch, shouldSearch && isOpen, maxResults);

  // Fetch initial value if we have one but no selected option
  const {
    data: initialData,
  } = useRelationshipOptions(
    modelName,
    fieldName,
    value !== null ? [value] : [],
    value !== null && selectedOption === null,
  );

  // Set initial selected option when data loads
  useEffect(() => {
    if (initialData?.items && initialData.items.length > 0 && selectedOption === null && value !== null) {
      const option = initialData.items.find((item) => String(item.id) === String(value));
      if (option) {
        setSelectedOption(option);
      }
    }
  }, [initialData, selectedOption, value]);

  // Clear selected option when value becomes null externally
  useEffect(() => {
    if (value === null) {
      setSelectedOption(null);
    }
  }, [value]);

  // Get options to display
  const options = searchData?.items ?? [];

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setInputValue("");
        setHighlightedIndex(-1);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  // Reset highlight when options change
  useEffect(() => {
    setHighlightedIndex(-1);
  }, [options]);

  // Handle input change
  const handleInputChange = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setIsOpen(true);
    setHighlightedIndex(-1);
  }, []);

  // Handle option selection
  const handleSelect = useCallback(
    (option: RelationshipOption) => {
      setSelectedOption(option);
      onChange(option.id);
      setIsOpen(false);
      setInputValue("");
      setHighlightedIndex(-1);
    },
    [onChange],
  );

  // Handle clear
  const handleClear = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      setSelectedOption(null);
      onChange(null);
      setInputValue("");
      inputRef.current?.focus();
    },
    [onChange],
  );

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (!isOpen) {
        if (e.key === "ArrowDown" || e.key === "Enter") {
          setIsOpen(true);
          return;
        }
        return;
      }

      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev < options.length - 1 ? prev + 1 : prev));
          break;
        case "ArrowUp":
          e.preventDefault();
          setHighlightedIndex((prev) => (prev > 0 ? prev - 1 : prev));
          break;
        case "Enter":
          e.preventDefault();
          if (highlightedIndex >= 0 && highlightedIndex < options.length) {
            const option = options[highlightedIndex];
            if (option) {
              handleSelect(option);
            }
          }
          break;
        case "Escape":
          e.preventDefault();
          setIsOpen(false);
          setInputValue("");
          setHighlightedIndex(-1);
          break;
        case "Tab":
          setIsOpen(false);
          setInputValue("");
          setHighlightedIndex(-1);
          break;
      }
    },
    [isOpen, highlightedIndex, options, handleSelect],
  );

  // Handle input focus
  const handleFocus = useCallback(() => {
    if (!disabled) {
      setIsOpen(true);
    }
  }, [disabled]);

  // Handle container click
  const handleContainerClick = useCallback(() => {
    if (!disabled) {
      inputRef.current?.focus();
    }
  }, [disabled]);

  // Display value
  const displayValue = selectedOption ? selectedOption.label : "";

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      {/* Input container */}
      <div
        onClick={handleContainerClick}
        className={cn(
          "relative flex items-center",
          "w-full h-10 px-3",
          "rounded-[var(--radius-md)]",
          "bg-[var(--color-card)] text-[var(--color-foreground)]",
          "border border-[var(--color-border)]",
          "transition-colors duration-150",
          "hover:border-[var(--color-muted)]",
          "focus-within:border-[var(--color-accent)] focus-within:ring-1 focus-within:ring-[var(--color-accent)]",
          error && "border-[var(--color-error)] focus-within:border-[var(--color-error)] focus-within:ring-[var(--color-error)]",
          disabled && "cursor-not-allowed opacity-50 bg-[var(--color-card-hover)]",
        )}
      >
        {/* Search icon */}
        <SearchIcon className="h-4 w-4 shrink-0 text-[var(--color-muted)] mr-2" />

        {/* Selected value display or input */}
        {selectedOption && !isOpen ? (
          <span className="flex-1 truncate text-sm">{displayValue}</span>
        ) : (
          <input
            ref={inputRef}
            id={inputId}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={handleFocus}
            disabled={disabled}
            placeholder={selectedOption ? displayValue : placeholder}
            autoComplete="off"
            role="combobox"
            aria-expanded={isOpen}
            aria-controls={listboxId}
            aria-activedescendant={highlightedIndex >= 0 ? `${listboxId}-option-${highlightedIndex}` : undefined}
            className={cn(
              "flex-1 min-w-0 bg-transparent",
              "text-sm text-[var(--color-foreground)]",
              "placeholder:text-[var(--color-muted)]",
              "focus:outline-none",
              "disabled:cursor-not-allowed",
            )}
          />
        )}

        {/* Loading indicator */}
        {isSearching && (
          <Spinner size="sm" className="shrink-0 ml-2" />
        )}

        {/* Clear button */}
        {selectedOption && !disabled && (
          <button
            type="button"
            onClick={handleClear}
            className={cn(
              "shrink-0 p-1 ml-1 rounded-[var(--radius-sm)]",
              "text-[var(--color-muted)]",
              "hover:text-[var(--color-foreground)]",
              "hover:bg-[var(--color-card-hover)]",
              "transition-colors duration-150",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[var(--color-accent)]",
            )}
            aria-label="Clear selection"
          >
            <XIcon className="h-4 w-4" />
          </button>
        )}

        {/* Dropdown indicator */}
        {!selectedOption && (
          <ChevronDownIcon
            className={cn(
              "h-4 w-4 shrink-0 ml-1 text-[var(--color-muted)]",
              "transition-transform duration-150",
              isOpen && "rotate-180",
            )}
          />
        )}
      </div>

      {/* Dropdown */}
      {isOpen && (
        <div
          id={listboxId}
          role="listbox"
          className={cn(
            "absolute z-50 w-full mt-1",
            "max-h-[240px] overflow-auto",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "py-1",
          )}
        >
          {/* Loading state */}
          {isSearching && (
            <div className="flex items-center justify-center py-4">
              <Spinner size="sm" />
              <span className="ml-2 text-sm text-[var(--color-muted)]">Searching...</span>
            </div>
          )}

          {/* Error state */}
          {searchError && !isSearching && (
            <div className="px-3 py-2 text-sm text-[var(--color-error)]">
              Failed to load options. Please try again.
            </div>
          )}

          {/* No results */}
          {!isSearching && !searchError && options.length === 0 && shouldSearch && (
            <div className="px-3 py-2 text-sm text-[var(--color-muted)]">
              No results found
            </div>
          )}

          {/* Prompt to type more */}
          {!isSearching && !searchError && !shouldSearch && inputValue.length > 0 && (
            <div className="px-3 py-2 text-sm text-[var(--color-muted)]">
              Type at least {minChars} character{minChars > 1 ? "s" : ""} to search
            </div>
          )}

          {/* Initial prompt */}
          {!isSearching && !searchError && !shouldSearch && inputValue.length === 0 && options.length === 0 && (
            <div className="px-3 py-2 text-sm text-[var(--color-muted)]">
              Start typing to search...
            </div>
          )}

          {/* Options */}
          {!isSearching && !searchError && options.map((option, index) => {
            const isHighlighted = index === highlightedIndex;
            const isSelected = selectedOption?.id === option.id;

            return (
              <button
                key={option.id}
                id={`${listboxId}-option-${index}`}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => handleSelect(option)}
                onMouseEnter={() => setHighlightedIndex(index)}
                className={cn(
                  "w-full px-3 py-2",
                  "flex items-center gap-2",
                  "text-sm text-left",
                  "transition-colors duration-150",
                  isHighlighted && "bg-[var(--color-card-hover)]",
                  isSelected && "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                  "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
                )}
              >
                <span className="truncate">{option.label}</span>
                {isSelected && (
                  <svg
                    className="h-4 w-4 shrink-0 ml-auto"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    aria-hidden="true"
                  >
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                )}
              </button>
            );
          })}

          {/* Has more indicator */}
          {!isSearching && !searchError && searchData?.has_more && (
            <div className="px-3 py-2 text-xs text-[var(--color-muted)] text-center border-t border-[var(--color-border)]">
              Type to refine results...
            </div>
          )}
        </div>
      )}
    </div>
  );
}

RelationshipPicker.displayName = "RelationshipPicker";

export default RelationshipPicker;
