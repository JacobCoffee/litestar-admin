"use client";

import { useEffect, type ReactNode } from "react";
import { useRouter, usePathname } from "next/navigation";

import { useAuthContext } from "@/contexts/AuthContext";
import { Spinner } from "@/components/ui/Loading";
import { cn } from "@/lib/utils";

/**
 * Props for ProtectedRoute component.
 */
export interface ProtectedRouteProps {
  /** The content to render when authenticated */
  children: ReactNode;
  /** Custom loading component to show while checking auth */
  loadingComponent?: ReactNode;
  /** URL to redirect to when not authenticated (default: /login) */
  loginUrl?: string;
  /** Whether to include return URL in redirect query params */
  includeReturnUrl?: boolean;
}

/**
 * Default loading component shown while checking authentication.
 */
function DefaultLoadingComponent() {
  return (
    <div
      className={cn(
        "flex min-h-screen items-center justify-center",
        "bg-[var(--color-background)]",
      )}
    >
      <div className="flex flex-col items-center gap-4">
        <Spinner size="xl" />
        <p className="text-sm text-[var(--color-muted)]">Checking authentication...</p>
      </div>
    </div>
  );
}

/**
 * A wrapper component that protects its children from unauthenticated access.
 * Redirects to login page if user is not authenticated.
 * Shows a loading state while checking authentication.
 *
 * @example
 * ```tsx
 * // Basic usage
 * <ProtectedRoute>
 *   <AdminDashboard />
 * </ProtectedRoute>
 *
 * // With custom loading component
 * <ProtectedRoute loadingComponent={<CustomLoader />}>
 *   <AdminDashboard />
 * </ProtectedRoute>
 *
 * // With custom login URL
 * <ProtectedRoute loginUrl="/auth/signin">
 *   <AdminDashboard />
 * </ProtectedRoute>
 * ```
 */
export function ProtectedRoute({
  children,
  loadingComponent,
  loginUrl = "/login",
  includeReturnUrl = true,
}: ProtectedRouteProps) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuthContext();

  useEffect(() => {
    // Wait for loading to complete before checking auth
    if (isLoading) return;

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
      const redirectUrl = includeReturnUrl
        ? `${loginUrl}?returnUrl=${encodeURIComponent(pathname)}`
        : loginUrl;
      router.replace(redirectUrl);
    }
  }, [isAuthenticated, isLoading, router, pathname, loginUrl, includeReturnUrl]);

  // Show loading state while checking authentication
  if (isLoading) {
    return <>{loadingComponent ?? <DefaultLoadingComponent />}</>;
  }

  // Don't render children if not authenticated (redirect will happen)
  if (!isAuthenticated) {
    return <>{loadingComponent ?? <DefaultLoadingComponent />}</>;
  }

  // User is authenticated, render children
  return <>{children}</>;
}
