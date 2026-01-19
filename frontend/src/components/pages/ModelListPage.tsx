"use client";

import { useState, useCallback, useMemo, useEffect, type ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { DataTable, useDataTable, type Column } from "@/components/data/DataTable";
import {
  SearchFilter,
  type FilterableColumn,
  type FilterState,
} from "@/components/data/SearchFilter";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Loading";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import {
  useRecordsPaginated,
  useModelSchema,
  useDeleteRecord,
  useBulkDelete,
  useExportRecords,
  useExportSelected,
} from "@/hooks/useApi";
import { cn, toTitleCase, formatDate } from "@/lib/utils";
import type {
  ModelRecord,
  ModelSchema,
  SchemaProperty,
  ListQueryParams,
  ExportFormat,
} from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface ModelListPageProps {
  model: string;
}

// ============================================================================
// Icons
// ============================================================================

const PlusIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
  </svg>
);

const EyeIcon = ({ className }: { className?: string }) => (
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
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const EditIcon = ({ className }: { className?: string }) => (
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
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
  </svg>
);

const TrashIcon = ({ className }: { className?: string }) => (
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

const DownloadIcon = ({ className }: { className?: string }) => (
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

const AlertCircleIcon = ({ className }: { className?: string }) => (
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
    <path d="M12 8v4M12 16h.01" />
  </svg>
);

const TableIcon = ({ className }: { className?: string }) => (
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
    <line x1="3" y1="9" x2="21" y2="9" />
    <line x1="3" y1="15" x2="21" y2="15" />
    <line x1="9" y1="3" x2="9" y2="21" />
    <line x1="15" y1="3" x2="15" y2="21" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatModelName(model: string): string {
  return toTitleCase(model.replace(/[-_]/g, " "));
}

function getFilterableType(property: SchemaProperty): FilterableColumn["type"] | null {
  if (property.enum) {
    return "enum";
  }

  switch (property.type) {
    case "string":
      if (property.format === "date") return "date";
      if (property.format === "date-time") return "datetime";
      return "string";
    case "integer":
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    default:
      return null;
  }
}

function generateColumnsFromSchema(
  schema: ModelSchema,
  onView: (record: ModelRecord) => void,
  onEdit: (record: ModelRecord) => void,
  onDelete: (record: ModelRecord) => void,
): Column<ModelRecord>[] {
  const columns: Column<ModelRecord>[] = [];
  const properties = Object.entries(schema.properties);

  const requiredSet = new Set(schema.required);
  properties.sort(([aName], [bName]) => {
    const aRequired = requiredSet.has(aName);
    const bRequired = requiredSet.has(bName);
    if (aRequired && !bRequired) return -1;
    if (!aRequired && bRequired) return 1;
    return aName.localeCompare(bName);
  });

  const visibleCount = Math.min(properties.length, 6);

  for (let i = 0; i < properties.length; i++) {
    const [name, property] = properties[i] as [string, SchemaProperty];

    if (name.endsWith("_id") && properties.some(([n]) => n === name.replace(/_id$/, ""))) {
      continue;
    }

    if (property.type === "object" || property.type === "array") {
      continue;
    }

    const column: Column<ModelRecord> = {
      key: name,
      header: property.title || formatModelName(name),
      sortable: true,
      priority: i < visibleCount ? 1 : i < visibleCount + 3 ? 2 : 3,
      render: (value: unknown) => renderCellValue(value, property),
    };

    if (name === "id" || name === "_id" || name === "pk") {
      column.width = "80px";
    }

    columns.push(column);
  }

  columns.push({
    key: "_actions",
    header: "Actions",
    sortable: false,
    width: "140px",
    align: "right",
    priority: 1,
    render: (_value: unknown, row: ModelRecord) => (
      <ActionsCell record={row} onView={onView} onEdit={onEdit} onDelete={onDelete} />
    ),
  });

  return columns;
}

function renderCellValue(value: unknown, property: SchemaProperty): ReactNode {
  if (value === null || value === undefined) {
    return <span className="text-[var(--color-muted)]">-</span>;
  }

  if (typeof value === "boolean") {
    return (
      <span
        className={cn(
          "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
          value
            ? "bg-[var(--color-success)]/10 text-[var(--color-success)]"
            : "bg-[var(--color-muted)]/10 text-[var(--color-muted)]",
        )}
      >
        {value ? "Yes" : "No"}
      </span>
    );
  }

  if (property.format === "date" && typeof value === "string") {
    return formatDate(value);
  }

  if (property.format === "date-time" && typeof value === "string") {
    return formatDate(value, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (property.format === "email" && typeof value === "string") {
    return (
      <a
        href={`mailto:${value}`}
        className="text-[var(--color-accent)] hover:underline"
        onClick={(e) => e.stopPropagation()}
      >
        {value}
      </a>
    );
  }

  if (property.format === "uri" && typeof value === "string") {
    return (
      <a
        href={value}
        target="_blank"
        rel="noopener noreferrer"
        className="text-[var(--color-accent)] hover:underline truncate max-w-[200px] block"
        onClick={(e) => e.stopPropagation()}
      >
        {value}
      </a>
    );
  }

  if (property.enum && typeof value === "string") {
    return (
      <span
        className={cn(
          "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
          "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
        )}
      >
        {value}
      </span>
    );
  }

  const stringValue = String(value);
  if (stringValue.length > 50) {
    return <span title={stringValue}>{stringValue.slice(0, 50)}...</span>;
  }

  return stringValue;
}

function generateFilterableColumns(schema: ModelSchema): FilterableColumn[] {
  const columns: FilterableColumn[] = [];

  for (const [name, property] of Object.entries(schema.properties)) {
    const filterType = getFilterableType(property);
    if (!filterType) continue;

    if (property.type === "object" || property.type === "array") continue;

    const enumValues = property.enum?.map(String);
    const column: FilterableColumn = {
      key: name,
      label: property.title || formatModelName(name),
      type: filterType,
    };
    if (enumValues) {
      column.enumValues = enumValues;
    }
    columns.push(column);
  }

  return columns;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function getRecordId(record: ModelRecord): string | number {
  return (record["id"] ?? record["_id"] ?? record["pk"] ?? 0) as string | number;
}

function getRecordTitle(record: ModelRecord): string {
  const titleFields = ["name", "title", "label", "email", "username", "slug"];
  for (const field of titleFields) {
    if (record[field] && typeof record[field] === "string") {
      return record[field] as string;
    }
  }
  const id = getRecordId(record);
  return `Record #${id}`;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface ActionsCellProps {
  record: ModelRecord;
  onView: (record: ModelRecord) => void;
  onEdit: (record: ModelRecord) => void;
  onDelete: (record: ModelRecord) => void;
}

function ActionsCell({ record, onView, onEdit, onDelete }: ActionsCellProps) {
  return (
    <div className="flex items-center justify-end gap-1">
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onView(record);
        }}
        className={cn(
          "p-1.5 rounded-[var(--radius-md)]",
          "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
          "hover:bg-[var(--color-card-hover)]",
          "transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
        )}
        aria-label="View record"
        title="View"
      >
        <EyeIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onEdit(record);
        }}
        className={cn(
          "p-1.5 rounded-[var(--radius-md)]",
          "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
          "hover:bg-[var(--color-card-hover)]",
          "transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
        )}
        aria-label="Edit record"
        title="Edit"
      >
        <EditIcon className="h-4 w-4" />
      </button>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDelete(record);
        }}
        className={cn(
          "p-1.5 rounded-[var(--radius-md)]",
          "text-[var(--color-muted)] hover:text-[var(--color-error)]",
          "hover:bg-[var(--color-error)]/10",
          "transition-colors duration-150",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-error)]",
        )}
        aria-label="Delete record"
        title="Delete"
      >
        <TrashIcon className="h-4 w-4" />
      </button>
    </div>
  );
}

