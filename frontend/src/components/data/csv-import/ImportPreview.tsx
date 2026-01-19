"use client";

import { useMemo } from "react";
import { cn } from "@/lib/utils";
import type { ImportPreviewProps, ColumnMapping, ModelField, RowValidationResult } from "./types";

// ============================================================================
// Icons
// ============================================================================

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
      <polyline points="20,6 9,17 4,12" />
    </svg>
  );
}

function AlertIcon({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function XCircleIcon({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="10" />
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Gets the mapped model field for a CSV column index.
 */
function getMappedField(
  columnIndex: number,
  headers: readonly string[],
  mappings: readonly ColumnMapping[],
  modelFields: readonly ModelField[],
): ModelField | undefined {
  const header = headers[columnIndex];
  if (!header) return undefined;

  const mapping = mappings.find((m) => m.csvColumn === header);
  if (!mapping?.modelField) return undefined;

  return modelFields.find((f) => f.name === mapping.modelField);
}

/**
 * Gets validation result for a specific row.
 */
function getRowValidation(
  rowIndex: number,
  validation?: { results: readonly RowValidationResult[] },
): RowValidationResult | undefined {
  return validation?.results.find((r) => r.rowIndex === rowIndex);
}

// ============================================================================
// Sub-components
// ============================================================================

interface ValidationBadgeProps {
  rowValidation: RowValidationResult | undefined;
}

function ValidationBadge({ rowValidation }: ValidationBadgeProps) {
  if (!rowValidation) return null;

  if (rowValidation.valid && rowValidation.warnings.length === 0) {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-[var(--color-success)]/10 text-[var(--color-success)]"
        title="Valid row"
      >
        <CheckIcon className="w-3 h-3" />
        Valid
      </span>
    );
  }

  if (rowValidation.valid && rowValidation.warnings.length > 0) {
    return (
      <span
        className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-[var(--color-warning)]/10 text-[var(--color-warning)]"
        title={`${rowValidation.warnings.length} warning(s)`}
      >
        <AlertIcon className="w-3 h-3" />
        {rowValidation.warnings.length} warning{rowValidation.warnings.length > 1 ? "s" : ""}
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-[var(--color-error)]/10 text-[var(--color-error)]"
      title={`${rowValidation.errors.length} error(s)`}
    >
      <XCircleIcon className="w-3 h-3" />
      {rowValidation.errors.length} error{rowValidation.errors.length > 1 ? "s" : ""}
    </span>
  );
}

interface TableCellProps {
  value: string;
  mappedField: ModelField | undefined;
  columnIndex: number;
  rowIndex: number;
  validation: RowValidationResult | undefined;
}

function TableCell({ value, mappedField, validation }: TableCellProps) {
  // Check for field-specific errors
  const fieldError = validation?.errors.find((e) => e.field === mappedField?.name);
  const fieldWarning = validation?.warnings.find((w) => w.field === mappedField?.name);

  const hasError = !!fieldError;
  const hasWarning = !!fieldWarning && !hasError;

  return (
    <td
      className={cn(
        "px-3 py-2 text-sm",
        "border-b border-[var(--color-border)]",
        hasError && "bg-[var(--color-error)]/5",
        hasWarning && "bg-[var(--color-warning)]/5",
      )}
      title={
        fieldError?.message ||
        fieldWarning?.message ||
        (value.length > 50 ? value : undefined)
      }
    >
      <span
        className={cn(
          "block truncate max-w-[200px]",
          !mappedField && "text-[var(--color-muted)]",
          hasError && "text-[var(--color-error)]",
          hasWarning && "text-[var(--color-warning)]",
        )}
      >
        {value || <span className="italic text-[var(--color-muted)]">empty</span>}
      </span>
    </td>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Preview table for CSV import data.
 *
 * Features:
 * - Shows first N rows of CSV data
 * - Highlights mapped vs unmapped columns
 * - Displays validation errors/warnings inline
 * - Row-level validation status badges
 *
 * @example
 * ```tsx
 * <ImportPreview
 *   data={parsedCSV}
 *   mappings={columnMappings}
 *   modelFields={fields}
 *   validation={validationSummary}
 *   previewRows={5}
 * />
 * ```
 */
export function ImportPreview({
  data,
  mappings,
  modelFields,
  previewRows = 5,
  validation,
  className,
}: ImportPreviewProps) {
  // Get preview rows
  const previewData = useMemo(() => {
    return data.rows.slice(0, previewRows);
  }, [data.rows, previewRows]);

  // Calculate column stats
  const columnStats = useMemo(() => {
    const stats = data.headers.map((header, index) => {
      const mapping = mappings.find((m) => m.csvColumn === header);
      const field = mapping?.modelField
        ? modelFields.find((f) => f.name === mapping.modelField)
        : undefined;

      return {
        header,
        isMapped: !!mapping?.modelField,
        field,
        index,
      };
    });
    return stats;
  }, [data.headers, mappings, modelFields]);

  const mappedCount = columnStats.filter((c) => c.isMapped).length;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-[var(--color-foreground)]">
            Data Preview
          </h3>
          <p className="text-xs text-[var(--color-muted)]">
            Showing {previewData.length} of {data.totalRows} rows |{" "}
            {mappedCount} of {data.headers.length} columns mapped
          </p>
        </div>
        {validation && (
          <div className="flex items-center gap-3 text-xs">
            <span className="flex items-center gap-1 text-[var(--color-success)]">
              <CheckIcon className="w-3.5 h-3.5" />
              {validation.validRows} valid
            </span>
            {validation.warningRows > 0 && (
              <span className="flex items-center gap-1 text-[var(--color-warning)]">
                <AlertIcon className="w-3.5 h-3.5" />
                {validation.warningRows} warnings
              </span>
            )}
            {validation.errorRows > 0 && (
              <span className="flex items-center gap-1 text-[var(--color-error)]">
                <XCircleIcon className="w-3.5 h-3.5" />
                {validation.errorRows} errors
              </span>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div
        className={cn(
          "overflow-x-auto rounded-[var(--radius-md)]",
          "border border-[var(--color-border)]",
        )}
      >
        <table className="w-full min-w-max">
          {/* Column Headers */}
          <thead className="bg-[var(--color-card)]">
            <tr>
              <th
                className={cn(
                  "px-3 py-2 text-left text-xs font-semibold",
                  "text-[var(--color-muted)] border-b border-[var(--color-border)]",
                  "w-10",
                )}
              >
                #
              </th>
              {columnStats.map((col) => (
                <th
                  key={col.header}
                  className={cn(
                    "px-3 py-2 text-left text-xs font-semibold",
                    "border-b border-[var(--color-border)]",
                    col.isMapped
                      ? "text-[var(--color-foreground)]"
                      : "text-[var(--color-muted)]",
                  )}
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5">
                      {col.isMapped && (
                        <CheckIcon className="w-3 h-3 text-[var(--color-success)]" />
                      )}
                      <span className="truncate max-w-[150px]" title={col.header}>
                        {col.header}
                      </span>
                    </div>
                    {col.field && (
                      <div
                        className={cn(
                          "text-[10px] font-normal px-1.5 py-0.5 rounded",
                          "bg-[var(--color-accent)]/10 text-[var(--color-accent)]",
                          "inline-block",
                        )}
                      >
                        {col.field.label}
                        {col.field.required && " *"}
                      </div>
                    )}
                    {!col.isMapped && (
                      <div
                        className={cn(
                          "text-[10px] font-normal px-1.5 py-0.5 rounded",
                          "bg-[var(--color-muted)]/10 text-[var(--color-muted)]",
                          "inline-block",
                        )}
                      >
                        Skipped
                      </div>
                    )}
                  </div>
                </th>
              ))}
              {validation && (
                <th
                  className={cn(
                    "px-3 py-2 text-left text-xs font-semibold",
                    "text-[var(--color-muted)] border-b border-[var(--color-border)]",
                    "w-24",
                  )}
                >
                  Status
                </th>
              )}
            </tr>
          </thead>

          {/* Data Rows */}
          <tbody>
            {previewData.map((row, rowIndex) => {
              const rowValidation = getRowValidation(rowIndex, validation);
              return (
                <tr
                  key={rowIndex}
                  className={cn(
                    "transition-colors",
                    "hover:bg-[var(--color-card-hover)]/50",
                    rowValidation?.errors.length &&
                      "bg-[var(--color-error)]/5 hover:bg-[var(--color-error)]/10",
                  )}
                >
                  <td
                    className={cn(
                      "px-3 py-2 text-xs text-[var(--color-muted)]",
                      "border-b border-[var(--color-border)]",
                    )}
                  >
                    {rowIndex + 1}
                  </td>
                  {row.map((cell, cellIndex) => {
                    const mappedField = getMappedField(
                      cellIndex,
                      data.headers,
                      mappings,
                      modelFields,
                    );
                    return (
                      <TableCell
                        key={cellIndex}
                        value={cell}
                        mappedField={mappedField}
                        columnIndex={cellIndex}
                        rowIndex={rowIndex}
                        validation={rowValidation}
                      />
                    );
                  })}
                  {validation && (
                    <td
                      className={cn(
                        "px-3 py-2 border-b border-[var(--color-border)]",
                      )}
                    >
                      <ValidationBadge rowValidation={rowValidation} />
                    </td>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* More rows indicator */}
      {data.totalRows > previewRows && (
        <p className="text-xs text-[var(--color-muted)] text-center">
          ... and {data.totalRows - previewRows} more rows
        </p>
      )}

      {/* Validation summary details */}
      {validation && validation.errorRows > 0 && (
        <div
          className={cn(
            "p-3 rounded-[var(--radius-md)]",
            "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
          )}
        >
          <div className="flex items-start gap-2">
            <XCircleIcon className="w-4 h-4 flex-shrink-0 mt-0.5 text-[var(--color-error)]" />
            <div className="text-xs text-[var(--color-error)]">
              <p className="font-medium">
                {validation.errorRows} row{validation.errorRows > 1 ? "s" : ""} with errors
              </p>
              <p className="mt-1 text-[var(--color-muted)]">
                Rows with errors will be skipped during import. You can proceed to import
                only the valid rows, or go back to fix the issues.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

ImportPreview.displayName = "ImportPreview";
