"use client";

import { cn } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

export type UserStatus = "active" | "inactive" | "superuser";

export interface UserStatusBadgeProps {
  /** Whether the user is active */
  isActive: boolean;
  /** Whether the user is a superuser */
  isSuperuser?: boolean;
  /** Display size variant */
  size?: "sm" | "md";
  /** Additional CSS classes */
  className?: string;
}

// ============================================================================
// Icons
// ============================================================================

function CheckCircleIcon({ className }: { className?: string }) {
  return (
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
      <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
      <polyline points="22,4 12,14.01 9,11.01" />
    </svg>
  );
}

function XCircleIcon({ className }: { className?: string }) {
  return (
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
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function ShieldCheckIcon({ className }: { className?: string }) {
  return (
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
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function UserStatusBadge({
  isActive,
  isSuperuser = false,
  size = "md",
  className,
}: UserStatusBadgeProps) {
  // Determine the status to display
  const status: UserStatus = isSuperuser ? "superuser" : isActive ? "active" : "inactive";

  const statusConfig = {
    active: {
      label: "Active",
      icon: CheckCircleIcon,
      colors: "bg-[var(--color-success)]/10 text-[var(--color-success)] border-[var(--color-success)]/20",
    },
    inactive: {
      label: "Inactive",
      icon: XCircleIcon,
      colors: "bg-[var(--color-muted)]/10 text-[var(--color-muted)] border-[var(--color-muted)]/20",
    },
    superuser: {
      label: "Superuser",
      icon: ShieldCheckIcon,
      colors: "bg-[var(--color-warning)]/10 text-[var(--color-warning)] border-[var(--color-warning)]/20",
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  const sizeClasses = {
    sm: "h-5 px-1.5 text-xs gap-1",
    md: "h-6 px-2 text-xs gap-1.5",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center",
        "rounded-full border",
        "font-medium",
        sizeClasses[size],
        config.colors,
        className,
      )}
    >
      <Icon className={cn(size === "sm" ? "h-3 w-3" : "h-3.5 w-3.5")} />
      <span>{config.label}</span>
    </span>
  );
}

UserStatusBadge.displayName = "UserStatusBadge";

// ============================================================================
// Role Badge Component
// ============================================================================

export interface RoleBadgeProps {
  /** The role name to display */
  role: string;
  /** Display size variant */
  size?: "sm" | "md";
  /** Additional CSS classes */
  className?: string;
}

export function RoleBadge({ role, size = "md", className }: RoleBadgeProps) {
  const sizeClasses = {
    sm: "h-5 px-1.5 text-xs",
    md: "h-6 px-2 text-xs",
  };

  return (
    <span
      className={cn(
        "inline-flex items-center",
        "rounded-full",
        "font-medium capitalize",
        "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
        sizeClasses[size],
        className,
      )}
    >
      {role}
    </span>
  );
}

RoleBadge.displayName = "RoleBadge";
