"use client";

import Link from "next/link";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { ModelCard, ModelCardSkeleton } from "./ModelCard";
import { cn } from "@/lib/utils";
import type { ModelStats } from "@/types";

export interface ModelOverviewProps {
  /** Array of model statistics */
  models?: readonly ModelStats[];
  /** Whether data is loading */
  isLoading?: boolean;
  /** Maximum number of models to display */
  maxModels?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * A grid of model cards showing an overview of all registered models.
 */
export function ModelOverview({
  models,
  isLoading = false,
  maxModels,
  className,
}: ModelOverviewProps) {
  if (isLoading) {
    return <ModelOverviewSkeleton count={6} className={className} />;
  }

  const displayModels = maxModels ? models?.slice(0, maxModels) : models;
  const hasMoreModels = maxModels && models && models.length > maxModels;

  if (!displayModels || displayModels.length === 0) {
    return <EmptyModelsState className={className} />;
  }

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-foreground)]">Model Overview</h2>
          <p className="mt-0.5 text-sm text-[var(--color-muted)]">
            {models?.length ?? 0} registered model{(models?.length ?? 0) === 1 ? "" : "s"}
          </p>
        </div>
        <Link
          href="/models"
          className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent)]/80"
        >
          View all models
        </Link>
      </div>

      {/* Model cards grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {displayModels.map((model) => (
          <ModelCard key={model.model_name} model={model} lastUpdated={new Date().toISOString()} />
        ))}
      </div>

      {/* Show more link */}
      {hasMoreModels && (
        <div className="flex justify-center pt-2">
          <Link
            href="/models"
            className={cn(
              "inline-flex items-center gap-2 px-4 py-2 rounded-lg",
              "text-sm font-medium text-[var(--color-accent)]",
              "hover:bg-[var(--color-card-hover)] transition-colors",
            )}
          >
            View {models.length - maxModels} more models
            <ChevronRightIcon className="h-4 w-4" />
          </Link>
        </div>
      )}
    </div>
  );
}

interface ModelOverviewSkeletonProps {
  count?: number;
  className?: string | undefined;
}

function ModelOverviewSkeleton({ count = 6, className }: ModelOverviewSkeletonProps) {
  return (
    <div className={cn("space-y-4", className)}>
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <div className="h-5 w-32 animate-pulse rounded bg-[var(--color-card-hover)]" />
          <div className="h-4 w-24 animate-pulse rounded bg-[var(--color-card-hover)]" />
        </div>
        <div className="h-4 w-24 animate-pulse rounded bg-[var(--color-card-hover)]" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: count }).map((_, i) => (
          <ModelCardSkeleton key={i} />
        ))}
      </div>
    </div>
  );
}

interface EmptyModelsStateProps {
  className?: string | undefined;
}

function EmptyModelsState({ className }: EmptyModelsStateProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <h2 className="text-base font-semibold text-[var(--color-foreground)]">Model Overview</h2>
      </CardHeader>
      <CardBody>
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-card-hover)]">
            <DatabaseIcon className="h-8 w-8 text-[var(--color-muted)]" />
          </div>
          <p className="mt-4 text-sm font-medium text-[var(--color-foreground)]">
            No models registered
          </p>
          <p className="mt-1 max-w-sm text-sm text-[var(--color-muted)]">
            Register your SQLAlchemy models with the admin panel to see them here.
          </p>
          <Link
            href="/docs/getting-started"
            className={cn(
              "mt-4 inline-flex items-center gap-2",
              "text-sm font-medium text-[var(--color-accent)]",
              "hover:text-[var(--color-accent)]/80",
            )}
          >
            Learn how to register models
            <ChevronRightIcon className="h-4 w-4" />
          </Link>
        </div>
      </CardBody>
    </Card>
  );
}

function DatabaseIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
      />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
    </svg>
  );
}
