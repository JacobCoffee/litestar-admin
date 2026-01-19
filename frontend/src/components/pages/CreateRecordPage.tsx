"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { RecordForm } from "@/components/data/RecordForm";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Loading";
import { useModelSchema, useCreateRecord, isApiError } from "@/hooks/useApi";
import { cn, toTitleCase } from "@/lib/utils";
import type { ApiError, ModelRecord, ModelSchema } from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface CreateRecordPageProps {
  model: string;
}

interface ServerValidationErrors {
  [field: string]: string;
}

// ============================================================================
// Icons
// ============================================================================

const PlusIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path d="M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5a.75.75 0 000 1.5h4.5v4.5a.75.75 0 001.5 0v-4.5h4.5a.75.75 0 000-1.5h-4.5v-4.5z" />
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

const ArrowLeftIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
    <path
      fillRule="evenodd"
      d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 111.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z"
      clipRule="evenodd"
    />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatModelName(model: string): string {
  return toTitleCase(model.replace(/[-_]/g, " "));
}

function extractSchemaDefaults(schema: ModelSchema): Record<string, unknown> {
  const defaults: Record<string, unknown> = {};

  for (const [name, property] of Object.entries(schema.properties)) {
    if (property.readOnly) continue;

    if (property.default !== undefined) {
      defaults[name] = property.default;
    } else if (property.type === "boolean") {
      defaults[name] = false;
    } else if (property.type === "array") {
      defaults[name] = [];
    } else if (property.type === "object") {
      defaults[name] = {};
    }
  }

  return defaults;
}

function parseValidationErrors(error: ApiError): ServerValidationErrors {
  const errors: ServerValidationErrors = {};

  const response = error.response;
  if (response?.extra) {
    const extra = response.extra as Record<string, unknown>;

    const extraErrors = extra["errors"];
    if (Array.isArray(extraErrors)) {
      for (const fieldError of extraErrors) {
        if (typeof fieldError === "object" && fieldError !== null) {
          const err = fieldError as {
            field?: string;
            loc?: string[];
            message?: string;
            msg?: string;
          };
          const fieldName = err.field ?? err.loc?.[err.loc.length - 1];
          const message = err.message ?? err.msg ?? "Invalid value";
          if (fieldName) {
            errors[fieldName] = message;
          }
        }
      }
    }

    const extraFields = extra["fields"];
    if (typeof extraFields === "object" && extraFields !== null) {
      const fields = extraFields as Record<string, string>;
      Object.assign(errors, fields);
    }
  }

  return errors;
}

// ============================================================================
// Loading Component
// ============================================================================

function LoadingState() {
  return (
    <div
      className={cn("flex flex-col items-center justify-center py-16", "text-[var(--color-muted)]")}
    >
      <Spinner size="lg" />
      <p className="mt-4 text-sm">Loading schema...</p>
    </div>
  );
}

// ============================================================================
// Error Component
// ============================================================================

interface ErrorStateProps {
  title: string;
  message: string;
  onRetry?: () => void;
}

function ErrorState({ title, message, onRetry }: ErrorStateProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center py-16", "text-center")}>
      <AlertCircleIcon className="h-12 w-12 text-[var(--color-error)]" />
      <h3 className="mt-4 text-lg font-medium text-[var(--color-foreground)]">{title}</h3>
      <p className="mt-2 text-sm text-[var(--color-muted)] max-w-md">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry} className="mt-6">
          Try Again
        </Button>
      )}
    </div>
  );
}

// ============================================================================
// Alert Component
// ============================================================================

interface AlertProps {
  variant: "error" | "success";
  title?: string;
  message: string;
  onDismiss?: () => void;
}

function Alert({ variant, title, message, onDismiss }: AlertProps) {
  const variantStyles = {
    error: "bg-[var(--color-error)]/10 border-[var(--color-error)]/20 text-[var(--color-error)]",
    success:
      "bg-[var(--color-success)]/10 border-[var(--color-success)]/20 text-[var(--color-success)]",
  };

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-[var(--radius-md)] p-4 border",
        variantStyles[variant],
      )}
      role="alert"
    >
      <AlertCircleIcon className="h-5 w-5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        {title && <p className="font-medium">{title}</p>}
        <p className={cn("text-sm", title && "mt-1")}>{message}</p>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="flex-shrink-0 p-1 rounded hover:bg-black/10 transition-colors"
          aria-label="Dismiss"
        >
          <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
          </svg>
        </button>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function CreateRecordPage({ model }: CreateRecordPageProps) {
  return (
    <ProtectedRoute>
      <CreateRecordContent model={model} />
    </ProtectedRoute>
  );
}

