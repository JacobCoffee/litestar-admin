"use client";

import { useState, useCallback, useMemo } from "react";
import { useRouter } from "next/navigation";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Loading";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { useToast } from "@/components/ui/Toast";
import { Input, Select, TextArea, Checkbox, FormField } from "@/components/ui/Form";
import { useAction, useExecuteAction } from "@/hooks/useApi";
import { cn, toTitleCase } from "@/lib/utils";
import type { FormField as FormFieldType, ActionInfo, FormFieldOption } from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface ActionPageProps {
  identity: string;
}

// ============================================================================
// Icons
// ============================================================================

const PlayIcon = ({ className }: { className?: string }) => (
  <svg className={className} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M8 5v14l11-7z" />
  </svg>
);

const AlertTriangleIcon = ({ className }: { className?: string }) => (
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
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const CheckCircleIcon = ({ className }: { className?: string }) => (
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
    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
    <polyline points="22 4 12 14.01 9 11.01" />
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

const ZapIcon = ({ className }: { className?: string }) => (
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
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatActionName(identity: string): string {
  return toTitleCase(identity.replace(/[-_]/g, " "));
}

function getDefaultValue(field: FormFieldType): unknown {
  if (field.default !== null && field.default !== undefined) {
    return field.default;
  }
  switch (field.field_type) {
    case "boolean":
      return false;
    case "number":
    case "integer":
      return "";
    case "multiselect":
      return [];
    default:
      return "";
  }
}

// ============================================================================
// Form Field Renderer
// ============================================================================

interface DynamicFormFieldProps {
  field: FormFieldType;
  value: unknown;
  onChange: (value: unknown) => void;
  error?: string | undefined;
}

function DynamicFormField({ field, value, onChange, error }: DynamicFormFieldProps) {
  const fieldId = `field-${field.name}`;

  switch (field.field_type) {
    case "text":
    case "json":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <TextArea
            id={fieldId}
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            error={!!error}
            rows={field.field_type === "json" ? 8 : 4}
          />
        </FormField>
      );

    case "boolean":
      return (
        <FormField hint={field.help_text} error={error}>
          <Checkbox
            id={fieldId}
            checked={!!value}
            onChange={(e) => onChange(e.target.checked)}
            label={field.label}
            error={!!error}
          />
        </FormField>
      );

    case "select":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Select
            id={fieldId}
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            options={field.options.map((opt: FormFieldOption) => ({
              value: opt.value,
              label: opt.label,
            }))}
            placeholder={field.placeholder || "Select an option"}
            error={!!error}
          />
        </FormField>
      );

    case "number":
    case "integer":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="number"
            value={String(value ?? "")}
            onChange={(e) => {
              const val = e.target.value;
              if (val === "") {
                onChange("");
              } else if (field.field_type === "integer") {
                onChange(parseInt(val, 10));
              } else {
                onChange(parseFloat(val));
              }
            }}
            placeholder={field.placeholder}
            error={!!error}
            step={field.field_type === "integer" ? 1 : "any"}
          />
        </FormField>
      );

    case "email":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="email"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            error={!!error}
          />
        </FormField>
      );

    case "url":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="url"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            error={!!error}
          />
        </FormField>
      );

    case "password":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="password"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            error={!!error}
          />
        </FormField>
      );

    case "date":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="date"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            error={!!error}
          />
        </FormField>
      );

    case "datetime":
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="datetime-local"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            error={!!error}
          />
        </FormField>
      );

    case "string":
    default:
      return (
        <FormField
          label={field.label}
          htmlFor={fieldId}
          required={field.required}
          error={error}
          hint={field.help_text}
        >
          <Input
            id={fieldId}
            type="text"
            value={String(value ?? "")}
            onChange={(e) => onChange(e.target.value)}
            placeholder={field.placeholder}
            error={!!error}
          />
        </FormField>
      );
  }
}

// ============================================================================
// Sub-Components
// ============================================================================

interface ConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isExecuting: boolean;
  action: ActionInfo;
}

function ConfirmationModal({
  isOpen,
  onClose,
  onConfirm,
  isExecuting,
  action,
}: ConfirmationModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose}>
      <ModalHeader onClose={onClose}>Confirm Action</ModalHeader>
      <ModalBody>
        {action.dangerous && (
          <div
            className={cn(
              "flex items-center gap-3 p-3 mb-4 rounded-[var(--radius-md)]",
              "bg-[var(--color-error)]/10 text-[var(--color-error)]",
            )}
          >
            <AlertTriangleIcon className="h-5 w-5 shrink-0" />
            <p className="text-sm font-medium">
              This is a dangerous action and may have irreversible consequences.
            </p>
          </div>
        )}
        <p className="text-sm text-[var(--color-foreground)]">
          {action.confirmation_message || `Are you sure you want to execute "${action.name}"?`}
        </p>
      </ModalBody>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={isExecuting}>
          Cancel
        </Button>
        <Button
          variant={action.dangerous ? "danger" : "primary"}
          onClick={onConfirm}
          loading={isExecuting}
        >
          Execute
        </Button>
      </ModalFooter>
    </Modal>
  );
}

interface ResultDisplayProps {
  success: boolean;
  message: string;
  onDismiss: () => void;
}