interface BulkActionToolbarProps {
  selectedCount: number;
  onClearSelection: () => void;
  onDeleteSelected: () => void;
  onExportSelected: () => void;
  isDeleting: boolean;
  isExporting: boolean;
}

function BulkActionToolbar({
  selectedCount,
  onClearSelection,
  onDeleteSelected,
  onExportSelected,
  isDeleting,
  isExporting,
}: BulkActionToolbarProps) {
  if (selectedCount === 0) return null;

  return (
    <div
      className={cn(
        "flex items-center justify-between gap-4",
        "px-4 py-3",
        "bg-[var(--color-primary)]/5",
        "border border-[var(--color-primary)]/20",
        "rounded-[var(--radius-lg)]",
        "animate-[fadeIn_150ms_ease-out]",
      )}
    >
      <div className="flex items-center gap-3">
        <span className="text-sm font-medium text-[var(--color-foreground)]">
          {selectedCount} selected
        </span>
        <button
          type="button"
          onClick={onClearSelection}
          className={cn(
            "text-sm text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
            "transition-colors duration-150",
          )}
        >
          Clear selection
        </button>
      </div>
      <div className="flex items-center gap-2">
        <Button
          variant="secondary"
          size="sm"
          onClick={onExportSelected}
          loading={isExporting}
          leftIcon={<DownloadIcon className="h-4 w-4" />}
        >
          Export Selected
        </Button>
        <Button
          variant="danger"
          size="sm"
          onClick={onDeleteSelected}
          loading={isDeleting}
          leftIcon={<TrashIcon className="h-4 w-4" />}
        >
          Delete Selected
        </Button>
      </div>
    </div>
  );
}

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isDeleting: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
  title,
  message,
  confirmLabel = "Delete",
}: DeleteConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader onClose={onClose}>{title}</ModalHeader>
      <ModalBody>
        <p className="text-sm text-[var(--color-foreground)]">{message}</p>
        <p className="text-sm text-[var(--color-muted)] mt-2">This action cannot be undone.</p>
      </ModalBody>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={isDeleting}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={isDeleting}>
          {confirmLabel}
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface ExportDropdownProps {
  onExport: (format: ExportFormat) => void;
  isExporting: boolean;
}

