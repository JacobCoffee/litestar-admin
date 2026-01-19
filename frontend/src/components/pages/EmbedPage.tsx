"use client";

import { useMemo, useState, useCallback } from "react";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton, Spinner } from "@/components/ui/Loading";
import { useEmbeds, useEmbedConfig } from "@/hooks/useApi";
import { cn, toTitleCase } from "@/lib/utils";
import type { EmbedInfo, EmbedLayout } from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface EmbedPageProps {
  identity: string;
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
    aria-hidden="true"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M12 8v4M12 16h.01" />
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
    aria-hidden="true"
  >
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
    <polyline points="15 3 21 3 21 9" />
    <line x1="10" y1="14" x2="21" y2="3" />
  </svg>
);

const MaximizeIcon = ({ className }: { className?: string }) => (
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
    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3" />
  </svg>
);

const MinimizeIcon = ({ className }: { className?: string }) => (
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
    <path d="M4 14h6m0 0v6m0-6L3 21m17-11h-6m0 0V4m0 6l7-7" />
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
    aria-hidden="true"
  >
    <polyline points="16 18 22 12 16 6" />
    <polyline points="8 6 2 12 8 18" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatEmbedName(identity: string): string {
  return toTitleCase(identity.replace(/[-_]/g, " "));
}

function getLayoutClasses(layout: EmbedLayout): string {
  switch (layout) {
    case "full":
      return "h-[calc(100vh-12rem)]";
    case "sidebar":
      return "h-[600px] max-w-4xl";
    case "card":
      return "h-[400px] max-w-2xl";
    default:
      return "h-[600px]";
  }
}

// ============================================================================
// Sub-Components
// ============================================================================

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

interface IframeEmbedProps {
  url: string;
  sandbox?: string | null;
  allow?: string | null;
  width: string;
  height: string;
  title: string;
  layout: EmbedLayout;
}

function IframeEmbed({ url, sandbox, allow, title, layout }: IframeEmbedProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [hasError, setHasError] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const handleLoad = useCallback(() => {
    setIsLoading(false);
    setHasError(false);
  }, []);

  const handleError = useCallback(() => {
    setIsLoading(false);
    setHasError(true);
  }, []);

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  const openInNewTab = useCallback(() => {
    window.open(url, "_blank", "noopener,noreferrer");
  }, [url]);

  const containerClasses = isFullscreen
    ? "fixed inset-0 z-50 bg-[var(--color-background)]"
    : cn("relative rounded-[var(--radius-lg)] overflow-hidden", getLayoutClasses(layout));

  return (
    <div className={containerClasses}>
      {/* Toolbar */}
      <div
        className={cn(
          "flex items-center justify-between px-3 py-2",
          "bg-[var(--color-card)] border-b border-[var(--color-border)]",
        )}
      >
        <span className="text-sm text-[var(--color-muted)] truncate max-w-[60%]">{url}</span>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={openInNewTab}
            className={cn(
              "p-1.5 rounded-[var(--radius-md)]",
              "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
              "hover:bg-[var(--color-card-hover)]",
              "transition-colors duration-150",
            )}
            title="Open in new tab"
            aria-label="Open in new tab"
          >
            <ExternalLinkIcon className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            className={cn(
              "p-1.5 rounded-[var(--radius-md)]",
              "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
              "hover:bg-[var(--color-card-hover)]",
              "transition-colors duration-150",
            )}
            title={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
            aria-label={isFullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <MinimizeIcon className="h-4 w-4" />
            ) : (
              <MaximizeIcon className="h-4 w-4" />
            )}
          </button>
        </div>
      </div>

      {/* Iframe container */}
      <div className="relative flex-1 h-[calc(100%-44px)]">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-card)]">
            <Spinner size="lg" />
          </div>
        )}

        {hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-[var(--color-card)]">
            <ErrorState
              title="Failed to Load"
              message="The embedded content could not be loaded. It may be blocked by the content security policy."
              onRetry={() => {
                setIsLoading(true);
                setHasError(false);
              }}
            />
          </div>
        )}

        <iframe
          src={url}
          title={title}
          className={cn("w-full h-full border-0", isLoading && "invisible")}
          sandbox={sandbox ?? undefined}
          allow={allow ?? undefined}
          onLoad={handleLoad}
          onError={handleError}
        />
      </div>

      {/* Fullscreen close overlay */}
      {isFullscreen && (
        <button
          type="button"
          onClick={toggleFullscreen}
          className={cn(
            "absolute top-4 right-4 z-10",
            "px-3 py-1.5 rounded-[var(--radius-md)]",
            "bg-[var(--color-card)] text-[var(--color-foreground)]",
            "border border-[var(--color-border)]",
            "hover:bg-[var(--color-card-hover)]",
            "transition-colors duration-150",
            "text-sm font-medium",
          )}
        >
          Exit Fullscreen (Esc)
        </button>
      )}
    </div>
  );
}

