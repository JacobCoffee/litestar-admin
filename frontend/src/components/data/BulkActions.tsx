"use client";

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  type KeyboardEvent,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { useBulkDelete, useBulkAction, useExportSelected } from "@/hooks/useApi";
import type { ExportFormat } from "@/types";

// ============================================================================
// Types
// ============================================================================

/**
 * Result returned after a bulk action completes.
 */
export interface BulkActionResult {
  /** Whether the action completed successfully */
  success: boolean;
  /** Number of records affected by the action */
  affected: number;
  /** Error messages if any operations failed */
  errors?: string[];
}

/**
 * Configuration for a custom bulk action.
 */
export interface BulkAction {
  /** Unique identifier for the action */
  key: string;
  /** Display label for the action */
  label: string;
  /** Icon to display alongside the label */
  icon?: ReactNode;
  /** Visual variant for the action button */
  variant?: "default" | "danger";
  /** Title for confirmation dialog */
  confirmTitle?: string;
  /** Message for confirmation dialog */
  confirmMessage?: string;
  /** Additional parameters to pass with the action */
  params?: Record<string, unknown>;
}

/**
 * Props for the BulkActions component.
 */
export interface BulkActionsProps {
  /** Model identifier for API calls */
  model: string;
  /** Set of selected record IDs */
  selectedIds: Set<string | number>;
  /** Total number of selected items */
  totalSelected: number;
  /** Callback to clear current selection */
  onClearSelection: () => void;
  /** Custom actions specific to this model */
  customActions?: BulkAction[];
  /** Callback fired when an action completes */
  onActionComplete?: (action: string, result: BulkActionResult) => void;
  /** Additional CSS classes */
  className?: string;
  /** Position of the toolbar */
  position?: "inline" | "floating";
  /** Available export formats */
  exportFormats?: ExportFormat[];
}

// ============================================================================
// Icons
// ============================================================================

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
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

function DownloadIcon({ className }: { className?: string }) {
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
      <polyline points="7,10 12,15 17,10" />
      <line x1="12" y1="15" x2="12" y2="3" />
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

function AlertTriangleIcon({ className }: { className?: string }) {
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
      <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function CheckCircleIcon({ className }: { className?: string }) {
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
      <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
      <polyline points="22,4 12,14.01 9,11.01" />
    </svg>
  );
}

function RefreshIcon({ className }: { className?: string }) {
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
      <polyline points="23,4 23,10 17,10" />
      <polyline points="1,20 1,14 7,14" />
      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15" />
    </svg>
  );
}

function MoreHorizontalIcon({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="1" />
      <circle cx="19" cy="12" r="1" />
      <circle cx="5" cy="12" r="1" />
    </svg>
  );
}

// ============================================================================
// Progress Indicator
// ============================================================================

interface ProgressIndicatorProps {
  label: string;
  isComplete?: boolean;
  hasError?: boolean;
}

function ProgressIndicator({ label, isComplete, hasError }: ProgressIndicatorProps) {
  return (
    <div className="flex items-center gap-3">
      {!isComplete && !hasError && (
        <div className="relative h-5 w-5">
          <div
            className={cn(
              "absolute inset-0 rounded-full",
              "border-2 border-[var(--color-primary)]/20",
            )}
          />
          <div
            className={cn(
              "absolute inset-0 rounded-full",
              "border-2 border-[var(--color-primary)] border-t-transparent",
              "animate-spin",
            )}
          />
        </div>
      )}
      {isComplete && <CheckCircleIcon className="h-5 w-5 text-[var(--color-success)]" />}
      {hasError && <AlertTriangleIcon className="h-5 w-5 text-[var(--color-error)]" />}
      <span className="text-sm text-[var(--color-foreground)]">{label}</span>
    </div>
  );
}

// ============================================================================
// Action Dropdown
// ============================================================================

interface ActionDropdownProps {
  actions: BulkAction[];
  onSelectAction: (action: BulkAction) => void;
  disabled?: boolean;
}