function ExportDropdown({ onExport, isExporting }: ExportDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        variant="secondary"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        loading={isExporting}
        leftIcon={<DownloadIcon className="h-4 w-4" />}
      >
        Export
      </Button>
      {isOpen && (
        <>
          <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} aria-hidden="true" />
          <div
            className={cn(
              "absolute right-0 top-full z-50 mt-1",
              "min-w-[140px] py-1",
              "rounded-[var(--radius-md)]",
              "border border-[var(--color-border)]",
              "bg-[var(--color-card)]",
              "shadow-lg shadow-black/20",
            )}
          >
            <button
              type="button"
              onClick={() => {
                onExport("csv");
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-4 py-2 text-left text-sm",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
              )}
            >
              Export as CSV
            </button>
            <button
              type="button"
              onClick={() => {
                onExport("json");
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-4 py-2 text-left text-sm",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
              )}
            >
              Export as JSON
            </button>
          </div>
        </>
      )}
    </div>
  );
}

interface EmptyStateProps {
  modelName: string;
  onCreateNew: () => void;
  hasFilters: boolean;
  onClearFilters: () => void;
}

function EmptyState({ modelName, onCreateNew, hasFilters, onClearFilters }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className={cn(
          "w-16 h-16 mb-4 rounded-full",
          "bg-[var(--color-card-hover)]",
          "flex items-center justify-center",
        )}
      >
        <TableIcon className="h-8 w-8 text-[var(--color-muted)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-2">
        {hasFilters ? "No matching records" : `No ${modelName} records`}
      </h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 max-w-md">
        {hasFilters
          ? "Try adjusting your search or filter criteria to find what you are looking for."
          : `Get started by creating your first ${modelName.toLowerCase()} record.`}
      </p>
      {hasFilters ? (
        <Button variant="secondary" onClick={onClearFilters}>
          Clear Filters
        </Button>
      ) : (
        <Button onClick={onCreateNew} leftIcon={<PlusIcon className="h-4 w-4" />}>
          Create {modelName}
        </Button>
      )}
    </div>
  );
}

