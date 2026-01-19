"use client";

import { Suspense } from "react";
import { useSearchParams, usePathname } from "next/navigation";
import Link from "next/link";
import { CustomViewListPage } from "@/components/pages/CustomViewListPage";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardBody } from "@/components/ui/Card";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner, Skeleton } from "@/components/ui/Loading";
import { useCustomViews } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

/**
 * Custom views page - handles all custom view routes client-side.
 *
 * Supports both path-based and query param routing:
 * - /custom - Custom views index
 * - /custom/analytics - Analytics custom view list
 * - /custom?view=analytics - Fallback query param
 */
export default function CustomViewsPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <CustomViewsContent />
    </Suspense>
  );
}

interface PathParams {
  view: string | null;
  id: string | null;
}

function parsePathParams(pathname: string): PathParams {
  const normalizedPath = pathname.replace(/^\/admin/, "").replace(/^\/custom\/?/, "");

  if (!normalizedPath) return { view: null, id: null };

  const segments = normalizedPath.split("/").filter(Boolean);
  if (segments.length === 0) return { view: null, id: null };

  const view = segments[0] ?? null;
  const id = segments[1] ?? null;

  return { view, id };
}

function CustomViewsContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const pathParams = parsePathParams(pathname);
  const view = pathParams.view ?? searchParams.get("view");
  // Note: id is parsed but not currently used - reserved for future detail/edit views
  const _id = pathParams.id ?? searchParams.get("id");

  // If a specific view is selected, render it
  if (view) {
    // For now, just show the list page. Later can add detail/edit views.
    return <CustomViewListPage identity={view} />;
  }

  // Show the custom views index
  return <CustomViewsIndexPage />;
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

const GridIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="7" height="7" />
    <rect x="14" y="3" width="7" height="7" />
    <rect x="14" y="14" width="7" height="7" />
    <rect x="3" y="14" width="7" height="7" />
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

function CustomViewsIndexPage() {
  const { data: customViews, isLoading, error } = useCustomViews();

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Custom Views"
          subtitle="Browse custom data views and integrations"
          breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Custom Views" }]}
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
              <p className="text-[var(--color-error)]">
                Failed to load custom views: {error.message}
              </p>
            </CardBody>
          </Card>
        )}

        {!isLoading && !error && customViews && customViews.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {customViews.map((view) => (
              <Link key={view.identity} href={`/custom/${view.identity}`} className="group">
                <Card className="h-full transition-all duration-150 hover:border-[var(--color-primary)] hover:shadow-md">
                  <CardBody className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "flex h-12 w-12 items-center justify-center rounded-lg",
                            "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                          )}
                        >
                          <GridIcon className="h-6 w-6" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-[var(--color-foreground)] group-hover:text-[var(--color-primary)]">
                            {view.name}
                          </h3>
                          <p className="text-sm text-[var(--color-muted)]">{view.identity}</p>
                        </div>
                      </div>
                      <ChevronRightIcon
                        className={cn(
                          "h-5 w-5 text-[var(--color-muted)]",
                          "transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-primary)]",
                        )}
                      />
                    </div>
                    {view.category && (
                      <div className="mt-3">
                        <span
                          className={cn(
                            "inline-flex items-center rounded-full px-2 py-0.5",
                            "text-xs font-medium",
                            "bg-[var(--color-card-hover)] text-[var(--color-muted)]",
                          )}
                        >
                          {view.category}
                        </span>
                      </div>
                    )}
                  </CardBody>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {!isLoading && !error && (!customViews || customViews.length === 0) && (
          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <GridIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                No Custom Views
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Custom views allow you to display non-model data sources with CRUD operations.
                Register custom views in your admin configuration.
              </p>
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
