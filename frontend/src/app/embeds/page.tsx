"use client";

import { Suspense } from "react";
import { useSearchParams, usePathname } from "next/navigation";
import Link from "next/link";
import { EmbedPage } from "@/components/pages/EmbedPage";
import { MainLayout } from "@/components/layout/MainLayout";
import { Card, CardBody } from "@/components/ui/Card";
import { PageHeader } from "@/components/layout/PageHeader";
import { Spinner, Skeleton } from "@/components/ui/Loading";
import { useEmbeds } from "@/hooks/useApi";
import { cn } from "@/lib/utils";

/**
 * Embeds page - handles all embed routes client-side.
 *
 * Supports both path-based and query param routing:
 * - /embeds - Embeds index
 * - /embeds/grafana - Grafana embed
 * - /embeds?embed=grafana - Fallback query param
 */
export default function EmbedsPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <EmbedsContent />
    </Suspense>
  );
}

function parsePathParams(pathname: string): string | null {
  const normalizedPath = pathname.replace(/^\/admin/, "").replace(/^\/embeds\/?/, "");

  if (!normalizedPath) return null;

  const segments = normalizedPath.split("/").filter(Boolean);
  return segments[0] ?? null;
}

function EmbedsContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const embedFromPath = parsePathParams(pathname);
  const embed = embedFromPath ?? searchParams.get("embed");

  if (embed) {
    return <EmbedPage identity={embed} />;
  }

  return <EmbedsIndexPage />;
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

const LayoutIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
    <line x1="3" y1="9" x2="21" y2="9" />
    <line x1="9" y1="21" x2="9" y2="9" />
  </svg>
);

const CodeIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
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

const ExternalLinkIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

function getEmbedTypeLabel(embedType: string): string {
  switch (embedType) {
    case "iframe":
      return "External Frame";
    case "component":
      return "Custom Component";
    default:
      return embedType;
  }
}

function getLayoutLabel(layout: string): string {
  switch (layout) {
    case "full":
      return "Full Width";
    case "sidebar":
      return "With Sidebar";
    case "card":
      return "Card";
    default:
      return layout;
  }
}

function EmbedsIndexPage() {
  const { data: embeds, isLoading, error } = useEmbeds();

  // Group embeds by category
  const groupedEmbeds = embeds?.reduce(
    (acc, embed) => {
      const category = embed.category || "General";
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(embed);
      return acc;
    },
    {} as Record<string, typeof embeds>,
  );

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Embeds"
          subtitle="External services and custom components"
          breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Embeds" }]}
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
              <p className="text-[var(--color-error)]">Failed to load embeds: {error.message}</p>
            </CardBody>
          </Card>
        )}

        {!isLoading && !error && groupedEmbeds && Object.keys(groupedEmbeds).length > 0 && (
          <div className="space-y-8">
            {Object.entries(groupedEmbeds).map(([category, categoryEmbeds]) => (
              <div key={category}>
                <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-4">
                  {category}
                </h2>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  {categoryEmbeds?.map((embed) => (
                    <Link key={embed.identity} href={`/embeds/${embed.identity}`} className="group">
                      <Card className="h-full transition-all duration-150 hover:border-[var(--color-primary)] hover:shadow-md">
                        <CardBody className="p-4">
                          <div className="flex items-start justify-between">
                            <div className="flex items-center gap-3">
                              <div
                                className={cn(
                                  "flex h-12 w-12 items-center justify-center rounded-lg",
                                  embed.embed_type === "iframe"
                                    ? "bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                                    : "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                                )}
                              >
                                {embed.embed_type === "iframe" ? (
                                  <LayoutIcon className="h-6 w-6" />
                                ) : (
                                  <CodeIcon className="h-6 w-6" />
                                )}
                              </div>
                              <div>
                                <h3 className="font-semibold text-[var(--color-foreground)] group-hover:text-[var(--color-primary)]">
                                  {embed.name}
                                </h3>
                                <p className="text-sm text-[var(--color-muted)]">
                                  {getEmbedTypeLabel(embed.embed_type)}
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
                              {getLayoutLabel(embed.layout)}
                            </span>
                            {embed.embed_type === "iframe" && embed.embed_url && (
                              <span
                                className={cn(
                                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5",
                                  "text-xs font-medium",
                                  "bg-[var(--color-accent)]/10 text-[var(--color-accent)]",
                                )}
                              >
                                <ExternalLinkIcon className="h-3 w-3" />
                                External
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

        {!isLoading && !error && (!embeds || embeds.length === 0) && (
          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <LayoutIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                No Embeds Available
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Embeds allow you to integrate external services like Grafana, Metabase, or custom
                React components into your admin panel. Register embeds in your admin configuration.
              </p>
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
