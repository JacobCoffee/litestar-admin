"use client";

import { useCallback, useRef, useState, type DragEvent, type ChangeEvent } from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { CSVDropzoneProps } from "./types";

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Formats file size in human-readable format.
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Validates a file for CSV import.
 */
function validateFile(
  file: File,
  maxFileSize?: number,
): { valid: boolean; error?: string } {
  // Check file type
  const isCSV =
    file.type === "text/csv" ||
    file.type === "application/vnd.ms-excel" ||
    file.name.toLowerCase().endsWith(".csv");

  if (!isCSV) {
    return {
      valid: false,
      error: "Please select a CSV file (.csv)",
    };
  }

  // Check file size
  if (maxFileSize && file.size > maxFileSize) {
    return {
      valid: false,
      error: `File size exceeds maximum of ${formatFileSize(maxFileSize)}`,
    };
  }

  return { valid: true };
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

function FileIcon({ className }: { className?: string }) {
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
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14,2 14,8 20,8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <polyline points="10,9 9,9 8,9" />
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
      <polyline points="20,6 9,17 4,12" />
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
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * CSV file drop zone component with drag-and-drop support.
 *
 * Features:
 * - Drag and drop file selection
 * - Click to browse
 * - File type validation (.csv only)
 * - File size validation
 * - Selected file display with size
 *
 * @example
 * ```tsx
 * <CSVDropzone
 *   onFileSelect={handleFileSelect}
 *   selectedFile={file}
 *   maxFileSize={10 * 1024 * 1024}
 * />
 * ```
 */
export function CSVDropzone({
  onFileSelect,
  selectedFile,
  disabled = false,
  error,
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  className,
}: CSVDropzoneProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  // Handle file selection
  const handleFile = useCallback(
    (file: File) => {
      setValidationError(null);
      const validation = validateFile(file, maxFileSize);

      if (!validation.valid) {
        setValidationError(validation.error || "Invalid file");
        return;
      }

      onFileSelect(file);
    },
    [maxFileSize, onFileSelect],
  );

  // Drag event handlers
  const handleDragEnter = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragOver(true);
      }
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDragOver = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) {
        setIsDragOver(true);
      }
    },
    [disabled],
  );

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      if (disabled) return;

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file) {
          handleFile(file);
        }
      }
    },
    [disabled, handleFile],
  );

  // Input change handler
  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        const file = files[0];
        if (file) {
          handleFile(file);
        }
      }
      // Reset input value to allow selecting the same file again
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [handleFile],
  );

  // Clear file handler
  const handleClearFile = useCallback(() => {
    setValidationError(null);
    onFileSelect(null as unknown as File);
  }, [onFileSelect]);

  const displayError = error || validationError;
  const hasFile = selectedFile !== null;

  return (
    <div className={cn("space-y-3", className)}>
      {/* Drop Zone */}
      <div
        className={cn(
          "relative rounded-[var(--radius-md)] border-2 border-dashed",
          "transition-all duration-150",
          isDragOver
            ? "border-[var(--color-accent)] bg-[var(--color-accent)]/5"
            : hasFile
              ? "border-[var(--color-success)]/50 bg-[var(--color-success)]/5"
              : "border-[var(--color-border)] hover:border-[var(--color-muted)]",
          displayError && "border-[var(--color-error)]",
          disabled && "opacity-50 cursor-not-allowed",
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label={hasFile ? `Selected file: ${selectedFile.name}` : "Drop CSV file here or click to browse"}
        onKeyDown={(e) => {
          if (!disabled && (e.key === "Enter" || e.key === " ")) {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
      >
        <div
          className={cn(
            "flex flex-col items-center justify-center py-8 px-4",
            "text-center",
          )}
        >
          {hasFile ? (
            <>
              {/* Selected File Display */}
              <div
                className={cn(
                  "w-14 h-14 mb-4 rounded-full",
                  "bg-[var(--color-success)]/10 flex items-center justify-center",
                )}
              >
                <FileIcon className="w-7 h-7 text-[var(--color-success)]" />
              </div>
              <div className="flex items-center gap-2 mb-1">
                <CheckIcon className="w-4 h-4 text-[var(--color-success)]" />
                <p className="text-sm font-medium text-[var(--color-foreground)]">
                  {selectedFile.name}
                </p>
              </div>
              <p className="text-xs text-[var(--color-muted)] mb-4">
                {formatFileSize(selectedFile.size)}
              </p>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation();
                  handleClearFile();
                }}
                disabled={disabled}
                leftIcon={<XIcon className="w-3 h-3" />}
              >
                Remove File
              </Button>
            </>
          ) : (
            <>
              {/* Upload Prompt */}
              <div
                className={cn(
                  "w-14 h-14 mb-4 rounded-full",
                  "bg-[var(--color-card-hover)] flex items-center justify-center",
                  isDragOver && "bg-[var(--color-accent)]/10",
                )}
              >
                <UploadIcon
                  className={cn(
                    "w-7 h-7",
                    isDragOver ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]",
                  )}
                />
              </div>

              <p className="text-sm text-[var(--color-foreground)] mb-1">
                {isDragOver ? "Drop CSV file here" : "Drag and drop your CSV file here"}
              </p>
              <p className="text-xs text-[var(--color-muted)] mb-4">or</p>

              <Button
                type="button"
                variant="secondary"
                size="sm"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  inputRef.current?.click();
                }}
              >
                Browse Files
              </Button>
            </>
          )}

          {/* Hidden file input */}
          <input
            ref={inputRef}
            type="file"
            accept=".csv,text/csv,application/vnd.ms-excel"
            disabled={disabled}
            onChange={handleInputChange}
            className="sr-only"
            aria-describedby={displayError ? "csv-dropzone-error" : "csv-dropzone-hint"}
          />
        </div>
      </div>

      {/* Hint Text */}
      {!displayError && (
        <p id="csv-dropzone-hint" className="text-xs text-[var(--color-muted)]">
          Supported format: CSV | Max size: {formatFileSize(maxFileSize)}
        </p>
      )}

      {/* Error Message */}
      {displayError && (
        <p
          id="csv-dropzone-error"
          className="text-xs text-[var(--color-error)]"
          role="alert"
          aria-live="polite"
        >
          {displayError}
        </p>
      )}
    </div>
  );
}

CSVDropzone.displayName = "CSVDropzone";
