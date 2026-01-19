"use client";

import {
  useCallback,
  useId,
  useRef,
  useState,
  type DragEvent,
  type ChangeEvent,
} from "react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import type { FileFieldConfig, UploadedFile, FileUploadStatus } from "@/types";
import { api } from "@/lib/api";

// ============================================================================
// Types
// ============================================================================

export interface FileUploadProps {
  /** Unique field name */
  name: string;
  /** Label for the field */
  label?: string;
  /** Configuration for file validation */
  config?: FileFieldConfig;
  /** Currently uploaded files (controlled) */
  value?: UploadedFile[];
  /** Callback when files change */
  onChange?: (files: UploadedFile[]) => void;
  /** Error message to display */
  error?: string;
  /** Hint text to display */
  hint?: string;
  /** Whether the field is disabled */
  disabled?: boolean;
  /** Whether the field is required */
  required?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Generates a unique ID for a file.
 */
function generateFileId(): string {
  return `file-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

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
 * Gets the file extension from a filename.
 */
function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf(".");
  return lastDot === -1 ? "" : filename.substring(lastDot).toLowerCase();
}

/**
 * Checks if a file is an image based on MIME type.
 */
function isImageFile(file: File | UploadedFile): boolean {
  const type = "type" in file ? file.type : "";
  return type.startsWith("image/");
}

/**
 * Validates a file against the configuration.
 */
function validateFile(
  file: File,
  config: FileFieldConfig,
  existingCount: number,
): { valid: boolean; error?: string } {
  // Check file size
  if (config.maxSize && file.size > config.maxSize) {
    return {
      valid: false,
      error: `File "${file.name}" exceeds maximum size of ${formatFileSize(config.maxSize)}`,
    };
  }

  // Check extension
  if (config.allowedExtensions && config.allowedExtensions.length > 0) {
    const ext = getFileExtension(file.name);
    const allowed = config.allowedExtensions.map((e) =>
      e.startsWith(".") ? e.toLowerCase() : `.${e.toLowerCase()}`,
    );
    if (!allowed.includes(ext)) {
      return {
        valid: false,
        error: `File type "${ext || "unknown"}" is not allowed. Allowed: ${allowed.join(", ")}`,
      };
    }
  }

  // Check MIME type
  if (config.allowedMimeTypes && config.allowedMimeTypes.length > 0) {
    if (!config.allowedMimeTypes.includes(file.type)) {
      return {
        valid: false,
        error: `File type "${file.type}" is not allowed`,
      };
    }
  }

  // Check max files
  if (config.maxFiles && existingCount >= config.maxFiles) {
    return {
      valid: false,
      error: `Maximum of ${config.maxFiles} file${config.maxFiles > 1 ? "s" : ""} allowed`,
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
    </svg>
  );
}

function ImageIcon({ className }: { className?: string }) {
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
      <circle cx="8.5" cy="8.5" r="1.5" />
      <polyline points="21,15 16,10 5,21" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
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
      <polyline points="3,6 5,6 21,6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
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

// ============================================================================
// FileItem Component
// ============================================================================

interface FileItemProps {
  file: UploadedFile;
  onRemove: (id: string) => void;
  onPreview?: (file: UploadedFile) => void;
  disabled?: boolean;
}

function FileItem({ file, onRemove, onPreview, disabled }: FileItemProps) {
  const isImage = file.type.startsWith("image/");
  const statusColors: Record<FileUploadStatus, string> = {
    idle: "text-[var(--color-muted)]",
    uploading: "text-[var(--color-accent)]",
    success: "text-[var(--color-success)]",
    error: "text-[var(--color-error)]",
  };

  return (
    <div
      className={cn(
        "flex items-center gap-3 p-3",
        "bg-[var(--color-card-hover)] rounded-[var(--radius-md)]",
        "border border-[var(--color-border)]",
        file.status === "error" && "border-[var(--color-error)]/50",
      )}
    >
      {/* Preview/Icon */}
      <div
        className={cn(
          "flex-shrink-0 w-12 h-12 rounded-[var(--radius-sm)]",
          "bg-[var(--color-card)] border border-[var(--color-border)]",
          "flex items-center justify-center overflow-hidden",
          isImage && onPreview && "cursor-pointer hover:opacity-80 transition-opacity",
        )}
        onClick={() => isImage && onPreview?.(file)}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && isImage && onPreview) {
            e.preventDefault();
            onPreview(file);
          }
        }}
        tabIndex={isImage && onPreview ? 0 : -1}
        role={isImage && onPreview ? "button" : undefined}
        aria-label={isImage && onPreview ? `Preview ${file.name}` : undefined}
      >
        {isImage && (file.thumbnailUrl || file.url) ? (
          <img
            src={file.thumbnailUrl || file.url}
            alt={file.name}
            className="w-full h-full object-cover"
          />
        ) : isImage ? (
          <ImageIcon className="w-6 h-6 text-[var(--color-muted)]" />
        ) : (
          <FileIcon className="w-6 h-6 text-[var(--color-muted)]" />
        )}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p
            className={cn(
              "text-sm font-medium truncate",
              file.status === "error"
                ? "text-[var(--color-error)]"
                : "text-[var(--color-foreground)]",
            )}
            title={file.name}
          >
            {file.name}
          </p>
          {file.status === "success" && (
            <CheckIcon className="w-4 h-4 flex-shrink-0 text-[var(--color-success)]" />
          )}
          {file.status === "error" && (
            <AlertIcon className="w-4 h-4 flex-shrink-0 text-[var(--color-error)]" />
          )}
        </div>
        <div className="flex items-center gap-2 mt-0.5">
          <span className="text-xs text-[var(--color-muted)]">{formatFileSize(file.size)}</span>
          {file.status === "uploading" && (
            <span className={cn("text-xs", statusColors[file.status])}>{file.progress}%</span>
          )}
          {file.error && (
            <span className="text-xs text-[var(--color-error)] truncate" title={file.error}>
              {file.error}
            </span>
          )}
        </div>

        {/* Progress Bar */}
        {file.status === "uploading" && (
          <div className="mt-2 h-1 bg-[var(--color-card)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--color-accent)] transition-all duration-200"
              style={{ width: `${file.progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Remove Button */}
      <button
        type="button"
        onClick={() => onRemove(file.id)}
        disabled={disabled || file.status === "uploading"}
        className={cn(
          "flex-shrink-0 p-1.5 rounded-[var(--radius-sm)]",
          "text-[var(--color-muted)] hover:text-[var(--color-error)]",
          "hover:bg-[var(--color-error)]/10",
          "transition-colors duration-150",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
        )}
        aria-label={`Remove ${file.name}`}
      >
        <TrashIcon className="w-4 h-4" />
      </button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * File upload component with drag-and-drop support, preview, and progress tracking.
 *
 * Features:
 * - Drag and drop zone
 * - File browser button
 * - Image thumbnails for image files
 * - Upload progress indicator
 * - Multiple file support (configurable)
 * - File size and type validation
 *
 * @example
 * ```tsx
 * <FileUpload
 *   name="avatar"
 *   label="Profile Picture"
 *   config={{
 *     maxSize: 5 * 1024 * 1024, // 5MB
 *     allowedExtensions: [".jpg", ".png", ".webp"],
 *     multiple: false,
 *   }}
 *   value={files}
 *   onChange={setFiles}
 * />
 * ```
 */
export function FileUpload({
  name,
  label,
  config = {},
  value = [],
  onChange,
  error,
  hint,
  disabled = false,
  required = false,
  className,
}: FileUploadProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [validationError, setValidationError] = useState<string | null>(null);

  const { multiple = false, maxSize, allowedExtensions, maxFiles } = config;

  // Build accept attribute from config
  const acceptAttribute = allowedExtensions
    ? allowedExtensions.map((ext) => (ext.startsWith(".") ? ext : `.${ext}`)).join(",")
    : undefined;

  // Handle files selection (from input or drop)
  const handleFiles = useCallback(
    async (files: FileList | null) => {
      if (!files || files.length === 0 || disabled) return;

      setValidationError(null);
      const fileArray = Array.from(files);
      const currentFiles = value || [];

      // Validate and process files
      const newFiles: UploadedFile[] = [];
      let existingCount = currentFiles.length;

      for (const file of fileArray) {
        // Single file mode: replace existing
        if (!multiple && existingCount > 0) {
          break;
        }

        // Validate file
        const validation = validateFile(file, config, existingCount);
        if (!validation.valid) {
          setValidationError(validation.error || "Invalid file");
          continue;
        }

        // Create file object
        const uploadedFile: UploadedFile = {
          id: generateFileId(),
          name: file.name,
          type: file.type,
          size: file.size,
          progress: 0,
          status: "uploading",
        };

        newFiles.push(uploadedFile);
        existingCount++;
      }

      if (newFiles.length === 0) return;

      // Update state with pending files
      const updatedFiles = multiple ? [...currentFiles, ...newFiles] : newFiles;
      onChange?.(updatedFiles);

      // Upload files
      for (let i = 0; i < newFiles.length; i++) {
        const uploadedFile = newFiles[i];
        const originalFile = fileArray[i];

        if (!uploadedFile || !originalFile) continue;

        try {
          const response = await api.uploadFile(originalFile, (progress) => {
            // Update progress
            onChange?.(
              updatedFiles.map((f) => (f.id === uploadedFile.id ? { ...f, progress } : f)),
            );
          });

          // Update with success
          onChange?.(
            updatedFiles.map((f) => {
              if (f.id === uploadedFile.id) {
                const successUpdate: UploadedFile = {
                  id: f.id,
                  name: f.name,
                  type: f.type,
                  size: f.size,
                  progress: 100,
                  status: "success",
                  url: response.url,
                  ...(response.thumbnail_url ? { thumbnailUrl: response.thumbnail_url } : {}),
                };
                return successUpdate;
              }
              return f;
            }),
          );
        } catch (err) {
          // Update with error
          const errorMessage = err instanceof Error ? err.message : "Upload failed";
          onChange?.(
            updatedFiles.map((f) => {
              if (f.id === uploadedFile.id) {
                const errorUpdate: UploadedFile = {
                  id: f.id,
                  name: f.name,
                  type: f.type,
                  size: f.size,
                  progress: f.progress,
                  status: "error",
                  error: errorMessage,
                };
                return errorUpdate;
              }
              return f;
            }),
          );
        }
      }
    },
    [config, disabled, multiple, onChange, value],
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

      if (!disabled) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [disabled, handleFiles],
  );

  // Input change handler
  const handleInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      handleFiles(e.target.files);
      // Reset input value to allow selecting the same file again
      if (inputRef.current) {
        inputRef.current.value = "";
      }
    },
    [handleFiles],
  );

