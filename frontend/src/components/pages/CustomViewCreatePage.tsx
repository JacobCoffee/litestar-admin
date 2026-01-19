"use client";

import { useMemo, useCallback } from "react";
import { useRouter } from "next/navigation";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Loading";
import { useToast } from "@/components/ui/Toast";
import { useCustomViewSchema, useCreateCustomViewItem } from "@/hooks/useApi";
import { RecordForm } from "@/components/data/RecordForm";
import { toTitleCase } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

type CustomViewRecord = Record<string, unknown>;

export interface CustomViewCreatePageProps {
  identity: string;
  viewName?: string | undefined;
}

// ============================================================================
// Icons
// ============================================================================

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

// ============================================================================
// Sub-Components
// ============================================================================

interface ErrorStateProps {
  title: string;
  message: string;
  onBack?: () => void;
}

function ErrorState({ title, message, onBack }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircleIcon className="h-12 w-12 text-[var(--color-error)] mb-4" />
      <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-2">{title}</h3>
      <p className="text-sm text-[var(--color-muted)] mb-6 max-w-md">{message}</p>
      {onBack && (
        <button
          type="button"
          onClick={onBack}
          className="px-4 py-2 text-sm font-medium text-[var(--color-foreground)] bg-[var(--color-card-hover)] rounded-[var(--radius-md)] hover:bg-[var(--color-border)] transition-colors"
        >
          Go Back
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function CustomViewCreatePage({ identity, viewName }: CustomViewCreatePageProps) {
  return (
    <ProtectedRoute>
      <CustomViewCreateContent identity={identity} viewName={viewName} />
    </ProtectedRoute>
  );
}

function CustomViewCreateContent({ identity, viewName }: CustomViewCreatePageProps) {
  const router = useRouter();
  const { addToast } = useToast();

  const {
    data: schemaResponse,
    isLoading: isLoadingSchema,
    error: schemaError,
  } = useCustomViewSchema(identity);

  const createItem = useCreateCustomViewItem<CustomViewRecord>(identity, {
    onSuccess: (data) => {
      addToast({
        variant: "success",
        title: "Item Created",
        description: "The item has been created successfully.",
      });
      // Get the ID from the created item to navigate to detail page
      const id = data?.["id"] ?? data?.["_id"] ?? data?.["pk"];
      if (id) {
        router.push(`/custom/${identity}/${id}`);
      } else {
        router.push(`/custom/${identity}`);
      }
    },
    onError: (error) => {
      addToast({
        variant: "error",
        title: "Creation Failed",
        description: error.message || "Failed to create the item.",
      });
    },
  });

  // Extract schema from response
  const schema = schemaResponse?.schema;
  const viewCanCreate = schemaResponse?.can_create ?? true;

  const displayName = viewName || formatViewName(identity);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Custom Views", href: "/custom" },
      { label: displayName, href: `/custom/${identity}` },
      { label: "Create New" },
    ],
    [displayName, identity],
  );

  const handleSubmit = useCallback(
    async (values: CustomViewRecord) => {
      await createItem.mutateAsync(values);
    },
    [createItem],
  );

  const handleCancel = useCallback(() => {
    router.push(`/custom/${identity}`);
  }, [router, identity]);

  if (isLoadingSchema) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={`Create ${displayName}`} breadcrumbs={breadcrumbs} />
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

  if (schemaError) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Form"
                message={schemaError.message || "Could not load the form schema."}
                onBack={handleCancel}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (!schema) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Schema Not Found"
                message="The form schema for this view is not available."
                onBack={handleCancel}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (!viewCanCreate) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={displayName} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Creation Not Allowed"
                message="Creating new items is not permitted for this view."
                onBack={handleCancel}
              />
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
          title={`Create ${displayName}`}
          subtitle="Fill in the details below to create a new item"
          breadcrumbs={breadcrumbs}
        />

        <Card>
          <CardHeader>
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Details</h2>
          </CardHeader>
          <CardBody>
            <RecordForm
              schema={schema}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              isSubmitting={createItem.isPending}
              mode="create"
            />
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}

export default CustomViewCreatePage;
