"use client";

import { useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Loading";
import { useCustomViewItem, useCustomViewSchema } from "@/hooks/useApi";
import { cn, toTitleCase, formatDate } from "@/lib/utils";
import type { SchemaProperty } from "@/types";

// ============================================================================
// Types
// ============================================================================

type CustomViewRecord = Record<string, unknown>;

export interface CustomViewDetailPageProps {
  identity: string;
  itemId: string;
  viewName?: string | undefined;
  canEdit?: boolean | undefined;
  canDelete?: boolean | undefined;
}

// ============================================================================
// Icons
// ============================================================================

const ArrowLeftIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M19 12H5M12 19l-7-7 7-7" />
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
  >
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
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
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4M12 16h.01" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatViewName(identity: string): string {
  return toTitleCase(identity.replace(/[-_]/g, " "));
}

function formatFieldValue(value: unknown, property?: SchemaProperty): string {
  if (value === null || value === undefined) {
    return "-";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (property?.format === "date" && typeof value === "string") {
    return formatDate(value);
  }

  if (property?.format === "date-time" && typeof value === "string") {
    return formatDate(value, {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  if (typeof value === "object") {
    return JSON.stringify(value, null, 2);
  }

  return String(value);
}

function getRecordTitle(record: CustomViewRecord): string {
  const titleFields = ["name", "title", "label", "email", "username", "slug", "key"];
  for (const field of titleFields) {
    if (record[field] && typeof record[field] === "string") {
      return record[field] as string;
    }
  }
  const id = record["id"] ?? record["_id"] ?? record["pk"] ?? "";
  return `Item #${id}`;
}

// ============================================================================
// Sub-Components
// ============================================================================

interface FieldDisplayProps {
  label: string;
  value: unknown;
  property?: SchemaProperty;
}

function FieldDisplay({ label, value, property }: FieldDisplayProps) {
  const formattedValue = formatFieldValue(value, property);
  const isLongText = typeof value === "string" && value.length > 100;
  const isObject = typeof value === "object" && value !== null;

  return (
    <div className="py-3 border-b border-[var(--color-border)] last:border-b-0">
      <dt className="text-sm font-medium text-[var(--color-muted)] mb-1">{label}</dt>
      <dd
        className={cn(
          "text-sm text-[var(--color-foreground)]",
          isLongText && "whitespace-pre-wrap",
          isObject && "font-mono text-xs bg-[var(--color-card-hover)] p-2 rounded overflow-x-auto",
        )}
      >
        {typeof value === "boolean" ? (
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
              value
                ? "bg-[var(--color-success)]/10 text-[var(--color-success)]"
                : "bg-[var(--color-muted)]/10 text-[var(--color-muted)]",
            )}
          >
            {formattedValue}
          </span>
        ) : property?.enum ? (
          <span
            className={cn(
              "inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium",
              "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
            )}
          >
            {formattedValue}
          </span>
        ) : (
          formattedValue
        )}
      </dd>
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

export function CustomViewDetailPage({
  identity,
  itemId,
  viewName,
  canEdit = false,
}: CustomViewDetailPageProps) {
  return (
    <ProtectedRoute>
      <CustomViewDetailContent
        identity={identity}
        itemId={itemId}
        viewName={viewName}
        canEdit={canEdit}
      />
    </ProtectedRoute>
  );
}

function CustomViewDetailContent({
  identity,
  itemId,
  viewName,
  canEdit,
}: CustomViewDetailPageProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isEditMode = searchParams.get("edit") === "true";

  const {
    data: item,
    isLoading: isLoadingItem,
    error: itemError,
    refetch: refetchItem,
  } = useCustomViewItem<CustomViewRecord>(identity, itemId);

  const {
    data: schemaResponse,
    isLoading: isLoadingSchema,
    error: schemaError,
  } = useCustomViewSchema(identity);

  // Extract schema from response
  const schema = schemaResponse?.schema;

  const displayName = viewName || formatViewName(identity);
  const isLoading = isLoadingItem || isLoadingSchema;
  const hasError = itemError || schemaError;

  const recordTitle = item ? getRecordTitle(item) : `Item #${itemId}`;

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Custom Views", href: "/custom" },
      { label: displayName, href: `/custom/${identity}` },
      { label: recordTitle },
    ],
    [displayName, identity, recordTitle],
  );

  // Get fields to display from schema
  const fields = useMemo(() => {
    if (!schema || !item) return [];

    return Object.entries(schema.properties || {}).map(([key, property]) => ({
      key,
      label: property.title || formatViewName(key),
      value: item[key],
      property,
    }));
  }, [schema, item]);

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Loading..." breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <div className="space-y-4">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="py-3 border-b border-[var(--color-border)]">
                    <Skeleton variant="text" width={100} className="mb-1" />
                    <Skeleton variant="text" width="60%" />
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (hasError) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Item"
                message={itemError?.message || schemaError?.message || "Item not found."}
                onRetry={() => refetchItem()}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (!item) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState title="Item Not Found" message="The requested item does not exist." />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title={recordTitle}
          subtitle={displayName}
          breadcrumbs={breadcrumbs}
          actions={
            <div className="flex items-center gap-2">
              <Link href={`/custom/${identity}`}>
                <Button variant="secondary" leftIcon={<ArrowLeftIcon className="h-4 w-4" />}>
                  Back to List
                </Button>
              </Link>
              {canEdit && !isEditMode && (
                <Button
                  onClick={() => router.push(`/custom/${identity}/${itemId}?edit=true`)}
                  leftIcon={<EditIcon className="h-4 w-4" />}
                >
                  Edit
                </Button>
              )}
            </div>
          }
        />

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Details</h2>
          </CardHeader>
          <CardBody>
            <dl className="divide-y divide-[var(--color-border)]">
              {fields.map(({ key, label, value, property }) => (
                <FieldDisplay key={key} label={label} value={value} property={property} />
              ))}
            </dl>
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}

export default CustomViewDetailPage;
