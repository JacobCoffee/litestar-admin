"use client";

import Link from "next/link";
import { Card, CardBody } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Loading";
import { cn, formatNumber, formatDate } from "@/lib/utils";
import type { ModelStats } from "@/types";

export interface ModelCardProps {
  /** Model statistics */
  model: ModelStats;
  /** Last updated timestamp */
  lastUpdated?: string;
  /** Additional CSS classes */
  className?: string;
}

/**
 * A card showing overview information for a single model.
 * Links to the model's list page.
 */
export function ModelCard({ model, lastUpdated, className }: ModelCardProps) {
  const href = `/models/${model.model_name}`;

  return (
    <Link href={href} className="block group">
      <Card
        className={cn(
          "h-full transition-all duration-200",
          "hover:border-[var(--color-accent)] hover:shadow-md",
          "group-focus-visible:ring-2 group-focus-visible:ring-[var(--color-accent)]",
          className,
        )}
      >
        <CardBody className="flex flex-col gap-4">
          {/* Header with icon and name */}
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--color-primary)]/10">
              <ModelIcon icon={model.icon} />
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-sm font-semibold text-[var(--color-foreground)] truncate group-hover:text-[var(--color-accent)]">
                {model.name}
              </h3>
              {model.category && (
                <p className="text-xs text-[var(--color-muted)] truncate">{model.category}</p>
              )}
            </div>
            <ChevronRightIcon className="h-4 w-4 text-[var(--color-muted)] opacity-0 transition-opacity group-hover:opacity-100" />
          </div>

          {/* Stats */}
          <div className="flex items-end justify-between">
            <div>
              <p className="text-2xl font-semibold text-[var(--color-foreground)]">
                {formatNumber(model.count)}
              </p>
              <p className="text-xs text-[var(--color-muted)]">
                {model.count === 1 ? "record" : "records"}
              </p>
            </div>
            {lastUpdated && (
              <p className="text-xs text-[var(--color-muted)]">Updated {formatDate(lastUpdated)}</p>
            )}
          </div>
        </CardBody>
      </Card>
    </Link>
  );
}

export interface ModelCardSkeletonProps {
  className?: string;
}

/**
 * Skeleton loader for ModelCard component.
 */
export function ModelCardSkeleton({ className }: ModelCardSkeletonProps) {
  return (
    <Card className={className}>
      <CardBody className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <Skeleton variant="circular" width={40} height={40} />
          <div className="flex-1">
            <Skeleton variant="text" width="60%" height={18} />
            <Skeleton variant="text" width="40%" height={14} className="mt-1" />
          </div>
        </div>
        <div className="flex items-end justify-between">
          <div>
            <Skeleton variant="text" width={60} height={28} />
            <Skeleton variant="text" width={40} height={14} className="mt-1" />
          </div>
          <Skeleton variant="text" width={80} height={14} />
        </div>
      </CardBody>
    </Card>
  );
}

interface ModelIconProps {
  icon?: string;
  className?: string;
}

function ModelIcon({ icon, className }: ModelIconProps) {
  // If icon is a known icon name, render the corresponding SVG
  // Otherwise, render a default database icon
  const iconMap: Record<string, React.FC<{ className?: string }>> = {
    user: UserIcon,
    users: UsersIcon,
    settings: SettingsIcon,
    document: DocumentIcon,
    folder: FolderIcon,
    database: DatabaseIcon,
  };

  const IconComponent = icon ? (iconMap[icon.toLowerCase()] ?? DatabaseIcon) : DatabaseIcon;

  return <IconComponent className={cn("h-5 w-5 text-[var(--color-primary)]", className)} />;
}

// Icon components
function UserIcon({ className }: { className?: string }) {
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
        d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
      />
    </svg>
  );
}

function UsersIcon({ className }: { className?: string }) {
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
        d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
      />
    </svg>
  );
}

function SettingsIcon({ className }: { className?: string }) {
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
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

function DocumentIcon({ className }: { className?: string }) {
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
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function FolderIcon({ className }: { className?: string }) {
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
        d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
      />
    </svg>
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
