"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { Breadcrumb, type BreadcrumbItem } from "./Breadcrumb";

export interface PageHeaderProps {
  /** Page title */
  title: string;
  /** Optional subtitle or description */
  subtitle?: string;
  /** Actions slot (buttons, etc.) */
  actions?: ReactNode;
  /** Breadcrumb items */
  breadcrumbs?: readonly BreadcrumbItem[];
  /** Whether to show breadcrumbs */
  showBreadcrumbs?: boolean;
  /** Additional CSS classes for the container */
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  actions,
  breadcrumbs,
  showBreadcrumbs = true,
  className,
}: PageHeaderProps) {
  return (
    <div className={cn("space-y-4", className)}>
      {/* Breadcrumbs */}
      {showBreadcrumbs && breadcrumbs && breadcrumbs.length > 0 && (
        <Breadcrumb items={breadcrumbs} />
      )}

      {/* Title and actions row */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--color-foreground)]">
            {title}
          </h1>
          {subtitle && <p className="mt-1 text-sm text-[var(--color-muted)]">{subtitle}</p>}
        </div>

        {/* Actions */}
        {actions && <div className="flex shrink-0 items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
