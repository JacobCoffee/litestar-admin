"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { CSVImportWizard } from "./CSVImportWizard";
import type { ModelField, ImportResult } from "./types";

// ============================================================================
// Types
// ============================================================================

/**
 * Props for the CSVImportButton component.
 */
export interface CSVImportButtonProps {
  /** Model name/identity */
  model: string;
  /** Available model fields for mapping */
  fields: readonly ModelField[];
  /** Callback when import is successful */
  onSuccess?: (result: ImportResult) => void;
  /** Button variant */
  variant?: "default" | "icon";
  /** Button size */
  size?: "sm" | "md" | "lg";
  /** Maximum file size in bytes */
  maxFileSize?: number;
  /** Maximum rows to import */
  maxRows?: number;
  /** Whether the button is disabled */
  disabled?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Icons
// ============================================================================

function UploadIcon({ className }: { className?: string }) {
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
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17,8 12,3 7,8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Button component that opens the CSV Import Wizard when clicked.
 *
 * This is a convenience wrapper around CSVImportWizard that handles
 * the open/close state automatically.
 *
 * @example
 * ```tsx
 * // Default button
 * <CSVImportButton
 *   model="users"
 *   fields={modelFields}
 *   onSuccess={(result) => {
 *     console.log("Imported:", result.importedRows);
 *     refetchUsers();
 *   }}
 * />
 *
 * // Icon-only button
 * <CSVImportButton
 *   model="users"
 *   fields={modelFields}
 *   variant="icon"
 *   onSuccess={handleSuccess}
 * />
 * ```
 */
export function CSVImportButton({
  model,
  fields,
  onSuccess,
  variant = "default",
  size = "md",
  maxFileSize,
  maxRows,
  disabled = false,
  className,
}: CSVImportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = useCallback(() => {
    setIsOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const handleSuccess = useCallback(
    (result: ImportResult) => {
      onSuccess?.(result);
    },
    [onSuccess],
  );

  const uploadIcon = <UploadIcon className="h-4 w-4" />;

  return (
    <>
      {variant === "icon" ? (
        <button
          type="button"
          onClick={handleOpen}
          disabled={disabled}
          className={cn(
            "inline-flex items-center justify-center",
            "w-9 h-9 rounded-[var(--radius-md)]",
            "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
            "bg-[var(--color-card)] hover:bg-[var(--color-card-hover)]",
            "border border-[var(--color-border)] hover:border-[var(--color-muted)]",
            "transition-colors duration-150",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            className,
          )}
          aria-label="Import CSV"
          title="Import CSV"
        >
          {uploadIcon}
        </button>
      ) : (
        <Button
          variant="secondary"
          size={size}
          onClick={handleOpen}
          disabled={disabled}
          leftIcon={uploadIcon}
          className={className}
        >
          Import CSV
        </Button>
      )}

      <CSVImportWizard
        model={model}
        fields={fields}
        isOpen={isOpen}
        onClose={handleClose}
        onSuccess={handleSuccess}
        maxFileSize={maxFileSize}
        maxRows={maxRows}
      />
    </>
  );
}

CSVImportButton.displayName = "CSVImportButton";