interface ErrorStateProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

function ErrorState({ title, message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircleIcon className="h-12 w-12 text-[var(--color-error)] mb-4" />
      <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-2">{title}</h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 max-w-md">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Try Again
        </Button>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ModelListPage({ model }: ModelListPageProps) {
  return (
    <ProtectedRoute>
      <ModelListContent model={model} />
    </ProtectedRoute>
  );
}

function ModelListContent({ model }: ModelListPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToast } = useToast();

  const [deleteModalState, setDeleteModalState] = useState<{
    isOpen: boolean;
    record: ModelRecord | null;
    isBulk: boolean;
  }>({
    isOpen: false,
    record: null,
    isBulk: false,
  });

  const {
    page,
    pageSize,
    sortBy,
    sortOrder,
    selectedIds,
    setPage,
    setPageSize,
    handleSort,
    setSelectedIds,
    clearSelection,
  } = useDataTable<ModelRecord>({
    initialPage: Number(searchParams.get("page")) || 1,
    initialPageSize: Number(searchParams.get("pageSize")) || 10,
    ...(searchParams.get("sortBy") ? { initialSortBy: searchParams.get("sortBy")! } : {}),
    initialSortOrder: (searchParams.get("sortOrder") as "asc" | "desc") || "asc",
    getRowId: getRecordId,
  });

  const [filterState, setFilterState] = useState<FilterState>({
    search: searchParams.get("search") || "",
    filters: [],
  });

  const queryParams = useMemo<ListQueryParams>(() => {
    let filtersObj: Record<string, unknown> | undefined;
    if (filterState.filters.length > 0) {
      filtersObj = {};
      for (const filter of filterState.filters) {
        filtersObj[filter.column] = {
          operator: filter.operator,
          value: filter.value,
        };
      }
    }

    return {
      page,
      pageSize,
      ...(sortBy ? { sortBy, sortOrder } : {}),
      ...(filterState.search ? { search: filterState.search } : {}),
      ...(filtersObj ? { filters: filtersObj } : {}),
    };
  }, [page, pageSize, sortBy, sortOrder, filterState]);

  const {
    data: recordsData,
    isLoading: isLoadingRecords,
    error: recordsError,
    refetch: refetchRecords,
  } = useRecordsPaginated<ModelRecord>(model, queryParams);

  const { data: schema, isLoading: isLoadingSchema, error: schemaError } = useModelSchema(model);

  const deleteRecord = useDeleteRecord(model, {
    onSuccess: () => {
      addToast({
        variant: "success",
        title: "Record Deleted",
        description: "The record has been deleted successfully.",
      });
      setDeleteModalState({ isOpen: false, record: null, isBulk: false });
      refetchRecords();
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Delete Failed",
        description: error.message || "Failed to delete the record.",
      });
    },
  });

  const bulkDelete = useBulkDelete(model, {
    onSuccess: (response) => {
      addToast({
        variant: "success",
        title: "Records Deleted",
        description: `Successfully deleted ${response.deleted} records.`,
      });
      setDeleteModalState({ isOpen: false, record: null, isBulk: false });
      clearSelection();
      refetchRecords();
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Delete Failed",
        description: error.message || "Failed to delete the selected records.",
      });
    },
  });

  const exportRecords = useExportRecords(model, {
    onSuccess: (blob) => {
      const filename = `${model}-export-${new Date().toISOString().split("T")[0]}`;
      downloadBlob(blob, `${filename}.csv`);
      addToast({
        variant: "success",
        title: "Export Complete",
        description: "Your data has been exported successfully.",
      });
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Export Failed",
        description: error.message || "Failed to export records.",
      });
    },
  });

  const exportSelected = useExportSelected(model, {
    onSuccess: (blob) => {
      const filename = `${model}-selected-${new Date().toISOString().split("T")[0]}`;
      downloadBlob(blob, `${filename}.csv`);
      addToast({
        variant: "success",
        title: "Export Complete",
        description: "Selected records have been exported successfully.",
      });
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Export Failed",
        description: error.message || "Failed to export selected records.",
      });
    },
  });

  const modelDisplayName = useMemo(() => formatModelName(model), [model]);
  const isLoading = isLoadingRecords || isLoadingSchema;
  const hasError = recordsError || schemaError;
  const records = recordsData?.items ?? [];
  const totalItems = recordsData?.total ?? 0;

  const { columns, filterableColumns } = useMemo(() => {
    if (!schema) {
      return { columns: [], filterableColumns: [] };
    }

    const handleView = (record: ModelRecord) => {
      router.push(`/models/${model}/${getRecordId(record)}`);
    };

    const handleEdit = (record: ModelRecord) => {
      router.push(`/models/${model}/${getRecordId(record)}?edit=true`);
    };

    const handleDelete = (record: ModelRecord) => {
      setDeleteModalState({ isOpen: true, record, isBulk: false });
    };

    return {
      columns: generateColumnsFromSchema(schema, handleView, handleEdit, handleDelete),
      filterableColumns: generateFilterableColumns(schema),
    };
  }, [schema, model, router]);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Models", href: "/models" },
      { label: modelDisplayName },
    ],
    [modelDisplayName],
  );

  const handleCreateNew = useCallback(() => {
    router.push(`/models/${model}/new`);
  }, [router, model]);

  const handleRowClick = useCallback(
    (record: ModelRecord) => {
      router.push(`/models/${model}/${getRecordId(record)}`);
    },
    [router, model],
  );

  const handleFilterChange = useCallback(
    (newFilters: FilterState) => {
      setFilterState(newFilters);
      setPage(1);
    },
    [setPage],
  );

  const handleClearFilters = useCallback(() => {
    setFilterState({ search: "", filters: [] });
    setPage(1);
  }, [setPage]);

  const handleDeleteSelected = useCallback(() => {
    setDeleteModalState({ isOpen: true, record: null, isBulk: true });
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (deleteModalState.isBulk) {
      const ids = Array.from(selectedIds);
      bulkDelete.mutate({ ids });
    } else if (deleteModalState.record) {
      const id = getRecordId(deleteModalState.record);
      deleteRecord.mutate({ id });
    }
  }, [deleteModalState, selectedIds, bulkDelete, deleteRecord]);

  const handleCloseDeleteModal = useCallback(() => {
    setDeleteModalState({ isOpen: false, record: null, isBulk: false });
  }, []);

  const handleExport = useCallback(
    (format: ExportFormat) => {
      exportRecords.mutate({ format });
    },
    [exportRecords],
  );

  const handleExportSelected = useCallback(() => {
    const ids = Array.from(selectedIds);
    exportSelected.mutate({ ids, format: "csv" });
  }, [selectedIds, exportSelected]);

  useEffect(() => {
    const params = new URLSearchParams();
    if (page > 1) params.set("page", String(page));
    if (pageSize !== 10) params.set("pageSize", String(pageSize));
    if (sortBy) params.set("sortBy", sortBy);
    if (sortOrder !== "asc") params.set("sortOrder", sortOrder);
    if (filterState.search) params.set("search", filterState.search);

    const newUrl = params.toString()
      ? `${window.location.pathname}?${params.toString()}`
      : window.location.pathname;

    window.history.replaceState(null, "", newUrl);
  }, [page, pageSize, sortBy, sortOrder, filterState.search]);

  if (hasError && !isLoading) {
    const errorMessage =
      schemaError?.message || recordsError?.message || "Failed to load model data.";
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={modelDisplayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Data"
                message={errorMessage}
                onRetry={() => refetchRecords()}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  const hasActiveFilters = filterState.search.length > 0 || filterState.filters.length > 0;
  const selectedCount = selectedIds.size;
  const deleteRecordTitle = deleteModalState.record ? getRecordTitle(deleteModalState.record) : "";

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title={modelDisplayName}
          subtitle={
            isLoading ? "Loading..." : `${totalItems} ${totalItems === 1 ? "record" : "records"}`
          }
          breadcrumbs={breadcrumbs}
          actions={
            <div className="flex items-center gap-3">
              <ExportDropdown onExport={handleExport} isExporting={exportRecords.isPending} />
              <Button onClick={handleCreateNew} leftIcon={<PlusIcon className="h-4 w-4" />}>
                Create {modelDisplayName}
              </Button>
            </div>
          }
        />

        <Card>
          <CardBody className="py-4">
            {isLoadingSchema ? (
              <div className="flex items-center gap-4">
                <Skeleton variant="rectangular" className="flex-1" height={40} />
                <Skeleton variant="rectangular" width={100} height={40} />
              </div>
            ) : (
              <SearchFilter
                columns={filterableColumns}
                onFilterChange={handleFilterChange}
                initialFilters={filterState}
                searchPlaceholder={`Search ${modelDisplayName.toLowerCase()}...`}
                syncToUrl={false}
              />
            )}
          </CardBody>
        </Card>

        <BulkActionToolbar
          selectedCount={selectedCount}
          onClearSelection={clearSelection}
          onDeleteSelected={handleDeleteSelected}
          onExportSelected={handleExportSelected}
          isDeleting={bulkDelete.isPending}
          isExporting={exportSelected.isPending}
        />

        <Card>
          {isLoading ? (
            <CardBody>
              <div className="space-y-4">
                <div className="flex items-center gap-4">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <Skeleton key={i} variant="text" className="flex-1" />
                  ))}
                </div>
                {Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="flex items-center gap-4">
                    {Array.from({ length: 5 }).map((_, j) => (
                      <Skeleton key={j} variant="text" className="flex-1" />
                    ))}
                  </div>
                ))}
              </div>
            </CardBody>
          ) : records.length === 0 ? (
            <CardBody>
              <EmptyState
                modelName={modelDisplayName}
                onCreateNew={handleCreateNew}
                hasFilters={hasActiveFilters}
                onClearFilters={handleClearFilters}
              />
            </CardBody>
          ) : (
            <DataTable
              columns={columns}
              data={records as ModelRecord[]}
              isLoading={isLoadingRecords}
              page={page}
              pageSize={pageSize}
              totalItems={totalItems}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              {...(sortBy ? { sortBy } : {})}
              sortOrder={sortOrder}
              onSort={handleSort}
              selectable
              selectedIds={selectedIds}
              onSelectionChange={setSelectedIds}
              getRowId={getRecordId}
              onRowClick={handleRowClick}
              emptyMessage={`No ${modelDisplayName.toLowerCase()} records found`}
              showColumnToggle
              striped
              searchTerm={filterState.search}
            />
          )}
        </Card>
      </div>

      <DeleteConfirmModal
        isOpen={deleteModalState.isOpen}
        onClose={handleCloseDeleteModal}
        onConfirm={handleConfirmDelete}
        isDeleting={deleteRecord.isPending || bulkDelete.isPending}
        title={
          deleteModalState.isBulk ? `Delete ${selectedCount} Records` : `Delete ${modelDisplayName}`
        }
        message={
          deleteModalState.isBulk
            ? `Are you sure you want to delete ${selectedCount} selected records? All associated data will be permanently removed.`
            : `Are you sure you want to delete "${deleteRecordTitle}"? All associated data will be permanently removed.`
        }
        confirmLabel={deleteModalState.isBulk ? `Delete ${selectedCount} Records` : "Delete"}
      />
    </MainLayout>
  );
}

export default ModelListPage;
