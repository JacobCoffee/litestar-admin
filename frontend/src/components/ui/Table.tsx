"use client";

import {
  forwardRef,
  type HTMLAttributes,
  type TdHTMLAttributes,
  type ThHTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

export type SortDirection = "asc" | "desc" | null;

export interface TableProps extends HTMLAttributes<HTMLTableElement> {
  striped?: boolean;
  children?: ReactNode;
}

export const Table = forwardRef<HTMLTableElement, TableProps>(
  ({ striped = false, className, children, ...props }, ref) => {
    return (
      <div className="w-full overflow-x-auto">
        <table
          ref={ref}
          className={cn(
            "w-full border-collapse",
            "text-sm text-[var(--color-foreground)]",
            striped && "[&_tbody_tr:nth-child(even)]:bg-[var(--color-card-hover)]/30",
            className,
          )}
          {...props}
        >
          {children}
        </table>
      </div>
    );
  },
);

Table.displayName = "Table";

export interface TableHeaderProps extends HTMLAttributes<HTMLTableSectionElement> {
  children?: ReactNode;
}

export const TableHeader = forwardRef<HTMLTableSectionElement, TableHeaderProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <thead
        ref={ref}
        className={cn("bg-[var(--color-card)]", "border-b border-[var(--color-border)]", className)}
        {...props}
      >
        {children}
      </thead>
    );
  },
);

TableHeader.displayName = "TableHeader";

export interface TableBodyProps extends HTMLAttributes<HTMLTableSectionElement> {
  children?: ReactNode;
}

export const TableBody = forwardRef<HTMLTableSectionElement, TableBodyProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <tbody
        ref={ref}
        className={cn("divide-y divide-[var(--color-border)]", className)}
        {...props}
      >
        {children}
      </tbody>
    );
  },
);

TableBody.displayName = "TableBody";

export interface TableRowProps extends HTMLAttributes<HTMLTableRowElement> {
  children?: ReactNode;
}

export const TableRow = forwardRef<HTMLTableRowElement, TableRowProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <tr
        ref={ref}
        className={cn(
          "transition-colors duration-150",
          "hover:bg-[var(--color-card-hover)]",
          className,
        )}
        {...props}
      >
        {children}
      </tr>
    );
  },
);

TableRow.displayName = "TableRow";

export interface TableHeadProps extends ThHTMLAttributes<HTMLTableCellElement> {
  sortable?: boolean;
  sortDirection?: SortDirection;
  onSort?: () => void;
  children?: ReactNode;
}

const SortIcon = ({ direction }: { direction: SortDirection }) => {
  if (direction === null) {
    return (
      <svg
        className="h-4 w-4 opacity-40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path d="M7 15l5 5 5-5M7 9l5-5 5 5" />
      </svg>
    );
  }

  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      {direction === "asc" ? <path d="M7 14l5-5 5 5" /> : <path d="M7 10l5 5 5-5" />}
    </svg>
  );
};

export const TableHead = forwardRef<HTMLTableCellElement, TableHeadProps>(
  ({ sortable = false, sortDirection = null, onSort, className, children, ...props }, ref) => {
    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (sortable && onSort && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        onSort();
      }
    };

    // Build aria-label for sortable columns
    const getSortAriaLabel = () => {
      if (!sortable) return undefined;
      const columnName = typeof children === "string" ? children : "column";
      if (sortDirection === "asc") {
        return `${columnName}, sorted ascending, click to sort descending`;
      } else if (sortDirection === "desc") {
        return `${columnName}, sorted descending, click to sort ascending`;
      }
      return `${columnName}, click to sort ascending`;
    };

    return (
      <th
        ref={ref}
        className={cn(
          "px-4 py-3 text-left font-semibold",
          "text-[var(--color-muted)]",
          sortable && [
            "cursor-pointer select-none",
            "hover:text-[var(--color-foreground)]",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2",
            "focus-visible:ring-[var(--color-accent)] focus-visible:ring-inset",
          ],
          className,
        )}
        onClick={sortable ? onSort : undefined}
        onKeyDown={handleKeyDown}
        tabIndex={sortable ? 0 : undefined}
        role={sortable ? "columnheader button" : "columnheader"}
        aria-sort={
          sortDirection === "asc"
            ? "ascending"
            : sortDirection === "desc"
              ? "descending"
              : undefined
        }
        aria-label={getSortAriaLabel()}
        scope="col"
        {...props}
      >
        <div className="flex items-center gap-1">
          {children}
          {sortable && <SortIcon direction={sortDirection} />}
        </div>
      </th>
    );
  },
);

TableHead.displayName = "TableHead";

export interface TableCellProps extends TdHTMLAttributes<HTMLTableCellElement> {
  children?: ReactNode;
}

export const TableCell = forwardRef<HTMLTableCellElement, TableCellProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <td ref={ref} className={cn("px-4 py-3", className)} {...props}>
        {children}
      </td>
    );
  },
);

TableCell.displayName = "TableCell";
