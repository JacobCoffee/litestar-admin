"use client";

import { Suspense } from "react";
import { useSearchParams, usePathname } from "next/navigation";
import Link from "next/link";
import { ActionPage } from "@/components/pages/ActionPage";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardBody } from "@/components/ui/Card";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner, Skeleton } from "@/components/ui/Loading";
import { useActions } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

/**
 * Actions page - handles all action routes client-side.
 *
 * Supports both path-based and query param routing:
 * - /actions - Actions index
 * - /actions/clear-cache - Execute clear-cache action
 * - /actions?action=clear-cache - Fallback query param
 */
export default function ActionsPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ActionsContent />
    </Suspense>
  );
}

function parsePathParams(pathname: string): string | null {
  const normalizedPath = pathname.replace(/^\/admin/, "").replace(/^\/actions\/?/, "");

  if (!normalizedPath) return null;

  const segments = normalizedPath.split("/").filter(Boolean);
  return segments[0] ?? null;
}

function ActionsContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const actionFromPath = parsePathParams(pathname);
  const action = actionFromPath ?? searchParams.get("action");

  if (action) {
    return <ActionPage identity={action} />;
  }

  return <ActionsIndexPage />;
}

function LoadingFallback() {
  return (
    <MainLayout>
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    </MainLayout>
  );
}

const ZapIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
  </svg>
);

const ChevronRightIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M9 18l6-6-6-6" />
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
  >
    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

function ActionsIndexPage() {
  const { data: actions, isLoading, error } = useActions();

  // Group actions by category
  const groupedActions = actions?.reduce(
    (acc, action) => {
      const category = action.category || "General";
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(action);
      return acc;
    },
    {} as Record<string, typeof actions>,
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Actions"
          subtitle="Execute administrative operations and tasks"
          breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Actions" }]}
        />

        {isLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <Card key={i}>
                <CardBody className="p-4">
                  <Skeleton className="h-12 w-12 rounded-lg mb-3" />
                  <Skeleton className="h-5 w-24 mb-2" />
                  <Skeleton className="h-4 w-32" />
                </CardBody>
              </Card>
            ))}
          </div>
        )}

        {error && (
          <Card>
            <CardBody className="py-12 text-center">
              <p className="text-[var(--color-error)]">Failed to load actions: {error.message}</p>
            </CardBody>
          </Card>
        )}

        {!isLoading && !error && groupedActions && Object.keys(groupedActions).length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedActions).map(([category, categoryActions]) => (
              <div key={category}>
                <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-4">
                  {category}
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryActions?.map((action) => (
                    <Link
                      key={action.identity}
                      href={`/actions/${action.identity}`}
                      className="group"
                    >
                      <Card
                        className={cn(
                          "h-full transition-all duration-150 hover:shadow-md",
                          action.dangerous
                            ? "hover:border-[var(--color-error)]"
                            : "hover:border-[var(--color-primary)]",
                        )}
                      >
                        <CardBody className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <div
                                className={cn(
                                  "flex h-12 w-12 items-center justify-center rounded-lg",
                                  action.dangerous
                                    ? "bg-[var(--color-error)]/10 text-[var(--color-error)]"
                                    : "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                                )}
                              >
                                {action.dangerous ? (
                                  <AlertTriangleIcon className="h-6 w-6" />
                                ) : (
                                  <ZapIcon className="h-6 w-6" />
                                )}
                              </div>
                              <div>
                                <h3
                                  className={cn(
                                    "font-semibold text-[var(--color-foreground)]",
                                    action.dangerous
                                      ? "group-hover:text-[var(--color-error)]"
                                      : "group-hover:text-[var(--color-primary)]",
                                  )}
                                >
                                  {action.name}
                                </h3>
                                <p className="text-sm text-[var(--color-muted)]">
                                  {action.form_fields.length} field
                                  {action.form_fields.length !== 1 ? "s" : ""}
                                </p>
                              </div>
                            </div>
                            <ChevronRightIcon
                              className={cn(
                                "h-5 w-5 text-[var(--color-muted)]",
                                "transition-transform group-hover:translate-x-1",
                                action.dangerous
                                  ? "group-hover:text-[var(--color-error)]"
                                  : "group-hover:text-[var(--color-primary)]",
                              )}
                            />
                          </div>
                          {(action.dangerous || action.requires_confirmation) && (
                            <div className="mt-3 flex items-center gap-2">
                              {action.dangerous && (
                                <span
                                  className={cn(
                                    "inline-flex items-center rounded-full px-2 py-0.5",
                                    "text-xs font-medium",
                                    "bg-[var(--color-error)]/10 text-[var(--color-error)]",
                                  )}
                                >
                                  Dangerous
                                </span>
                              )}
                              {action.requires_confirmation && (
                                <span
                                  className={cn(
                                    "inline-flex items-center rounded-full px-2 py-0.5",
                                    "text-xs font-medium",
                                    "bg-[var(--color-warning)]/10 text-[var(--color-warning)]",
                                  )}
                                >
                                  Requires confirmation
                                </span>
                              )}
                            </div>
                          )}
                        </CardBody>
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && !error && (!actions || actions.length === 0) && (
          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <ZapIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                No Actions Available
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Actions allow administrators to execute operations like cache clearing, data
                imports, or maintenance tasks. Register actions in your admin configuration.
              </p>
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