function ResultDisplay({ success, message, onDismiss }: ResultDisplayProps) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 p-4 rounded-[var(--radius-lg)]",
        success
          ? "bg-[var(--color-success)]/10 text-[var(--color-success)]"
          : "bg-[var(--color-error)]/10 text-[var(--color-error)]",
      )}
    >
      {success ? (
        <CheckCircleIcon className="h-5 w-5 shrink-0 mt-0.5" />
      ) : (
        <AlertCircleIcon className="h-5 w-5 shrink-0 mt-0.5" />
      )}
      <div className="flex-1">
        <p className="font-medium">{success ? "Success" : "Error"}</p>
        <p className="text-sm mt-1 opacity-90">{message}</p>
      </div>
      <button
        type="button"
        onClick={onDismiss}
        className="text-current hover:opacity-70 transition-opacity"
        aria-label="Dismiss"
      >
        <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
        </svg>
      </button>
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

export function ActionPage({ identity }: ActionPageProps) {
  return (
    <ProtectedRoute>
      <ActionPageContent identity={identity} />
    </ProtectedRoute>
  );
}

function ActionPageContent({ identity }: ActionPageProps) {
  const router = useRouter();
  const { addToast } = useToast();

  const [formData, setFormData] = useState<Record<string, unknown>>({});
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

  const { data: action, isLoading, error, refetch } = useAction(identity);

  const executeAction = useExecuteAction(identity, {
    onSuccess: (result) => {
      setResult({ success: result.success, message: result.message });
      setShowConfirmation(false);

      if (result.success) {
        addToast({
          variant: "success",
          title: "Action Executed",
          description: result.message,
        });

        if (result.redirect) {
          router.push(result.redirect);
        }
      } else {
        addToast({
          variant: "error",
          title: "Action Failed",
          description: result.message,
        });
      }
    },
    onError: (error) => {
      setShowConfirmation(false);
      setResult({ success: false, message: error.message || "Failed to execute action." });
      addToast({
        variant: "error",
        title: "Error",
        description: error.message || "Failed to execute action.",
      });
    },
  });

  // Initialize form data when action loads
  useMemo(() => {
    if (action?.form_fields) {
      const initialData: Record<string, unknown> = {};
      for (const field of action.form_fields) {
        initialData[field.name] = getDefaultValue(field);
      }
      setFormData(initialData);
    }
  }, [action]);

  const displayName = action?.name || formatActionName(identity);

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Actions", href: "/actions" },
      { label: displayName },
    ],
    [displayName],
  );

  const handleFieldChange = useCallback((fieldName: string, value: unknown) => {
    setFormData((prev) => ({ ...prev, [fieldName]: value }));
    setFormErrors((prev) => {
      const next = { ...prev };
      delete next[fieldName];
      return next;
    });
  }, []);

  const validateForm = useCallback((): boolean => {
    if (!action) return false;

    const errors: Record<string, string> = {};

    for (const field of action.form_fields) {
      if (field.required) {
        const value = formData[field.name];
        if (value === undefined || value === null || value === "") {
          errors[field.name] = `${field.label} is required`;
        }
      }
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  }, [action, formData]);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setResult(null);

      if (!validateForm()) return;

      if (action?.requires_confirmation) {
        setShowConfirmation(true);
      } else {
        executeAction.mutate(formData);
      }
    },
    [action, formData, validateForm, executeAction],
  );

  const handleConfirmExecute = useCallback(() => {
    executeAction.mutate(formData);
  }, [executeAction, formData]);

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Loading..." breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <div className="space-y-6">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton variant="text" width={120} />
                    <Skeleton variant="rectangular" height={40} />
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (error || !action) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Action" breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Action"
                message={error?.message || "Action not found."}
                onRetry={() => refetch()}
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
        <PageHeader title={displayName} breadcrumbs={breadcrumbs} />

        {action.dangerous && (
          <div
            className={cn(
              "flex items-center gap-3 p-4 rounded-[var(--radius-lg)]",
              "bg-[var(--color-warning)]/10 border border-[var(--color-warning)]/20",
            )}
          >
            <AlertTriangleIcon className="h-5 w-5 text-[var(--color-warning)] shrink-0" />
            <p className="text-sm text-[var(--color-foreground)]">
              <span className="font-medium">Warning:</span> This action may have significant or
              irreversible effects. Please review carefully before executing.
            </p>
          </div>
        )}

        {result && (
          <ResultDisplay
            success={result.success}
            message={result.message}
            onDismiss={() => setResult(null)}
          />
        )}

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ZapIcon className="h-5 w-5 text-[var(--color-primary)]" />
              <span className="text-lg font-semibold text-[var(--color-foreground)]">
                Execute Action
              </span>
            </div>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-6">
              {action.form_fields.length === 0 ? (
                <p className="text-sm text-[var(--color-muted)]">
                  This action does not require any input parameters.
                </p>
              ) : (
                <div className="space-y-4">
                  {action.form_fields.map((field) => (
                    <DynamicFormField
                      key={field.name}
                      field={field}
                      value={formData[field.name]}
                      onChange={(value) => handleFieldChange(field.name, value)}
                      error={formErrors[field.name]}
                    />
                  ))}
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-[var(--color-border)]">
                <Button type="button" variant="secondary" onClick={() => router.back()}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant={action.dangerous ? "danger" : "primary"}
                  loading={executeAction.isPending}
                  leftIcon={<PlayIcon className="h-4 w-4" />}
                >
                  Execute
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      </div>

      {action.requires_confirmation && (
        <ConfirmationModal
          isOpen={showConfirmation}
          onClose={() => setShowConfirmation(false)}
          onConfirm={handleConfirmExecute}
          isExecuting={executeAction.isPending}
          action={action}
        />
      )}
    </MainLayout>
  );
}

export default ActionPage;