function CreateRecordContent({ model }: CreateRecordPageProps) {
  const router = useRouter();
  const [serverErrors, setServerErrors] = useState<ServerValidationErrors>({});
  const [generalError, setGeneralError] = useState<string | null>(null);

  const {
    data: schema,
    isLoading: isLoadingSchema,
    error: schemaError,
    refetch: refetchSchema,
  } = useModelSchema(model, "create");

  const createRecord = useCreateRecord<ModelRecord>(model, {
    onSuccess: (newRecord) => {
      const recordId = newRecord["id"] ?? newRecord["_id"] ?? newRecord["pk"];

      if (recordId !== undefined && recordId !== null) {
        router.push(`/models/${model}/${recordId}`);
      } else {
        router.push(`/models/${model}`);
      }
    },
    onError: (error) => {
      if (isApiError(error)) {
        const fieldErrors = parseValidationErrors(error);

        if (Object.keys(fieldErrors).length > 0) {
          setServerErrors(fieldErrors);
          setGeneralError("Please correct the errors below and try again.");
        } else {
          setGeneralError(
            error.detail ?? error.message ?? "Failed to create record. Please try again.",
          );
        }
      } else {
        setGeneralError("An unexpected error occurred. Please try again.");
      }
    },
  });

  const modelDisplayName = useMemo(() => formatModelName(model), [model]);

  const initialValues = useMemo(() => {
    if (!schema) return {};
    return extractSchemaDefaults(schema);
  }, [schema]);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Models", href: "/models" },
      { label: modelDisplayName, href: `/models/${model}` },
      { label: "New" },
    ],
    [model, modelDisplayName],
  );

  const handleSubmit = useCallback(
    async (values: Record<string, unknown>) => {
      setServerErrors({});
      setGeneralError(null);
      await createRecord.mutateAsync(values);
    },
    [createRecord],
  );

  const handleCancel = useCallback(() => {
    router.push(`/models/${model}`);
  }, [router, model]);

  const handleDismissError = useCallback(() => {
    setGeneralError(null);
  }, []);

  if (isLoadingSchema) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title={`Create ${modelDisplayName}`} breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <LoadingState />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (schemaError || !schema) {
    const errorMessage = isApiError(schemaError)
      ? (schemaError.detail ?? schemaError.message)
      : "Failed to load model schema. The model may not exist or you may not have permission to access it.";

    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title={`Create ${modelDisplayName}`}
            breadcrumbs={breadcrumbs}
            actions={
              <Button
                variant="secondary"
                leftIcon={<ArrowLeftIcon className="h-4 w-4" />}
                onClick={handleCancel}
              >
                Back to List
              </Button>
            }
          />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Form"
                message={errorMessage}
                onRetry={() => refetchSchema()}
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
          title={`Create ${modelDisplayName}`}
          subtitle={`Add a new ${modelDisplayName.toLowerCase()} record`}
          breadcrumbs={breadcrumbs}
          actions={
            <Link href={`/models/${model}`}>
              <Button variant="secondary" leftIcon={<ArrowLeftIcon className="h-4 w-4" />}>
                Back to List
              </Button>
            </Link>
          }
        />

        {generalError && (
          <Alert
            variant="error"
            title="Error Creating Record"
            message={generalError}
            onDismiss={handleDismissError}
          />
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <div
                className={cn(
                  "flex h-10 w-10 items-center justify-center rounded-[var(--radius-md)]",
                  "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                )}
              >
                <PlusIcon className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-lg font-medium text-[var(--color-foreground)]">
                  New {modelDisplayName}
                </h2>
                <p className="text-sm text-[var(--color-muted)]">
                  Fill in the form below to create a new record
                </p>
              </div>
            </div>
          </CardHeader>

          <CardBody>
            <RecordForm
              schema={schema}
              initialValues={initialValues}
              onSubmit={handleSubmit}
              onCancel={handleCancel}
              isSubmitting={createRecord.isPending}
              mode="create"
              errors={serverErrors}
              modelName={model}
            />
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}

export default CreateRecordPage;