interface ComponentEmbedProps {
  componentName: string;
  layout: EmbedLayout;
}

function ComponentEmbed({ componentName, layout }: ComponentEmbedProps) {
  // In a real implementation, this would dynamically load and render
  // a registered React component. For now, we show a placeholder.
  return (
    <div
      className={cn(
        "rounded-[var(--radius-lg)] overflow-hidden",
        "bg-[var(--color-card)] border border-[var(--color-border)]",
        getLayoutClasses(layout),
      )}
    >
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div
          className={cn(
            "w-16 h-16 mb-4 rounded-full",
            "bg-[var(--color-card-hover)]",
            "flex items-center justify-center",
          )}
        >
          <CodeIcon className="h-8 w-8 text-[var(--color-muted)]" />
        </div>
        <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-2">
          Custom Component
        </h3>
        <p className="text-sm text-[var(--color-muted)] max-w-md">
          Component:{" "}
          <code className="bg-[var(--color-card-hover)] px-1.5 py-0.5 rounded text-sm">
            {componentName}
          </code>
        </p>
        <p className="text-xs text-[var(--color-muted)] mt-2">
          Custom components can be registered and rendered here.
        </p>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function EmbedPage({ identity }: EmbedPageProps) {
  return (
    <ProtectedRoute>
      <EmbedPageContent identity={identity} />
    </ProtectedRoute>
  );
}

function EmbedPageContent({ identity }: EmbedPageProps) {
  const { data: embeds, isLoading: isLoadingEmbeds, error: embedsError } = useEmbeds();

  const {
    data: config,
    isLoading: isLoadingConfig,
    error: configError,
    refetch: refetchConfig,
  } = useEmbedConfig(identity);

  // Find the embed info from the list
  const embedInfo = useMemo<EmbedInfo | undefined>(() => {
    return embeds?.find((e) => e.identity === identity);
  }, [embeds, identity]);

  const displayName = embedInfo?.name || formatEmbedName(identity);
  const isLoading = isLoadingEmbeds || isLoadingConfig;
  const hasError = embedsError || configError;

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Embeds", href: "/embeds" },
      { label: displayName },
    ],
    [displayName],
  );

  if (isLoading) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Loading..." breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody className="p-0">
              <Skeleton variant="rectangular" height={500} />
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
          <PageHeader title="Embed" breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Embed"
                message={embedsError?.message || configError?.message || "Embed not found."}
                onRetry={() => refetchConfig()}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (!embedInfo) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Embed" breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState title="Embed Not Found" message="The requested embed does not exist." />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  const layout = embedInfo.layout || "full";

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader title={displayName} breadcrumbs={breadcrumbs} />

        {embedInfo.embed_type === "iframe" && config?.url ? (
          <IframeEmbed
            url={config.url}
            sandbox={config.sandbox}
            allow={config.allow}
            width={config.width}
            height={config.height}
            title={displayName}
            layout={layout}
          />
        ) : embedInfo.embed_type === "component" && embedInfo.component_name ? (
          <ComponentEmbed componentName={embedInfo.component_name} layout={layout} />
        ) : (
          <Card>
            <CardBody>
              <ErrorState
                title="Invalid Embed Configuration"
                message="The embed is missing required configuration (URL or component name)."
              />
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}

export default EmbedPage;
