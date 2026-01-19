"use client";

import { useMemo, useEffect, useRef } from "react";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import type { BreadcrumbItem } from "@/components/layout/Breadcrumb";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Loading";
import { usePage, usePageContent } from "@/hooks/useApi";
import { cn, toTitleCase } from "@/lib/utils";
import type { PageContentType } from "@/types";

// ============================================================================
// Types
// ============================================================================

export interface ContentPageProps {
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

const RefreshIcon = ({ className }: { className?: string }) => (
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
    <polyline points="23 4 23 10 17 10" />
    <polyline points="1 20 1 14 7 14" />
    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
  </svg>
);

const FileTextIcon = ({ className }: { className?: string }) => (
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
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
    <line x1="16" y1="13" x2="8" y2="13" />
    <line x1="16" y1="17" x2="8" y2="17" />
    <polyline points="10 9 9 9 8 9" />
  </svg>
);

// ============================================================================
// Helper Functions
// ============================================================================

function formatPageName(identity: string): string {
  return toTitleCase(identity.replace(/[-_]/g, " "));
}

// ============================================================================
// Content Renderers
// ============================================================================

interface MarkdownRendererProps {
  content: string;
}

function MarkdownRenderer({ content }: MarkdownRendererProps) {
  // Simple markdown-to-HTML conversion
  // For production, consider using a library like marked or remark
  const html = useMemo(() => {
    let processed = content
      // Headers
      .replace(/^### (.+)$/gm, '<h3 class="text-lg font-semibold mt-6 mb-3">$1</h3>')
      .replace(/^## (.+)$/gm, '<h2 class="text-xl font-semibold mt-8 mb-4">$1</h2>')
      .replace(/^# (.+)$/gm, '<h1 class="text-2xl font-bold mt-8 mb-4">$1</h1>')
      // Bold and italic
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      // Code blocks
      .replace(
        /```(\w*)\n([\s\S]*?)```/g,
        (_match, _lang, code) =>
          `<pre class="bg-[var(--color-card-hover)] p-4 rounded-[var(--radius-md)] overflow-x-auto my-4"><code>${code.trim()}</code></pre>`,
      )
      // Inline code
      .replace(
        /`([^`]+)`/g,
        '<code class="bg-[var(--color-card-hover)] px-1.5 py-0.5 rounded text-sm">$1</code>',
      )
      // Links
      .replace(
        /\[(.+?)\]\((.+?)\)/g,
        '<a href="$2" class="text-[var(--color-accent)] hover:underline">$1</a>',
      )
      // Unordered lists
      .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
      // Ordered lists
      .replace(/^\d+\. (.+)$/gm, '<li class="ml-4 list-decimal">$1</li>')
      // Blockquotes
      .replace(
        /^> (.+)$/gm,
        '<blockquote class="border-l-4 border-[var(--color-border)] pl-4 my-4 italic text-[var(--color-muted)]">$1</blockquote>',
      )
      // Horizontal rules
      .replace(/^---$/gm, '<hr class="my-6 border-[var(--color-border)]" />')
      // Paragraphs (wrap remaining text)
      .replace(/^(?!<[hpuolbhc])(.+)$/gm, '<p class="my-3">$1</p>');

    // Wrap consecutive list items
    processed = processed.replace(
      /(<li[^>]*>.*<\/li>\n?)+/g,
      (match) => `<ul class="my-4 space-y-1">${match}</ul>`,
    );

    return processed;
  }, [content]);

  return (
    <div
      className="prose prose-invert max-w-none text-[var(--color-foreground)]"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

interface HtmlRendererProps {
  content: string;
}

function HtmlRenderer({ content }: HtmlRendererProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Execute any scripts in the HTML content
    if (containerRef.current) {
      const scripts = containerRef.current.querySelectorAll("script");
      scripts.forEach((script) => {
        const newScript = document.createElement("script");
        Array.from(script.attributes).forEach((attr) => {
          newScript.setAttribute(attr.name, attr.value);
        });
        newScript.textContent = script.textContent;
        script.parentNode?.replaceChild(newScript, script);
      });
    }
  }, [content]);

  return (
    <div
      ref={containerRef}
      className="prose prose-invert max-w-none text-[var(--color-foreground)]"
      dangerouslySetInnerHTML={{ __html: content }}
    />
  );
}

interface TextRendererProps {
  content: string;
}

function TextRenderer({ content }: TextRendererProps) {
  return (
    <pre className="whitespace-pre-wrap font-mono text-sm text-[var(--color-foreground)]">
      {content}
    </pre>
  );
}

interface ContentRendererProps {
  content: string;
  contentType: PageContentType;
}

function ContentRenderer({ content, contentType }: ContentRendererProps) {
  switch (contentType) {
    case "markdown":
      return <MarkdownRenderer content={content} />;
    case "html":
      return <HtmlRenderer content={content} />;
    case "text":
      return <TextRenderer content={content} />;
    case "dynamic":
    case "template":
      // Dynamic content is already rendered by the backend
      return <HtmlRenderer content={content} />;
    default:
      return <TextRenderer content={content} />;
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

interface EmptyStateProps {
  pageName: string;
}

function EmptyState({ pageName }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div
        className={cn(
          "w-16 h-16 mb-4 rounded-full",
          "bg-[var(--color-card-hover)]",
          "flex items-center justify-center",
        )}
      >
        <FileTextIcon className="h-8 w-8 text-[var(--color-muted)]" />
      </div>
      <h3 className="text-lg font-medium text-[var(--color-foreground)] mb-2">
        No Content Available
      </h3>
      <p className="text-sm text-[var(--color-muted)] max-w-md">
        The {pageName.toLowerCase()} page does not have any content yet.
      </p>
    </div>
  );
}

interface RefreshIndicatorProps {
  interval: number;
}

function RefreshIndicator({ interval }: RefreshIndicatorProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-[var(--color-muted)]">
      <RefreshIcon className="h-3 w-3 animate-spin" />
      <span>Auto-refreshes every {interval / 1000}s</span>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function ContentPage({ identity }: ContentPageProps) {
  return (
    <ProtectedRoute>
      <ContentPageContent identity={identity} />
    </ProtectedRoute>
  );
}

function ContentPageContent({ identity }: ContentPageProps) {
  const {
    data: pageInfo,
    isLoading: isLoadingPage,
    error: pageError,
    refetch: refetchPage,
  } = usePage(identity);

  const {
    data: pageContent,
    isLoading: isLoadingContent,
    error: contentError,
    refetch: refetchContent,
  } = usePageContent(identity, pageInfo?.refresh_interval, {
    enabled:
      !!pageInfo && (pageInfo.content_type === "dynamic" || pageInfo.content_type === "template"),
  });

  const displayName = pageInfo?.name || formatPageName(identity);
  const hasError = pageError || contentError;

  // Determine the content to display
  const content = useMemo(() => {
    if (pageInfo?.content_type === "dynamic" || pageInfo?.content_type === "template") {
      return pageContent?.content || "";
    }
    return pageInfo?.content || "";
  }, [pageInfo, pageContent]);

  const contentType = pageContent?.content_type || pageInfo?.content_type || "text";

  const breadcrumbs: BreadcrumbItem[] = useMemo(
    () => [
      { label: "Dashboard", href: "/" },
      { label: "Pages", href: "/pages" },
      { label: displayName },
    ],
    [displayName],
  );

  // Layout classes based on page layout
  const layoutClasses = useMemo(() => {
    switch (pageInfo?.layout) {
      case "full-width":
        return "max-w-none";
      case "sidebar":
        return "max-w-4xl";
      default:
        return "max-w-5xl";
    }
  }, [pageInfo?.layout]);

  if (isLoadingPage) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Loading..." breadcrumbs={breadcrumbs} />
          <Card className={layoutClasses}>
            <CardBody>
              <div className="space-y-4">
                <Skeleton variant="text" />
                <Skeleton variant="text" />
                <Skeleton variant="text" width="80%" />
                <Skeleton variant="rectangular" height={200} className="mt-6" />
                <Skeleton variant="text" />
                <Skeleton variant="text" width="60%" />
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
          <PageHeader title="Page" breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState
                title="Unable to Load Page"
                message={pageError?.message || contentError?.message || "Page not found."}
                onRetry={() => {
                  refetchPage();
                  refetchContent();
                }}
              />
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    );
  }

  if (!pageInfo) {
    return (
      <MainLayout>
        <div className="space-y-6">
          <PageHeader title="Page" breadcrumbs={breadcrumbs} />
          <Card>
            <CardBody>
              <ErrorState title="Page Not Found" message="The requested page does not exist." />
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
          title={displayName}
          breadcrumbs={breadcrumbs}
          actions={
            pageInfo.refresh_interval ? (
              <RefreshIndicator interval={pageInfo.refresh_interval} />
            ) : undefined
          }
        />

        <Card className={layoutClasses}>
          <CardBody>
            {isLoadingContent ? (
              <div className="space-y-4">
                <Skeleton variant="text" />
                <Skeleton variant="text" />
                <Skeleton variant="text" width="80%" />
              </div>
            ) : !content ? (
              <EmptyState pageName={displayName} />
            ) : (
              <ContentRenderer content={content} contentType={contentType} />
            )}
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}

export default ContentPage;
