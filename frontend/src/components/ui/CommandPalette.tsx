"use client";

import {
  forwardRef,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type HTMLAttributes,
  type KeyboardEvent as ReactKeyboardEvent,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import { SearchIcon } from "@/lib/icons";

/**
 * A command item displayed in the palette.
 */
export interface CommandItem {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Optional description */
  description?: string;
  /** Category for grouping */
  category?: string;
  /** Icon component */
  icon?: ReactNode;
  /** Keyboard shortcut hint (e.g., "Cmd + K") */
  shortcut?: string;
  /** Handler when selected */
  onSelect: () => void;
  /** Keywords for searching */
  keywords?: string[];
  /** Whether the item is disabled */
  disabled?: boolean;
}

/**
 * Props for the CommandPalette component.
 */
export interface CommandPaletteProps extends Omit<HTMLAttributes<HTMLDivElement>, "onSelect"> {
  /** Whether the palette is open */
  isOpen: boolean;
  /** Callback when the palette should close */
  onClose: () => void;
  /** Items to display in the palette */
  items: CommandItem[];
  /** Placeholder text for the search input */
  placeholder?: string;
  /** Empty state message when no results */
  emptyMessage?: string;
  /** Loading state */
  isLoading?: boolean;
  /** Custom filter function */
  filterFn?: (item: CommandItem, query: string) => boolean;
  /** Callback when search query changes */
  onQueryChange?: (query: string) => void;
  /** Maximum height of the results list */
  maxHeight?: number | string;
}

/**
 * Default filter function for matching items against a query.
 */
function defaultFilter(item: CommandItem, query: string): boolean {
  const searchTerm = query.toLowerCase().trim();
  if (!searchTerm) return true;

  const label = item.label.toLowerCase();
  const description = item.description?.toLowerCase() || "";
  const category = item.category?.toLowerCase() || "";
  const keywords = item.keywords?.map((k) => k.toLowerCase()) || [];

  return (
    label.includes(searchTerm) ||
    description.includes(searchTerm) ||
    category.includes(searchTerm) ||
    keywords.some((k) => k.includes(searchTerm))
  );
}

/**
 * Group items by category.
 */
function groupByCategory(items: CommandItem[]): Map<string, CommandItem[]> {
  const groups = new Map<string, CommandItem[]>();

  for (const item of items) {
    const category = item.category || "General";
    const existing = groups.get(category) || [];
    existing.push(item);
    groups.set(category, existing);
  }

  return groups;
}

/**
 * CommandPalette - A spotlight-style search modal (Cmd+K).
 *
 * Features:
 * - Fuzzy search across items
 * - Keyboard navigation (arrow keys, enter, escape)
 * - Grouped results by category
 * - Shortcut hints
 * - Accessible with proper ARIA attributes
 *
 * @example
 * ```tsx
 * const [open, setOpen] = useState(false);
 *
 * const items: CommandItem[] = [
 *   {
 *     id: 'users',
 *     label: 'Go to Users',
 *     category: 'Navigation',
 *     onSelect: () => router.push('/admin/users'),
 *   },
 *   {
 *     id: 'new-user',
 *     label: 'Create User',
 *     category: 'Actions',
 *     shortcut: 'Cmd + N',
 *     onSelect: () => router.push('/admin/users/new'),
 *   },
 * ];
 *
 * <CommandPalette
 *   isOpen={open}
 *   onClose={() => setOpen(false)}
 *   items={items}
 *   placeholder="Search commands..."
 * />
 * ```
 */
export const CommandPalette = forwardRef<HTMLDivElement, CommandPaletteProps>(
  (
    {
      isOpen,
      onClose,
      items,
      placeholder = "Search commands...",
      emptyMessage = "No results found.",
      isLoading = false,
      filterFn = defaultFilter,
      onQueryChange,
      maxHeight = 400,
      className,
      ...props
    },
    ref,
  ) => {
    const paletteId = useId();
    const inputRef = useRef<HTMLInputElement>(null);
    const listRef = useRef<HTMLDivElement>(null);
    const [query, setQuery] = useState("");
    const [selectedIndex, setSelectedIndex] = useState(0);

    // Filter items based on query
    const filteredItems = useMemo(() => {
      return items.filter((item) => filterFn(item, query));
    }, [items, query, filterFn]);

    // Group filtered items by category
    const groupedItems = useMemo(() => {
      return groupByCategory(filteredItems);
    }, [filteredItems]);

    // Flatten grouped items for keyboard navigation
    const flattenedItems = useMemo(() => {
      const result: CommandItem[] = [];
      for (const group of groupedItems.values()) {
        result.push(...group);
      }
      return result;
    }, [groupedItems]);

    // Reset selection when items change
    useEffect(() => {
      setSelectedIndex(0);
    }, [filteredItems.length]);

    // Focus input when opening
    useEffect(() => {
      if (isOpen) {
        setQuery("");
        setSelectedIndex(0);
        requestAnimationFrame(() => {
          inputRef.current?.focus();
        });
      }
    }, [isOpen]);

    // Scroll selected item into view
    useEffect(() => {
      if (!listRef.current) return;

      const selectedId = flattenedItems[selectedIndex]?.id;
      if (!selectedId) return;

      const selectedElement = listRef.current.querySelector(
        `[data-command-id="${selectedId}"]`,
      );
      if (selectedElement) {
        selectedElement.scrollIntoView({ block: "nearest" });
      }
    }, [selectedIndex, flattenedItems]);

    const handleQueryChange = useCallback(
      (value: string) => {
        setQuery(value);
        setSelectedIndex(0);
        onQueryChange?.(value);
      },
      [onQueryChange],
    );

    const handleSelect = useCallback(
      (item: CommandItem) => {
        if (item.disabled) return;
        onClose();
        item.onSelect();
      },
      [onClose],
    );

    const handleKeyDown = useCallback(
      (e: ReactKeyboardEvent<HTMLInputElement>) => {
        switch (e.key) {
          case "ArrowDown":
            e.preventDefault();
            setSelectedIndex((prev) =>
              prev < flattenedItems.length - 1 ? prev + 1 : prev,
            );
            break;

          case "ArrowUp":
            e.preventDefault();
            setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
            break;

          case "Enter":
            e.preventDefault();
            const selectedItem = flattenedItems[selectedIndex];
            if (selectedItem) {
              handleSelect(selectedItem);
            }
            break;

          case "Escape":
            e.preventDefault();
            onClose();
            break;

          case "Tab":
            e.preventDefault();
            if (e.shiftKey) {
              setSelectedIndex((prev) => (prev > 0 ? prev - 1 : prev));
            } else {
              setSelectedIndex((prev) =>
                prev < flattenedItems.length - 1 ? prev + 1 : prev,
              );
            }
            break;
        }
      },
      [flattenedItems, selectedIndex, handleSelect, onClose],
    );

    const handleOverlayClick = useCallback(() => {
      onClose();
    }, [onClose]);

    if (!isOpen) return null;

    const paletteContent = (
      <div
        className={cn(
          "fixed inset-0 z-50",
          "flex items-start justify-center pt-[15vh]",
          "animate-[fadeIn_100ms_ease-out]",
        )}
        onClick={handleOverlayClick}
        role="dialog"
        aria-modal="true"
        aria-labelledby={`${paletteId}-label`}
      >
        {/* Backdrop */}
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm"
          aria-hidden="true"
        />

        {/* Palette Container */}
        <div
          ref={ref}
          className={cn(
            "relative z-10 w-full max-w-xl",
            "bg-[var(--color-card)] rounded-[var(--radius-lg)]",
            "border border-[var(--color-border)]",
            "shadow-2xl shadow-black/50",
            "animate-[scaleIn_100ms_ease-out]",
            "overflow-hidden",
            className,
          )}
          onClick={(e) => e.stopPropagation()}
          {...props}
        >
          {/* Search Header */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)]">
            <SearchIcon className="h-5 w-5 text-[var(--color-muted)] shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => handleQueryChange(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className={cn(
                "flex-1 bg-transparent",
                "text-base text-[var(--color-foreground)]",
                "placeholder:text-[var(--color-muted)]",
                "focus:outline-none",
              )}
              role="combobox"
              aria-expanded={isOpen}
              aria-controls={`${paletteId}-list`}
              aria-activedescendant={
                flattenedItems[selectedIndex]
                  ? `${paletteId}-item-${flattenedItems[selectedIndex].id}`
                  : undefined
              }
              aria-label="Search commands"
              id={`${paletteId}-label`}
            />
            <kbd
              className={cn(
                "hidden sm:flex items-center gap-1",
                "px-1.5 py-0.5 rounded-[var(--radius-sm)]",
                "bg-[var(--color-background)] border border-[var(--color-border)]",
                "text-xs text-[var(--color-muted)]",
                "font-mono",
              )}
            >
              esc
            </kbd>
          </div>

          {/* Results List */}
          <div
            ref={listRef}
            id={`${paletteId}-list`}
            role="listbox"
            className="overflow-y-auto"
            style={{ maxHeight }}
          >
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <div className="h-6 w-6 border-2 border-[var(--color-accent)] border-t-transparent rounded-full animate-spin" />
              </div>
            ) : filteredItems.length === 0 ? (
              <div className="py-8 text-center text-[var(--color-muted)]">
                {emptyMessage}
              </div>
            ) : (
              <div className="py-2">
                {Array.from(groupedItems.entries()).map(([category, categoryItems]) => (
                  <div key={category}>
                    {/* Category Header */}
                    <div
                      className={cn(
                        "px-4 py-1.5",
                        "text-xs font-medium text-[var(--color-muted)]",
                        "uppercase tracking-wider",
                      )}
                    >
                      {category}
                    </div>

                    {/* Category Items */}
                    {categoryItems.map((item) => {
                      const flatIndex = flattenedItems.findIndex((f) => f.id === item.id);
                      const isSelected = flatIndex === selectedIndex;

                      return (
                        <CommandPaletteItem
                          key={item.id}
                          item={item}
                          isSelected={isSelected}
                          paletteId={paletteId}
                          onSelect={() => handleSelect(item)}
                          onMouseEnter={() => setSelectedIndex(flatIndex)}
                        />
                      );
                    })}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          {filteredItems.length > 0 && (
            <div
              className={cn(
                "flex items-center justify-between gap-4 px-4 py-2",
                "border-t border-[var(--color-border)]",
                "bg-[var(--color-background)]/50",
                "text-xs text-[var(--color-muted)]",
              )}
            >
              <div className="flex items-center gap-3">
                <span className="flex items-center gap-1">
                  <kbd className="px-1 py-0.5 rounded bg-[var(--color-card)] border border-[var(--color-border)] font-mono">
                    {"\u2191"}
                  </kbd>
                  <kbd className="px-1 py-0.5 rounded bg-[var(--color-card)] border border-[var(--color-border)] font-mono">
                    {"\u2193"}
                  </kbd>
                  <span className="ml-1">navigate</span>
                </span>
                <span className="flex items-center gap-1">
                  <kbd className="px-1 py-0.5 rounded bg-[var(--color-card)] border border-[var(--color-border)] font-mono">
                    {"\u23CE"}
                  </kbd>
                  <span className="ml-1">select</span>
                </span>
              </div>
              <span>{filteredItems.length} results</span>
            </div>
          )}
        </div>
      </div>
    );

    if (typeof document === "undefined") return null;

    return createPortal(paletteContent, document.body);
  },
);

CommandPalette.displayName = "CommandPalette";

/**
 * Props for a command palette item.
 */
interface CommandPaletteItemProps {
  item: CommandItem;
  isSelected: boolean;
  paletteId: string;
  onSelect: () => void;
  onMouseEnter: () => void;
}

/**
 * Individual item in the command palette.
 */
function CommandPaletteItem({
  item,
  isSelected,
  paletteId,
  onSelect,
  onMouseEnter,
}: CommandPaletteItemProps) {
  return (
    <div
      id={`${paletteId}-item-${item.id}`}
      role="option"
      aria-selected={isSelected}
      aria-disabled={item.disabled}
      data-command-id={item.id}
      onClick={onSelect}
      onMouseEnter={onMouseEnter}
      className={cn(
        "flex items-center gap-3 px-4 py-2.5 mx-2 rounded-[var(--radius-md)]",
        "cursor-pointer transition-colors duration-75",
        isSelected
          ? "bg-[var(--color-accent)]/15 text-[var(--color-foreground)]"
          : "text-[var(--color-foreground)] hover:bg-[var(--color-card-hover)]",
        item.disabled && "opacity-50 cursor-not-allowed",
      )}
    >
      {/* Icon */}
      {item.icon && (
        <span
          className={cn(
            "shrink-0",
            isSelected ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]",
          )}
        >
          {item.icon}
        </span>
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="truncate font-medium">{item.label}</div>
        {item.description && (
          <div className="truncate text-sm text-[var(--color-muted)]">
            {item.description}
          </div>
        )}
      </div>

      {/* Shortcut */}
      {item.shortcut && (
        <kbd
          className={cn(
            "shrink-0 px-1.5 py-0.5 rounded-[var(--radius-sm)]",
            "bg-[var(--color-background)] border border-[var(--color-border)]",
            "text-xs text-[var(--color-muted)]",
            "font-mono",
          )}
        >
          {item.shortcut}
        </kbd>
      )}
    </div>
  );
}

/**
 * Re-export types for convenience.
 */
export type { CommandItem as CommandPaletteItem };
