'use client';

import {
  useState,
  useCallback,
  useMemo,
  type ChangeEvent,
} from 'react';
import { Modal, ModalHeader, ModalBody, ModalFooter } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { useExportRecords, useExportSelected } from '@/hooks/useApi';
import { cn } from '@/lib/utils';
import type { ExportFormat } from '@/types';

// ============================================================================
// Types
// ============================================================================

/**
 * Column configuration for export selection.
 */
export interface ExportColumn {
  /** Unique column key/identifier */
  key: string;
  /** Display label for the column */
  label: string;
  /** Whether this column is selected by default */
  defaultSelected?: boolean;
}

/**
 * Props for the ExportDialog component.
 */
export interface ExportDialogProps {
  /** Model name/identifier for the export */
  model: string;
  /** Whether the dialog is open */
  isOpen: boolean;
  /** Callback when the dialog is closed */
  onClose: () => void;
  /** Optional set of selected record IDs for partial export */
  selectedIds?: Set<string | number>;
  /** Available columns for export selection */
  columns: ExportColumn[];
  /** Total number of records (for display purposes) */
  totalRecords?: number;
}

/**
 * Export scope - whether to export all records or only selected ones.
 */
type ExportScope = 'all' | 'selected';

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Triggers a browser download for a Blob.
 */
function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Generates a filename for the export.
 */
function generateFilename(model: string, format: ExportFormat, scope: ExportScope): string {
  const timestamp = new Date().toISOString().slice(0, 10);
  const scopeSuffix = scope === 'selected' ? '_selected' : '';
  return `${model}${scopeSuffix}_${timestamp}.${format}`;
}

// ============================================================================
// Sub-components
// ============================================================================

interface FormatOptionProps {
  format: ExportFormat;
  selected: boolean;
  onSelect: (format: ExportFormat) => void;
}

function FormatOption({ format, selected, onSelect }: FormatOptionProps) {
  const formatInfo: Record<ExportFormat, { label: string; description: string; icon: JSX.Element }> = {
    csv: {
      label: 'CSV',
      description: 'Comma-separated values, compatible with Excel and spreadsheet applications',
      icon: (
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="8" y1="13" x2="16" y2="13" />
          <line x1="8" y1="17" x2="16" y2="17" />
        </svg>
      ),
    },
    json: {
      label: 'JSON',
      description: 'JavaScript Object Notation, for programmatic access and APIs',
      icon: (
        <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <path d="M8 12h.01" />
          <path d="M12 12h.01" />
          <path d="M16 12h.01" />
        </svg>
      ),
    },
  };

  const { label, description, icon } = formatInfo[format];

  return (
    <button
      type="button"
      onClick={() => onSelect(format)}
      className={cn(
        'flex items-start gap-3 p-3 rounded-[var(--radius-md)]',
        'border transition-all duration-150',
        'text-left w-full',
        selected
          ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10'
          : 'border-[var(--color-border)] bg-[var(--color-card)] hover:border-[var(--color-muted)]'
      )}
      aria-pressed={selected}
    >
      <span
        className={cn(
          'flex-shrink-0 mt-0.5',
          selected ? 'text-[var(--color-primary)]' : 'text-[var(--color-muted)]'
        )}
      >
        {icon}
      </span>
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            'font-medium text-sm',
            selected ? 'text-[var(--color-foreground)]' : 'text-[var(--color-muted)]'
          )}
        >
          {label}
        </div>
        <div className="text-xs text-[var(--color-muted)] mt-0.5">{description}</div>
      </div>
      <span
        className={cn(
          'flex-shrink-0 w-4 h-4 rounded-full border-2 mt-0.5',
          'flex items-center justify-center transition-colors',
          selected
            ? 'border-[var(--color-primary)] bg-[var(--color-primary)]'
            : 'border-[var(--color-muted)]'
        )}
      >
        {selected && (
          <svg className="h-2.5 w-2.5 text-white" viewBox="0 0 12 12" fill="currentColor">
            <circle cx="6" cy="6" r="3" />
          </svg>
        )}
      </span>
    </button>
  );
}

interface ColumnCheckboxProps {
  column: ExportColumn;
  checked: boolean;
  onChange: (key: string, checked: boolean) => void;
}

