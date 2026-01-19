"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { useLogin, useLogout, useCurrentUser, apiClient, isApiError } from "./useApi";
import type { AdminUser } from "@/types";

/**
 * Token storage key for localStorage.
 */
const ACCESS_TOKEN_KEY = "admin_access_token";

/**
 * Result of the useAuth hook.
 */
export interface UseAuthResult {
  /** Current authenticated user, null if not authenticated */
  user: AdminUser | null;
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** Whether the initial auth check is loading */
  isLoading: boolean;
  /** Error from the auth operations */
  error: Error | null;
  /** Login function */
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  /** Logout function */
  logout: () => Promise<void>;
  /** Whether a login is in progress */
  isLoggingIn: boolean;
  /** Whether a logout is in progress */
  isLoggingOut: boolean;
}

/**
 * Hook for authentication state and operations.
 * Wraps useLogin, useLogout, and useCurrentUser from useApi.
 * Handles redirect after login/logout and token persistence.
 *
 * @example
 * ```tsx
 * const { user, isAuthenticated, login, logout, isLoading } = useAuth();
 *
 * if (isLoading) return <Spinner />;
 * if (!isAuthenticated) return <LoginForm onSubmit={login} />;
 * return <Dashboard user={user} onLogout={logout} />;
 * ```
 */
export function useAuth(): UseAuthResult {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // Get current user query - this validates the token and fetches user data
  const {
    data: user,
    isLoading: isUserLoading,
    error: userError,
    refetch: refetchUser,
  } = useCurrentUser({
    retry: false,
    // Only run the query if we have a token
    enabled: typeof window !== "undefined" && !!localStorage.getItem(ACCESS_TOKEN_KEY),
  });

  // Login mutation
  const loginMutation = useLogin({
    onSuccess: async () => {
      // Refetch user data after successful login
      await refetchUser();

      // Redirect to returnUrl or default to dashboard
      const returnUrl = searchParams.get("returnUrl") ?? "/";
      router.push(returnUrl);
    },
  });

  // Logout mutation
  const logoutMutation = useLogout({
    onSuccess: () => {
      // Redirect to login page after logout
      router.push("/login");
    },
  });

  // Check initial authentication state
  useEffect(() => {
    const checkAuth = async () => {
      const hasToken = typeof window !== "undefined" && !!localStorage.getItem(ACCESS_TOKEN_KEY);

      if (hasToken && !user && !isUserLoading) {
        // We have a token but no user data, try to fetch it
        try {
          await refetchUser();
        } catch {
          // Token is invalid, clear it
          apiClient.clearTokens();
        }
      }

      setInitialCheckDone(true);
    };

    checkAuth();
  }, [user, isUserLoading, refetchUser]);

  // Compute authentication state
  const isAuthenticated = useMemo(() => {
    return !!user && !userError;
  }, [user, userError]);

  // Compute loading state - true during initial check or when fetching user
  const isLoading = useMemo(() => {
    if (!initialCheckDone) return true;
    if (typeof window === "undefined") return true;

    const hasToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (hasToken && isUserLoading) return true;

    return false;
  }, [initialCheckDone, isUserLoading]);

  // Login handler
  const login = useCallback(
    async (email: string, password: string, _rememberMe = false) => {
      await loginMutation.mutateAsync({ email, password });
    },
    [loginMutation],
  );

  // Logout handler
  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  // Compute error state
  const error = useMemo(() => {
    if (loginMutation.error) {
      return isApiError(loginMutation.error) ? loginMutation.error : null;
    }
    if (userError && isApiError(userError)) {
      // Ignore 401 errors during initial load as they just mean not authenticated
      if (userError.status === 401) return null;
      return userError;
    }
    return null;
  }, [loginMutation.error, userError]);

  return {
    user: user ?? null,
    isAuthenticated,
    isLoading,
    error,
    login,
    logout,
    isLoggingIn: loginMutation.isPending,
    isLoggingOut: logoutMutation.isPending,
  };
}