  // Remove file handler
  const handleRemove = useCallback(
    (fileId: string) => {
      onChange?.(value.filter((f) => f.id !== fileId));
    },
    [onChange, value],
  );

  // Build hint text
  const hintText = hint || buildHintText(config);

  return (
    <div className={cn("space-y-2", className)}>
      {/* Label */}
      {label && (
        <label
          htmlFor={inputId}
          className={cn("block text-sm font-medium text-[var(--color-foreground)]", "mb-1.5")}
        >
          {label}
          {required && (
            <>
              <span className="ml-1 text-[var(--color-error)]" aria-hidden="true">
                *
              </span>
              <span className="sr-only">(required)</span>
            </>
          )}
        </label>
      )}

      {/* Drop Zone */}
      <div
        className={cn(
          "relative rounded-[var(--radius-md)] border-2 border-dashed",
          "transition-colors duration-150",
          isDragOver
            ? "border-[var(--color-accent)] bg-[var(--color-accent)]/5"
            : "border-[var(--color-border)] hover:border-[var(--color-muted)]",
          (error || validationError) && "border-[var(--color-error)]",
          disabled && "opacity-50 cursor-not-allowed",
        )}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div
          className={cn(
            "flex flex-col items-center justify-center py-8 px-4",
            "text-center",
          )}
        >
          <div
            className={cn(
              "w-12 h-12 mb-4 rounded-full",
              "bg-[var(--color-card-hover)] flex items-center justify-center",
              isDragOver && "bg-[var(--color-accent)]/10",
            )}
          >
            <UploadIcon
              className={cn(
                "w-6 h-6",
                isDragOver ? "text-[var(--color-accent)]" : "text-[var(--color-muted)]",
              )}
            />
          </div>

          <p className="text-sm text-[var(--color-foreground)] mb-1">
            {isDragOver ? "Drop files here" : "Drag and drop files here"}
          </p>
          <p className="text-xs text-[var(--color-muted)] mb-4">or</p>

          <Button
            type="button"
            variant="secondary"
            size="sm"
            disabled={disabled}
            onClick={() => inputRef.current?.click()}
          >
            Browse Files
          </Button>

          {/* Hidden file input */}
          <input
            ref={inputRef}
            id={inputId}
            name={name}
            type="file"
            accept={acceptAttribute}
            multiple={multiple}
            disabled={disabled}
            onChange={handleInputChange}
            className="sr-only"
            aria-describedby={
              error || validationError
                ? `${inputId}-error`
                : hintText
                  ? `${inputId}-hint`
                  : undefined
            }
          />
        </div>
      </div>

      {/* Hint Text */}
      {hintText && !error && !validationError && (
        <p id={`${inputId}-hint`} className="text-xs text-[var(--color-muted)]">
          {hintText}
        </p>
      )}

      {/* Error Message */}
      {(error || validationError) && (
        <p
          id={`${inputId}-error`}
          className="text-xs text-[var(--color-error)]"
          role="alert"
          aria-live="polite"
        >
          {error || validationError}
        </p>
      )}

      {/* File List */}
      {value.length > 0 && (
        <div className="space-y-2 mt-4">
          {value.map((file) => (
            <FileItem key={file.id} file={file} onRemove={handleRemove} disabled={disabled} />
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Build hint text from file field configuration.
 */
function buildHintText(config: FileFieldConfig): string {
  const parts: string[] = [];

  if (config.maxSize) {
    parts.push(`Max size: ${formatFileSize(config.maxSize)}`);
  }

  if (config.allowedExtensions && config.allowedExtensions.length > 0) {
    const extensions = config.allowedExtensions
      .map((ext) => (ext.startsWith(".") ? ext : `.${ext}`))
      .join(", ");
    parts.push(`Allowed types: ${extensions}`);
  }

  if (config.maxFiles && config.maxFiles > 1) {
    parts.push(`Max ${config.maxFiles} files`);
  }

  return parts.join(" | ");
}

FileUpload.displayName = "FileUpload";
