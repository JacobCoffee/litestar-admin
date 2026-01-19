"use client";

import { useMemo, type ReactNode } from "react";

import { useAuthContext } from "@/contexts/AuthContext";
import { Card, CardBody } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

/**
 * Props for AuthGuard component.
 */
export interface AuthGuardProps {
  /** The content to render when authorized */
  children: ReactNode;
  /** Required permissions (user must have at least one) */
  requiredPermissions?: string[];
  /** Required roles (user must have at least one) */
  requiredRoles?: string[];
  /** Require ALL permissions instead of ANY (default: false) */
  requireAllPermissions?: boolean;
  /** Custom component to show when access is denied */
  fallback?: ReactNode;
  /** Whether to hide the content completely instead of showing fallback */
  hideOnDenied?: boolean;
}

/**
 * Lock icon for access denied state.
 */
function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

/**
 * Default access denied component.
 */
function DefaultAccessDenied() {
  return (
    <Card variant="default" className="max-w-md mx-auto">
      <CardBody>
        <div className="flex flex-col items-center gap-4 py-6 text-center">
          <div
            className={cn(
              "flex h-16 w-16 items-center justify-center rounded-full",
              "bg-[var(--color-error)]/10",
            )}
          >
            <LockIcon className="h-8 w-8 text-[var(--color-error)]" />
          </div>
          <div className="space-y-2">
            <h3 className="text-lg font-semibold text-[var(--color-foreground)]">Access Denied</h3>
            <p className="text-sm text-[var(--color-muted)]">
              You do not have permission to view this content. Please contact your administrator if
              you believe this is an error.
            </p>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}

/**
 * Component that guards its children based on user permissions and roles.
 * Shows an access denied message if the user lacks required permissions.
 *
 * @example
 * ```tsx
 * // Require any of the specified permissions
 * <AuthGuard requiredPermissions={['users:read', 'users:admin']}>
 *   <UserList />
 * </AuthGuard>
 *
 * // Require ALL permissions
 * <AuthGuard
 *   requiredPermissions={['users:read', 'users:write']}
 *   requireAllPermissions
 * >
 *   <UserEditor />
 * </AuthGuard>
 *
 * // Require specific roles
 * <AuthGuard requiredRoles={['admin', 'superuser']}>
 *   <AdminPanel />
 * </AuthGuard>
 *
 * // Hide content completely instead of showing fallback
 * <AuthGuard requiredPermissions={['admin']} hideOnDenied>
 *   <AdminOnlyButton />
 * </AuthGuard>
 *
 * // Custom fallback
 * <AuthGuard
 *   requiredPermissions={['premium']}
 *   fallback={<UpgradePrompt />}
 * >
 *   <PremiumFeature />
 * </AuthGuard>
 * ```
 */
export function AuthGuard({
  children,
  requiredPermissions = [],
  requiredRoles = [],
  requireAllPermissions = false,
  fallback,
  hideOnDenied = false,
}: AuthGuardProps) {
  const { user, hasAllPermissions, hasAnyPermission, hasAnyRole } = useAuthContext();

  const isAuthorized = useMemo(() => {
    // If no requirements specified, allow access
    if (requiredPermissions.length === 0 && requiredRoles.length === 0) {
      return true;
    }

    // User must be authenticated
    if (!user) {
      return false;
    }

    // Check permissions
    let hasRequiredPermissions = true;
    if (requiredPermissions.length > 0) {
      hasRequiredPermissions = requireAllPermissions
        ? hasAllPermissions(requiredPermissions)
        : hasAnyPermission(requiredPermissions);
    }

    // Check roles
    let hasRequiredRoles = true;
    if (requiredRoles.length > 0) {
      hasRequiredRoles = hasAnyRole(requiredRoles);
    }

    // Must satisfy both permission and role requirements
    return hasRequiredPermissions && hasRequiredRoles;
  }, [
    user,
    requiredPermissions,
    requiredRoles,
    requireAllPermissions,
    hasAllPermissions,
    hasAnyPermission,
    hasAnyRole,
  ]);

  // If authorized, render children
  if (isAuthorized) {
    return <>{children}</>;
  }

  // If hideOnDenied is true, render nothing
  if (hideOnDenied) {
    return null;
  }

  // Show fallback or default access denied
  return <>{fallback ?? <DefaultAccessDenied />}</>;
}

/**
 * Hook to check if the current user is authorized for specific permissions/roles.
 * Useful for conditional rendering without wrapping in AuthGuard.
 *
 * @example
 * ```tsx
 * const canEdit = useIsAuthorized({ permissions: ['users:write'] });
 *
 * return (
 *   <div>
 *     <ViewUser user={user} />
 *     {canEdit && <EditButton onClick={handleEdit} />}
 *   </div>
 * );
 * ```
 */
export function useIsAuthorized(options: {
  permissions?: string[];
  roles?: string[];
  requireAllPermissions?: boolean;
}): boolean {
  const { user, hasAllPermissions, hasAnyPermission, hasAnyRole } = useAuthContext();

  const { permissions = [], roles = [], requireAllPermissions = false } = options;

  return useMemo(() => {
    if (permissions.length === 0 && roles.length === 0) {
      return true;
    }

    if (!user) {
      return false;
    }

    let hasRequiredPermissions = true;
    if (permissions.length > 0) {
      hasRequiredPermissions = requireAllPermissions
        ? hasAllPermissions(permissions)
        : hasAnyPermission(permissions);
    }

    let hasRequiredRoles = true;
    if (roles.length > 0) {
      hasRequiredRoles = hasAnyRole(roles);
    }

    return hasRequiredPermissions && hasRequiredRoles;
  }, [
    user,
    permissions,
    roles,
    requireAllPermissions,
    hasAllPermissions,
    hasAnyPermission,
    hasAnyRole,
  ]);
}
