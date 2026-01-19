"use client";

import { Suspense } from "react";
import { useSearchParams, usePathname } from "next/navigation";
import Link from "next/link";
import { ContentPage } from "@/components/pages/ContentPage";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardBody } from "@/components/ui/Card";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner, Skeleton } from "@/components/ui/Loading";
import { usePages } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

/**
 * Pages page - handles all content page routes client-side.
 *
 * Supports both path-based and query param routing:
 * - /pages - Pages index
 * - /pages/help - Help content page
 * - /pages?page=help - Fallback query param
 */
export default function PagesPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <PagesContent />
    </Suspense>
  );
}

function parsePathParams(pathname: string): string | null {
  const normalizedPath = pathname.replace(/^\/admin/, "").replace(/^\/pages\/?/, "");

  if (!normalizedPath) return null;

  const segments = normalizedPath.split("/").filter(Boolean);
  return segments[0] ?? null;
}

function PagesContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const pageFromPath = parsePathParams(pathname);
  const page = pageFromPath ?? searchParams.get("page");

  if (page) {
    return <ContentPage identity={page} />;
  }

  return <PagesIndexPage />;
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

const FileTextIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
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

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="23 4 23 10 17 10" />
    <polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

function getContentTypeLabel(contentType: string): string {
  switch (contentType) {
    case "markdown":
      return "Markdown";
    case "html":
      return "HTML";
    case "text":
      return "Plain Text";
    case "dynamic":
      return "Dynamic";
    case "template":
      return "Template";
    default:
      return contentType;
  }
}

function PagesIndexPage() {
  const { data: pages, isLoading, error } = usePages();

  // Group pages by category
  const groupedPages = pages?.reduce(
    (acc, page) => {
      const category = page.category || "General";
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(page);
      return acc;
    },
    {} as Record<string, typeof pages>,
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Pages"
          subtitle="Browse documentation and content pages"
          breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Pages" }]}
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
              <p className="text-[var(--color-error)]">Failed to load pages: {error.message}</p>
            </CardBody>
          </Card>
        )}

        {!isLoading && !error && groupedPages && Object.keys(groupedPages).length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedPages).map(([category, categoryPages]) => (
              <div key={category}>
                <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-4">
                  {category}
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryPages?.map((page) => (
                    <Link key={page.identity} href={`/pages/${page.identity}`} className="group">
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
                                <FileTextIcon className="h-6 w-6" />
                              </div>
                              <div>
                                <h3 className="font-semibold text-[var(--color-foreground)] group-hover:text-[var(--color-primary)]">
                                  {page.name}
                                </h3>
                                <p className="text-sm text-[var(--color-muted)]">
                                  {getContentTypeLabel(page.content_type)}
                                </p>
                              </div>
                            </div>
                            <ChevronRightIcon
                              className={cn(
                                "h-5 w-5 text-[var(--color-muted)]",
                                "transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-primary)]",
                              )}
                            />
                          </div>
                          <div className="mt-3 flex items-center gap-2">
                            <span
                              className={cn(
                                "inline-flex items-center rounded-full px-2 py-0.5",
                                "text-xs font-medium",
                                "bg-[var(--color-card-hover)] text-[var(--color-muted)]",
                              )}
                            >
                              {page.layout}
                            </span>
                            {page.refresh_interval && (
                              <span
                                className={cn(
                                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                                  "text-xs font-medium",
                                  "bg-[var(--color-success)]/10 text-[var(--color-success)]",
                                )}
                              >
                                <RefreshIcon className="h-3 w-3" />
                                Auto-refresh
                              </span>
                            )}
                          </div>
                        </CardBody>
                      </Card>
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {!isLoading && !error && (!pages || pages.length === 0) && (
          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <FileTextIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                No Pages Available
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Pages allow you to display static or dynamic content like documentation, help text,
                or system information. Register pages in your admin configuration.
              </p>
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