function ColumnCheckbox({ column, checked, onChange }: ColumnCheckboxProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange(column.key, e.target.checked);
  };

  return (
    <label
      className={cn(
        'flex items-center gap-2 p-2 rounded-[var(--radius-sm)]',
        'cursor-pointer transition-colors',
        'hover:bg-[var(--color-card-hover)]',
        checked && 'bg-[var(--color-primary)]/5'
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={handleChange}
        className={cn(
          'w-4 h-4 rounded-[var(--radius-sm)]',
          'border border-[var(--color-border)]',
          'text-[var(--color-primary)]',
          'focus:ring-2 focus:ring-[var(--color-primary)] focus:ring-offset-0',
          'bg-[var(--color-card)]',
          'cursor-pointer'
        )}
      />
      <span
        className={cn(
          'text-sm truncate',
          checked ? 'text-[var(--color-foreground)]' : 'text-[var(--color-muted)]'
        )}
      >
        {column.label}
      </span>
    </label>
  );
}

interface ProgressIndicatorProps {
  status: 'idle' | 'exporting' | 'success' | 'error';
  message?: string;
}

function ProgressIndicator({ status, message }: ProgressIndicatorProps) {
  if (status === 'idle') return null;

  return (
    <div
      className={cn(
        'flex items-center gap-2 p-3 rounded-[var(--radius-md)]',
        'text-sm',
        status === 'exporting' && 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]',
        status === 'success' && 'bg-[var(--color-success)]/10 text-[var(--color-success)]',
        status === 'error' && 'bg-[var(--color-error)]/10 text-[var(--color-error)]'
      )}
    >
      {status === 'exporting' && (
        <svg
          className="h-4 w-4 animate-spin"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" />
          <path className="opacity-75" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" fill="currentColor" />
        </svg>
      )}
      {status === 'success' && (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      )}
      {status === 'error' && (
        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      )}
      <span>{message}</span>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Export dialog for downloading model records in various formats.
 * Supports exporting all records or selected records with column selection.
 */
export function ExportDialog({
  model,
  isOpen,
  onClose,
  selectedIds,
  columns,
  totalRecords,
}: ExportDialogProps) {
  // State
  const [format, setFormat] = useState<ExportFormat>('csv');
  const [scope, setScope] = useState<ExportScope>(selectedIds?.size ? 'selected' : 'all');
  const [selectedColumns, setSelectedColumns] = useState<Set<string>>(() => {
    const initial = new Set<string>();
    for (const col of columns) {
      if (col.defaultSelected !== false) {
        initial.add(col.key);
      }
    }
    return initial;
  });
  const [status, setStatus] = useState<'idle' | 'exporting' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // Mutations
  const exportAll = useExportRecords(model);
  const exportSelected = useExportSelected(model);

  // Computed values
  const hasSelectedIds = selectedIds && selectedIds.size > 0;
  const recordCount = scope === 'selected' && hasSelectedIds ? selectedIds.size : totalRecords;
  const allColumnsSelected = selectedColumns.size === columns.length;
  const noColumnsSelected = selectedColumns.size === 0;

  // Handlers
  const handleColumnChange = useCallback((key: string, checked: boolean) => {
    setSelectedColumns((prev) => {
      const next = new Set(prev);
      if (checked) {
        next.add(key);
      } else {
        next.delete(key);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedColumns(new Set(columns.map((c) => c.key)));
  }, [columns]);

  const handleDeselectAll = useCallback(() => {
    setSelectedColumns(new Set());
  }, []);

  const handleExport = useCallback(async () => {
    if (noColumnsSelected) return;

    setStatus('exporting');
    setErrorMessage('');

    try {
      let blob: Blob;

      if (scope === 'selected' && hasSelectedIds) {
        blob = await exportSelected.mutateAsync({
          ids: Array.from(selectedIds),
          format,
        });
      } else {
        blob = await exportAll.mutateAsync({ format });
      }

      const filename = generateFilename(model, format, scope);
      downloadBlob(blob, filename);

      setStatus('success');

      // Auto-close after success
      setTimeout(() => {
        onClose();
        setStatus('idle');
      }, 1500);
    } catch (error) {
      setStatus('error');
      setErrorMessage(error instanceof Error ? error.message : 'Export failed. Please try again.');
    }
  }, [
    format,
    scope,
    selectedIds,
    hasSelectedIds,
    noColumnsSelected,
    model,
    exportAll,
    exportSelected,
    onClose,
  ]);

  const handleClose = useCallback(() => {
    if (status !== 'exporting') {
      onClose();
      setStatus('idle');
      setErrorMessage('');
    }
  }, [status, onClose]);

  // Status message
  const statusMessage = useMemo(() => {
    switch (status) {
      case 'exporting':
        return 'Preparing export...';
      case 'success':
        return 'Export complete! Download started.';
      case 'error':
        return errorMessage;
      default:
        return '';
    }
  }, [status, errorMessage]);

  const isExporting = status === 'exporting';

  return (
    <Modal isOpen={isOpen} onClose={handleClose} closeOnOverlayClick={!isExporting}>
      {isExporting ? (
        <ModalHeader>Export Records</ModalHeader>
      ) : (
        <ModalHeader onClose={handleClose}>Export Records</ModalHeader>
      )}

      <ModalBody className="space-y-5">
        {/* Export Scope Selection (only show if there are selected records) */}
        {hasSelectedIds && (
          <div>
            <label className="block text-sm font-medium text-[var(--color-foreground)] mb-2">
              Export Scope
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setScope('all')}
                disabled={isExporting}
                className={cn(
                  'flex-1 px-3 py-2 text-sm rounded-[var(--radius-md)]',
                  'border transition-colors',
                  scope === 'all'
                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-foreground)]'
                    : 'border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-muted)]',
                  isExporting && 'opacity-50 cursor-not-allowed'
                )}
              >
                All records{totalRecords !== undefined && ` (${totalRecords})`}
              </button>
              <button
                type="button"
                onClick={() => setScope('selected')}
                disabled={isExporting}
                className={cn(
                  'flex-1 px-3 py-2 text-sm rounded-[var(--radius-md)]',
                  'border transition-colors',
                  scope === 'selected'
                    ? 'border-[var(--color-primary)] bg-[var(--color-primary)]/10 text-[var(--color-foreground)]'
                    : 'border-[var(--color-border)] text-[var(--color-muted)] hover:border-[var(--color-muted)]',
                  isExporting && 'opacity-50 cursor-not-allowed'
                )}
              >
                Selected only ({selectedIds.size})
              </button>
            </div>
          </div>
        )}

        {/* Format Selection */}
        <div>
          <label className="block text-sm font-medium text-[var(--color-foreground)] mb-2">
            Export Format
          </label>
          <div className="grid grid-cols-2 gap-3">
            <FormatOption format="csv" selected={format === 'csv'} onSelect={setFormat} />
            <FormatOption format="json" selected={format === 'json'} onSelect={setFormat} />
          </div>
        </div>

        {/* Column Selection */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-[var(--color-foreground)]">
              Columns to Export
            </label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleSelectAll}
                disabled={allColumnsSelected || isExporting}
                className={cn(
                  'text-xs text-[var(--color-accent)] hover:text-[var(--color-accent)]/80',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                Select All
              </button>
              <span className="text-xs text-[var(--color-muted)]">|</span>
              <button
                type="button"
                onClick={handleDeselectAll}
                disabled={noColumnsSelected || isExporting}
                className={cn(
                  'text-xs text-[var(--color-accent)] hover:text-[var(--color-accent)]/80',
                  'disabled:opacity-50 disabled:cursor-not-allowed'
                )}
              >
                Deselect All
              </button>
            </div>
          </div>
          <div
            className={cn(
              'grid grid-cols-2 gap-1 p-2',
              'max-h-48 overflow-y-auto',
              'border border-[var(--color-border)] rounded-[var(--radius-md)]',
              'bg-[var(--color-background)]'
            )}
          >
            {columns.map((column) => (
              <ColumnCheckbox
                key={column.key}
                column={column}
                checked={selectedColumns.has(column.key)}
                onChange={handleColumnChange}
              />
            ))}
          </div>
          <p className="text-xs text-[var(--color-muted)] mt-1">
            {selectedColumns.size} of {columns.length} columns selected
          </p>
        </div>

        {/* Progress/Status Indicator */}
        <ProgressIndicator status={status} message={statusMessage} />
      </ModalBody>

      <ModalFooter>
        <Button variant="secondary" onClick={handleClose} disabled={isExporting}>
          Cancel
        </Button>
        <Button
          variant="primary"
          onClick={handleExport}
          loading={isExporting}
          disabled={noColumnsSelected || isExporting}
          leftIcon={
            !isExporting ? (
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7 10 12 15 17 10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
            ) : undefined
          }
        >
          Export {recordCount !== undefined && `${recordCount} `}
          {recordCount === 1 ? 'Record' : 'Records'}
        </Button>
      </ModalFooter>
    </Modal>
  );
}

// ============================================================================
// ExportButton Component
// ============================================================================

/**
 * Props for the ExportButton component.
 */
export interface ExportButtonProps {
  /** Model name/identifier */
  model: string;
  /** Available columns for export */
  columns: ExportColumn[];
  /** Optional set of selected record IDs */
  selectedIds?: Set<string | number>;
  /** Total number of records */
  totalRecords?: number;
  /** Button variant */
  variant?: 'default' | 'icon';
  /** Additional CSS classes */
  className?: string;
}

/**
 * Button component that opens the ExportDialog when clicked.
 */
export function ExportButton({
  model,
  columns,
  selectedIds,
  totalRecords,
  variant = 'default',
  className,
}: ExportButtonProps) {
  const [isOpen, setIsOpen] = useState(false);

  const handleOpen = useCallback(() => {
    setIsOpen(true);
  }, []);

  const handleClose = useCallback(() => {
    setIsOpen(false);
  }, []);

  const downloadIcon = (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );

  return (
    <>
      {variant === 'icon' ? (
        <button
          type="button"
          onClick={handleOpen}
          className={cn(
            'inline-flex items-center justify-center',
            'w-9 h-9 rounded-[var(--radius-md)]',
            'text-[var(--color-muted)] hover:text-[var(--color-foreground)]',
            'bg-[var(--color-card)] hover:bg-[var(--color-card-hover)]',
            'border border-[var(--color-border)] hover:border-[var(--color-muted)]',
            'transition-colors duration-150',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]',
            className
          )}
          aria-label="Export records"
          title="Export records"
        >
          {downloadIcon}
        </button>
      ) : (
        <Button
          variant="secondary"
          onClick={handleOpen}
          leftIcon={downloadIcon}
          className={className}
        >
          Export
        </Button>
      )}

      <ExportDialog
        model={model}
        isOpen={isOpen}
        onClose={handleClose}
        columns={columns}
        {...(selectedIds !== undefined && { selectedIds })}
        {...(totalRecords !== undefined && { totalRecords })}
      />
    </>
  );
}