function ActionDropdown({ actions, onSelectAction, disabled }: ActionDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = useCallback((e: KeyboardEvent<HTMLButtonElement>) => {
    if (e.key === "Escape") {
      setIsOpen(false);
    }
  }, []);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  if (actions.length === 0) return null;

  return (
    <div ref={dropdownRef} className="relative">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <MoreHorizontalIcon className="h-4 w-4" />
        <span className="hidden sm:inline">More Actions</span>
        <ChevronDownIcon
          className={cn("h-4 w-4 transition-transform duration-150", isOpen && "rotate-180")}
        />
      </Button>

      {isOpen && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-full z-50 mt-1",
            "min-w-[180px] py-1",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "animate-[scaleIn_100ms_ease-out]",
          )}
        >
          {actions.map((action) => (
            <button
              key={action.key}
              type="button"
              role="menuitem"
              onClick={() => {
                onSelectAction(action);
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-4 py-2",
                "flex items-center gap-2",
                "text-sm text-left",
                "transition-colors duration-150",
                "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
                action.variant === "danger"
                  ? "text-[var(--color-error)] hover:bg-[var(--color-error)]/10"
                  : "text-[var(--color-foreground)] hover:bg-[var(--color-card-hover)]",
              )}
            >
              {action.icon && <span className="h-4 w-4">{action.icon}</span>}
              {action.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Export Dropdown
// ============================================================================

interface ExportDropdownProps {
  formats: ExportFormat[];
  onExport: (format: ExportFormat) => void;
  disabled?: boolean;
  isExporting?: boolean;
}

function ExportDropdown({ formats, onExport, disabled, isExporting }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;

    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const formatLabels: Record<ExportFormat, string> = {
    csv: "Export as CSV",
    json: "Export as JSON",
  };

  return (
    <div ref={dropdownRef} className="relative">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || isExporting}
        loading={isExporting === true}
        leftIcon={isExporting ? undefined : <DownloadIcon className="h-4 w-4" />}
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <span className="hidden sm:inline">Export</span>
        <ChevronDownIcon
          className={cn(
            "h-4 w-4 transition-transform duration-150 sm:block hidden",
            isOpen && "rotate-180",
          )}
        />
      </Button>

      {isOpen && !isExporting && (
        <div
          role="menu"
          className={cn(
            "absolute right-0 top-full z-50 mt-1",
            "min-w-[160px] py-1",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "animate-[scaleIn_100ms_ease-out]",
          )}
        >
          {formats.map((format) => (
            <button
              key={format}
              type="button"
              role="menuitem"
              onClick={() => {
                onExport(format);
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-4 py-2",
                "text-sm text-left",
                "text-[var(--color-foreground)]",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
                "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
              )}
            >
              {formatLabels[format]}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Confirmation Modal
// ============================================================================

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel: string;
  isLoading: boolean;
  variant?: "default" | "danger";
  progress?: {
    label: string;
    isComplete: boolean;
    hasError: boolean;
    errorMessage?: string;
  };
  onRetry?: () => void;
}

function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel,
  isLoading,
  variant = "default",
  progress,
  onRetry,
}: ConfirmationModalProps) {
  const handleClose = isLoading ? undefined : onClose;

  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={!isLoading}>
      {handleClose ? (
        <ModalHeader onClose={handleClose}>{title}</ModalHeader>
      ) : (
        <ModalHeader>{title}</ModalHeader>
      )}
      <ModalBody>
        {!progress ? (
          <>
            <div className="flex gap-4">
              {variant === "danger" && (
                <div
                  className={cn(
                    "flex-shrink-0",
                    "h-10 w-10 rounded-full",
                    "bg-[var(--color-error)]/10",
                    "flex items-center justify-center",
                  )}
                >
                  <AlertTriangleIcon className="h-5 w-5 text-[var(--color-error)]" />
                </div>
              )}
              <div className="flex-1">
                <p className="text-sm text-[var(--color-foreground)]">{message}</p>
                {variant === "danger" && (
                  <p className="text-sm text-[var(--color-muted)] mt-2">
                    This action cannot be undone.
                  </p>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="space-y-4">
            <ProgressIndicator
              label={progress.label}
              isComplete={progress.isComplete}
              hasError={progress.hasError}
            />
            {progress.hasError && progress.errorMessage && (
              <div
                className={cn(
                  "px-4 py-3 rounded-[var(--radius-md)]",
                  "bg-[var(--color-error)]/10",
                  "border border-[var(--color-error)]/20",
                )}
              >
                <p className="text-sm text-[var(--color-error)]">{progress.errorMessage}</p>
              </div>
            )}
          </div>
        )}
      </ModalBody>
      <ModalFooter>
        {!progress ? (
          <>
            <Button variant="secondary" onClick={onClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button
              variant={variant === "danger" ? "danger" : "primary"}
              onClick={onConfirm}
              loading={isLoading}
            >
              {confirmLabel}
            </Button>
          </>
        ) : progress.hasError ? (
          <>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            {onRetry && (
              <Button
                variant="primary"
                onClick={onRetry}
                leftIcon={<RefreshIcon className="h-4 w-4" />}
              >
                Retry
              </Button>
            )}
          </>
        ) : progress.isComplete ? (
          <Button variant="primary" onClick={onClose}>
            Done
          </Button>
        ) : null}
      </ModalFooter>
    </Modal>
  );
}

// ============================================================================
// Toolbar Content
// ============================================================================

interface ToolbarContentProps {
  totalSelected: number;
  onClearSelection: () => void;
  onDelete: () => void;
  onExport: (format: ExportFormat) => void;
  customActions: BulkAction[];
  onCustomAction: (action: BulkAction) => void;
  isDeleting: boolean;
  isExporting: boolean;
  exportFormats: ExportFormat[];
}

function ToolbarContent({
  totalSelected,
  onClearSelection,
  onDelete,
  onExport,
  customActions,
  onCustomAction,
  isDeleting,
  isExporting,
  exportFormats,
}: ToolbarContentProps) {
  const isDisabled = isDeleting || isExporting;

  return (
    <div className="flex items-center justify-between gap-4 w-full">
      {/* Selection info */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-[var(--color-foreground)]">
          {totalSelected} {totalSelected === 1 ? "item" : "items"} selected
        </span>
        <button
          type="button"
          onClick={onClearSelection}
          disabled={isDisabled}
          className={cn(
            "text-sm text-[var(--color-muted)]",
            "hover:text-[var(--color-foreground)]",
            "transition-colors duration-150",
            "disabled:opacity-50 disabled:cursor-not-allowed",
          )}
        >
          Clear selection
        </button>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Export dropdown */}
        <ExportDropdown
          formats={exportFormats}
          onExport={onExport}
          disabled={isDisabled}
          isExporting={isExporting}
        />

        {/* Custom actions dropdown */}
        {customActions.length > 0 && (
          <ActionDropdown
            actions={customActions}
            onSelectAction={onCustomAction}
            disabled={isDisabled}
          />
        )}

        {/* Delete button */}
        <Button
          variant="danger"
          size="sm"
          onClick={onDelete}
          disabled={isDisabled}
          loading={isDeleting}
          leftIcon={!isDeleting ? <TrashIcon className="h-4 w-4" /> : undefined}
        >
          <span className="hidden sm:inline">Delete Selected</span>
          <span className="sm:hidden">Delete</span>
        </Button>
      </div>
    </div>
  );
}

// ============================================================================
// Floating Toolbar
// ============================================================================

interface FloatingToolbarProps {
  children: ReactNode;
  isVisible: boolean;
}

function FloatingToolbar({ children, isVisible }: FloatingToolbarProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || typeof document === "undefined") return null;

  return createPortal(
    <div
      className={cn(
        "fixed left-1/2 bottom-6 z-50",
        "-translate-x-1/2",
        "transition-all duration-300 ease-out",
        isVisible ? "opacity-100 translate-y-0" : "opacity-0 translate-y-4 pointer-events-none",
      )}
    >
      <div
        className={cn(
          "px-4 py-3",
          "bg-[var(--color-card)]",
          "border border-[var(--color-border)]",
          "rounded-[var(--radius-lg)]",
          "shadow-2xl shadow-black/40",
          "backdrop-blur-sm",
          "min-w-[320px] max-w-[90vw]",
        )}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function BulkActions({
  model,
  selectedIds,
  totalSelected,
  onClearSelection,
  customActions = [],
  onActionComplete,
  className,
  position = "inline",
  exportFormats = ["csv", "json"],
}: BulkActionsProps) {
  // Modal state
  const [confirmModal, setConfirmModal] = useState<{
    isOpen: boolean;
    type: "delete" | "custom";
    action?: BulkAction;
  }>({
    isOpen: false,
    type: "delete",
  });

  // Progress state
  const [progress, setProgress] = useState<{
    label: string;
    isComplete: boolean;
    hasError: boolean;
    errorMessage?: string;
  } | null>(null);

  // Convert selectedIds to array for API calls
  const selectedIdsArray = Array.from(selectedIds);

  // Bulk delete mutation
  const bulkDelete = useBulkDelete(model, {
    onSuccess: (response) => {
      setProgress({
        label: `Successfully deleted ${response.deleted} records`,
        isComplete: true,
        hasError: false,
      });
      onActionComplete?.("delete", {
        success: true,
        affected: response.deleted,
      });
    },
    onError: (error) => {
      setProgress({
        label: "Delete operation failed",
        isComplete: false,
        hasError: true,
        errorMessage: error.message || "An unexpected error occurred",
      });
      onActionComplete?.("delete", {
        success: false,
        affected: 0,
        errors: [error.message || "Delete failed"],
      });
    },
  });

  // Bulk action mutation (for custom actions)
  const bulkAction = useBulkAction(model, confirmModal.action?.key ?? "", {
    onSuccess: (response) => {
      setProgress({
        label: `Successfully completed action on ${response.affected} records`,
        isComplete: true,
        hasError: false,
      });
      onActionComplete?.(confirmModal.action?.key ?? "", {
        success: true,
        affected: response.affected,
      });
    },
    onError: (error) => {
      setProgress({
        label: "Action failed",
        isComplete: false,
        hasError: true,
        errorMessage: error.message || "An unexpected error occurred",
      });
      onActionComplete?.(confirmModal.action?.key ?? "", {
        success: false,
        affected: 0,
        errors: [error.message || "Action failed"],
      });
    },
  });

  // Export mutation
  const exportSelected = useExportSelected(model, {
    onSuccess: (blob) => {
      // Trigger file download
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${model}-export-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      onActionComplete?.("export", {
        success: true,
        affected: selectedIdsArray.length,
      });
    },
    onError: (error) => {
      onActionComplete?.("export", {
        success: false,
        affected: 0,
        errors: [error.message || "Export failed"],
      });
    },
  });

  // Handlers
  const handleOpenDeleteModal = useCallback(() => {
    setProgress(null);
    setConfirmModal({ isOpen: true, type: "delete" });
  }, []);

  const handleOpenCustomActionModal = useCallback((action: BulkAction) => {
    setProgress(null);
    setConfirmModal({ isOpen: true, type: "custom", action });
  }, []);

  const handleCloseModal = useCallback(() => {
    setConfirmModal({ isOpen: false, type: "delete" });
    setProgress(null);
    // Clear selection if action was successful
    if (progress?.isComplete) {
      onClearSelection();
    }
  }, [progress, onClearSelection]);

  const handleConfirmDelete = useCallback(() => {
    setProgress({
      label: `Deleting ${totalSelected} records...`,
      isComplete: false,
      hasError: false,
    });
    bulkDelete.mutate({ ids: selectedIdsArray });
  }, [bulkDelete, selectedIdsArray, totalSelected]);

  const handleConfirmCustomAction = useCallback(() => {
    if (!confirmModal.action) return;

    setProgress({
      label: `Executing ${confirmModal.action.label}...`,
      isComplete: false,
      hasError: false,
    });
    const mutationPayload: { ids: readonly (string | number)[]; params?: Record<string, unknown> } =
      {
        ids: selectedIdsArray,
      };
    if (confirmModal.action.params) {
      mutationPayload.params = confirmModal.action.params;
    }
    bulkAction.mutate(mutationPayload);
  }, [bulkAction, confirmModal.action, selectedIdsArray]);

  const handleExport = useCallback(
    (format: ExportFormat) => {
      exportSelected.mutate({ ids: selectedIdsArray, format });
    },
    [exportSelected, selectedIdsArray],
  );

  const handleRetry = useCallback(() => {
    if (confirmModal.type === "delete") {
      handleConfirmDelete();
    } else {
      handleConfirmCustomAction();
    }
  }, [confirmModal.type, handleConfirmDelete, handleConfirmCustomAction]);

  // Don't render if nothing is selected
  if (totalSelected === 0) return null;

  const toolbarContent = (
    <ToolbarContent
      totalSelected={totalSelected}
      onClearSelection={onClearSelection}
      onDelete={handleOpenDeleteModal}
      onExport={handleExport}
      customActions={customActions}
      onCustomAction={handleOpenCustomActionModal}
      isDeleting={bulkDelete.isPending}
      isExporting={exportSelected.isPending}
      exportFormats={exportFormats}
    />
  );

  // Confirmation modal content
  const getModalContent = () => {
    if (confirmModal.type === "delete") {
      return {
        title: confirmModal.action?.confirmTitle ?? `Delete ${totalSelected} Records`,
        message:
          confirmModal.action?.confirmMessage ??
          `Are you sure you want to delete ${totalSelected} selected ${
            totalSelected === 1 ? "record" : "records"
          }? All associated data will be permanently removed.`,
        confirmLabel: `Delete ${totalSelected} ${totalSelected === 1 ? "Record" : "Records"}`,
        variant: "danger" as const,
      };
    }

    // Custom action
    return {
      title: confirmModal.action?.confirmTitle ?? `Confirm ${confirmModal.action?.label}`,
      message:
        confirmModal.action?.confirmMessage ??
        `Are you sure you want to execute "${confirmModal.action?.label}" on ${totalSelected} selected ${
          totalSelected === 1 ? "record" : "records"
        }?`,
      confirmLabel: confirmModal.action?.label ?? "Confirm",
      variant: confirmModal.action?.variant ?? ("default" as const),
    };
  };

  const modalContent = getModalContent();

  return (
    <>
      {/* Toolbar */}
      {position === "floating" ? (
        <FloatingToolbar isVisible={totalSelected > 0}>{toolbarContent}</FloatingToolbar>
      ) : (
        <div
          className={cn(
            "flex items-center justify-between gap-4",
            "px-4 py-3",
            "bg-[var(--color-primary)]/5",
            "border border-[var(--color-primary)]/20",
            "rounded-[var(--radius-lg)]",
            "animate-[slideIn_200ms_ease-out]",
            className,
          )}
        >
          {toolbarContent}
        </div>
      )}

      {/* Confirmation Modal */}
      <ConfirmationModal
        isOpen={confirmModal.isOpen}
        onClose={handleCloseModal}
        onConfirm={confirmModal.type === "delete" ? handleConfirmDelete : handleConfirmCustomAction}
        title={modalContent.title}
        message={modalContent.message}
        confirmLabel={modalContent.confirmLabel}
        isLoading={bulkDelete.isPending || bulkAction.isPending}
        variant={modalContent.variant}
        {...(progress ? { progress } : {})}
        {...(progress?.hasError ? { onRetry: handleRetry } : {})}
      />
    </>
  );
}

BulkActions.displayName = "BulkActions";

// ============================================================================
// Hook for managing bulk selection
// ============================================================================

export interface UseBulkSelectionOptions<T> {
  /** Function to get unique ID from a record */
  getRowId?: (row: T) => string | number;
}

export interface UseBulkSelectionReturn<T> {
  /** Currently selected IDs */
  selectedIds: Set<string | number>;
  /** Number of selected items */
  totalSelected: number;
  /** Check if a specific row is selected */
  isSelected: (row: T) => boolean;
  /** Toggle selection for a single row */
  toggleSelection: (row: T) => void;
  /** Select multiple rows */
  selectMultiple: (rows: T[]) => void;
  /** Clear all selections */
  clearSelection: () => void;
  /** Select all provided rows */
  selectAll: (rows: T[]) => void;
  /** Set selected IDs directly */
  setSelectedIds: (ids: Set<string | number>) => void;
}

export function useBulkSelection<T>({
  getRowId = (row: T) => (row as { id?: string | number }).id ?? 0,
}: UseBulkSelectionOptions<T> = {}): UseBulkSelectionReturn<T> {
  const [selectedIds, setSelectedIds] = useState<Set<string | number>>(new Set());

  const isSelected = useCallback(
    (row: T) => selectedIds.has(getRowId(row)),
    [selectedIds, getRowId],
  );

  const toggleSelection = useCallback(
    (row: T) => {
      const id = getRowId(row);
      setSelectedIds((prev) => {
        const next = new Set(prev);
        if (next.has(id)) {
          next.delete(id);
        } else {
          next.add(id);
        }
        return next;
      });
    },
    [getRowId],
  );

  const selectMultiple = useCallback(
    (rows: T[]) => {
      setSelectedIds((prev) => {
        const next = new Set(prev);
        rows.forEach((row) => next.add(getRowId(row)));
        return next;
      });
    },
    [getRowId],
  );

  const clearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  const selectAll = useCallback(
    (rows: T[]) => {
      setSelectedIds(new Set(rows.map(getRowId)));
    },
    [getRowId],
  );

  return {
    selectedIds,
    totalSelected: selectedIds.size,
    isSelected,
    toggleSelection,
    selectMultiple,
    clearSelection,
    selectAll,
    setSelectedIds,
  };
}
