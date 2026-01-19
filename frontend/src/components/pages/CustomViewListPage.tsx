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
import { useCustomViewItems, useCustomViewSchema, useDeleteCustomViewItem } from "@/hooks/useApi";
import { useAdminSettings } from "@/contexts/AdminSettingsContext";
import { cn, toTitleCase, formatDate } from "@/lib/utils";
import type { ModelSchema, SchemaProperty, ListQueryParams, ColumnDefinition } from "@/types";

// ============================================================================
// Types
// ============================================================================

type CustomViewRecord = Record<string, unknown>;

export interface CustomViewListPageProps {
  identity: string;
  viewName?: string | undefined;
  columns?: readonly ColumnDefinition[];
  canCreate?: boolean;
  canEdit?: boolean;
  canDelete?: boolean;
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

function formatViewName(identity: string): string {
  return toTitleCase(identity.replace(/[-_]/g, " "));
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
  onView: (record: CustomViewRecord) => void,
  onEdit: (record: CustomViewRecord) => void,
  onDelete: (record: CustomViewRecord) => void,
  canEdit: boolean,
  canDelete: boolean,
): Column<CustomViewRecord>[] {
  const columns: Column<CustomViewRecord>[] = [];
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

    const column: Column<CustomViewRecord> = {
      key: name,
      header: property.title || formatViewName(name),
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
    render: (_value: unknown, row: CustomViewRecord) => (
      <ActionsCell
        record={row}
        onView={onView}
        onEdit={canEdit ? onEdit : undefined}
        onDelete={canDelete ? onDelete : undefined}
      />
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
      label: property.title || formatViewName(name),
      type: filterType,
    };
    if (enumValues) {
      column.enumValues = enumValues;
    }
    columns.push(column);
  }

  return columns;
}

function getRecordId(record: CustomViewRecord, pkField: string = "id"): string {
  const id = record[pkField] ?? record["id"] ?? record["_id"] ?? record["pk"] ?? "";
  return String(id);
}

function getRecordTitle(record: CustomViewRecord): string {
  const titleFields = ["name", "title", "label", "email", "username", "slug"];
  for (const field of titleFields) {
    if (record[field] && typeof record[field] === "string") {
      return record[field] as string;
    }
  }
  const id = getRecordId(record);
  return `Item #${id}`;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface ActionsCellProps {
  record: CustomViewRecord;
  onView: (record: CustomViewRecord) => void;
  onEdit?: ((record: CustomViewRecord) => void) | undefined;
  onDelete?: ((record: CustomViewRecord) => void) | undefined;
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
        aria-label="View item"
        title="View"
      >
        <EyeIcon className="h-4 w-4" />
      </button>
      {onEdit && (
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
          aria-label="Edit item"
          title="Edit"
        >
          <EditIcon className="h-4 w-4" />
        </button>
      )}
      {onDelete && (
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
          aria-label="Delete item"
          title="Delete"
        >
          <TrashIcon className="h-4 w-4" />
        </button>
      )}
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
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  isDeleting,
  title,
  message,
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
          Delete
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface EmptyStateProps {
  viewName: string;
  onCreateNew?: (() => void) | undefined;
  hasFilters: boolean;
  onClearFilters: () => void;
}

function EmptyState({ viewName, onCreateNew, hasFilters, onClearFilters }: EmptyStateProps) {
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
        {hasFilters ? "No matching items" : `No ${viewName} items`}
      </h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 max-w-md">
        {hasFilters
          ? "Try adjusting your search or filter criteria to find what you are looking for."
          : `No items are available in this view yet.`}
      </p>
      {hasFilters ? (
        <Button variant="secondary" onClick={onClearFilters}>
          Clear Filters
        </Button>
      ) : onCreateNew ? (
        <Button onClick={onCreateNew} leftIcon={<PlusIcon className="h-4 w-4" />}>
          Create {viewName}
        </Button>
      ) : null}
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

export function CustomViewListPage({
  identity,
  viewName,
  canCreate = false,
  canEdit = false,
  canDelete = false,
}: CustomViewListPageProps) {
  return (
    <ProtectedRoute>
      <CustomViewListContent
        identity={identity}
        viewName={viewName}
        canCreate={canCreate}
        canEdit={canEdit}
        canDelete={canDelete}
      />
    </ProtectedRoute>
  );
}

function CustomViewListContent({
  identity,
  viewName,
  canCreate,
  canEdit,
  canDelete,
}: CustomViewListPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { addToast } = useToast();
  const { settings } = useAdminSettings();

  const [deleteModalState, setDeleteModalState] = useState<{
    isOpen: boolean;
    record: CustomViewRecord | null;
  }>({
    isOpen: false,
    record: null,
  });

  const { page, pageSize, sortBy, sortOrder, setPage, setPageSize, handleSort } =
    useDataTable<CustomViewRecord>({
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
    data: itemsData,
    isLoading: isLoadingItems,
    error: itemsError,
    refetch: refetchItems,
  } = useCustomViewItems<CustomViewRecord>(identity, queryParams);

  const {
    data: schemaResponse,
    isLoading: isLoadingSchema,
    error: schemaError,
  } = useCustomViewSchema(identity);

  // Extract schema and metadata from response
  const schema = schemaResponse?.schema;
  const pkField = schemaResponse?.pk_field ?? "id";
  const viewCanCreate = schemaResponse?.can_create ?? canCreate ?? false;
  const viewCanEdit = schemaResponse?.can_edit ?? canEdit ?? false;
  const viewCanDelete = schemaResponse?.can_delete ?? canDelete ?? false;

  const deleteItem = useDeleteCustomViewItem(identity, {
    onSuccess: () => {
      addToast({
        variant: "success",
        title: "Item Deleted",
        description: "The item has been deleted successfully.",
      });
      setDeleteModalState({ isOpen: false, record: null });
      refetchItems();
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Delete Failed",
        description: error.message || "Failed to delete the item.",
      });
    },
  });

  const displayName = viewName || formatViewName(identity);
  const isLoading = isLoadingItems || isLoadingSchema;
  const hasError = itemsError || schemaError;
  const items = itemsData?.items ?? [];
  const totalItems = itemsData?.total ?? 0;

  const { columns, filterableColumns } = useMemo(() => {
    if (!schema) {
      return { columns: [], filterableColumns: [] };
    }

    const handleView = (record: CustomViewRecord) => {
      router.push(`/custom/${identity}/${getRecordId(record, pkField)}`);
    };

    const handleEdit = (record: CustomViewRecord) => {
      router.push(`/custom/${identity}/${getRecordId(record, pkField)}?edit=true`);
    };

    const handleDelete = (record: CustomViewRecord) => {
      setDeleteModalState({ isOpen: true, record });
    };

    return {
      columns: generateColumnsFromSchema(
        schema,
        handleView,
        handleEdit,
        handleDelete,
        viewCanEdit,
        viewCanDelete,
      ),
      filterableColumns: generateFilterableColumns(schema),
    };
  }, [schema, identity, router, pkField, viewCanEdit, viewCanDelete]);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Custom Views", href: "/custom" },
      { label: displayName },
    ],
    [displayName],
  );

  const handleCreateNew = useCallback(() => {
    router.push(`/custom/${identity}/new`);
  }, [router, identity]);

  // Memoized getRowId that uses the pk_field from schema
  const getRowIdWithPk = useCallback(
    (record: CustomViewRecord) => getRecordId(record, pkField),
    [pkField],
  );

  const handleRowClick = useCallback(
    (record: CustomViewRecord) => {
      router.push(`/custom/${identity}/${getRecordId(record, pkField)}`);
    },
    [router, identity, pkField],
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

  const handleConfirmDelete = useCallback(() => {
    if (deleteModalState.record) {
      const id = getRecordId(deleteModalState.record, pkField);
      deleteItem.mutate(id);
    }
  }, [deleteModalState, deleteItem, pkField]);

  const handleCloseDeleteModal = useCallback(() => {
    setDeleteModalState({ isOpen: false, record: null });
  }, []);

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
    const errorMessage = schemaError?.message || itemsError?.message || "Failed to load data.";
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Data"
                message={errorMessage}
                onRetry={() => refetchItems()}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  const hasActiveFilters = filterState.search.length > 0 || filterState.filters.length > 0;
  const deleteRecordTitle = deleteModalState.record ? getRecordTitle(deleteModalState.record) : "";

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title={displayName}
          subtitle={
            isLoading ? "Loading..." : `${totalItems} ${totalItems === 1 ? "item" : "items"}`
          }
          breadcrumbs={breadcrumbs}
          actions={
            viewCanCreate ? (
              <Button onClick={handleCreateNew} leftIcon={<PlusIcon className="h-4 w-4" />}>
                Create {displayName}
              </Button>
            ) : undefined
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
                searchPlaceholder={`Search ${displayName.toLowerCase()}...`}
                syncToUrl={false}
              />
            )}
          </CardBody>
        </Card>

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
          ) : items.length === 0 ? (
            <CardBody>
              <EmptyState
                viewName={displayName}
                onCreateNew={viewCanCreate ? handleCreateNew : undefined}
                hasFilters={hasActiveFilters}
                onClearFilters={handleClearFilters}
              />
            </CardBody>
          ) : (
            <DataTable
              columns={columns}
              data={items as CustomViewRecord[]}
              isLoading={isLoadingItems}
              page={page}
              pageSize={pageSize}
              totalItems={totalItems}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
              {...(sortBy ? { sortBy } : {})}
              sortOrder={sortOrder}
              onSort={handleSort}
              getRowId={getRowIdWithPk}
              onRowClick={handleRowClick}
              emptyMessage={`No ${displayName.toLowerCase()} items found`}
              showColumnToggle
              striped
              showKeyboardHints={settings.showKeyboardHints}
              enableKeyboardNavigation={settings.enableKeyboardNavigation}
            />
          )}
        </Card>
      </div>

      <DeleteConfirmModal
        isOpen={deleteModalState.isOpen}
        onClose={handleCloseDeleteModal}
        onConfirm={handleConfirmDelete}
        isDeleting={deleteItem.isPending}
        title={`Delete ${displayName}`}
        message={`Are you sure you want to delete "${deleteRecordTitle}"? All associated data will be permanently removed.`}
      />
    </MainLayout>
  );
}

export default CustomViewListPage;
