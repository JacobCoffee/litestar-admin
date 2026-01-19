'use client';

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';

import { useLogin, useLogout, useCurrentUser, apiClient, isApiError, queryKeys } from '@/hooks/useApi';
import type { AdminUser } from '@/types';

/**
 * Token storage key for localStorage.
 */
const ACCESS_TOKEN_KEY = 'admin_access_token';

/**
 * Auth context value interface.
 */
export interface AuthContextValue {
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
  /** Check if user has a specific permission */
  hasPermission: (permission: string) => boolean;
  /** Check if user has a specific role */
  hasRole: (role: string) => boolean;
  /** Check if user has any of the specified permissions */
  hasAnyPermission: (permissions: string[]) => boolean;
  /** Check if user has all of the specified permissions */
  hasAllPermissions: (permissions: string[]) => boolean;
  /** Check if user has any of the specified roles */
  hasAnyRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/**
 * Hook to access auth context.
 * Must be used within an AuthProvider.
 *
 * @throws Error if used outside of AuthProvider
 *
 * @example
 * ```tsx
 * const { user, isAuthenticated, login, logout } = useAuthContext();
 * ```
 */
export function useAuthContext(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}

/**
 * Props for AuthProvider component.
 */
export interface AuthProviderProps {
  children: ReactNode;
}

/**
 * Provider component that wraps the app and provides auth state.
 * Handles initial auth check on mount and provides auth methods.
 *
 * @example
 * ```tsx
 * function App() {
 *   return (
 *     <AuthProvider>
 *       <YourApp />
 *     </AuthProvider>
 *   );
 * }
 * ```
 */
export function AuthProvider({ children }: AuthProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const [initialCheckDone, setInitialCheckDone] = useState(false);

  // Check if we have a token in storage (client-side only)
  const hasStoredToken = useMemo(() => {
    if (typeof window === 'undefined') return false;
    return !!localStorage.getItem(ACCESS_TOKEN_KEY);
  }, []);

  // Get current user query - this validates the token and fetches user data
  const {
    data: user,
    isLoading: isUserLoading,
    error: userError,
    refetch: refetchUser,
  } = useCurrentUser({
    retry: false,
    enabled: hasStoredToken,
  });

  // Login mutation
  const loginMutation = useLogin({
    onSuccess: async () => {
      // Refetch user data after successful login
      await refetchUser();

      // Redirect to returnUrl or default to /admin
      const returnUrl = searchParams.get('returnUrl') ?? '/';
      router.push(returnUrl);
    },
  });

  // Logout mutation
  const logoutMutation = useLogout({
    onSuccess: () => {
      // Clear all queries to ensure fresh state
      queryClient.removeQueries({ queryKey: queryKeys.auth.all });
      // Redirect to login page after logout
      router.push('/login');
    },
  });

  // Check initial authentication state on mount
  useEffect(() => {
    const checkAuth = async () => {
      if (typeof window === 'undefined') {
        setInitialCheckDone(true);
        return;
      }

      const hasToken = !!localStorage.getItem(ACCESS_TOKEN_KEY);

      if (hasToken) {
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
  }, [refetchUser]);

  // Compute authentication state
  const isAuthenticated = useMemo(() => {
    return !!user && !userError;
  }, [user, userError]);

  // Compute loading state
  const isLoading = useMemo(() => {
    if (!initialCheckDone) return true;
    if (typeof window === 'undefined') return true;

    const hasToken = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (hasToken && isUserLoading) return true;

    return false;
  }, [initialCheckDone, isUserLoading]);

  // Login handler
  const login = useCallback(
    async (email: string, password: string, _rememberMe = false) => {
      await loginMutation.mutateAsync({ email, password });
    },
    [loginMutation]
  );

  // Logout handler
  const logout = useCallback(async () => {
    await logoutMutation.mutateAsync();
  }, [logoutMutation]);

  // Permission check helpers
  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!user) return false;
      return user.permissions.includes(permission);
    },
    [user]
  );

  const hasRole = useCallback(
    (role: string): boolean => {
      if (!user) return false;
      return user.roles.includes(role);
    },
    [user]
  );

  const hasAnyPermission = useCallback(
    (permissions: string[]): boolean => {
      if (!user) return false;
      return permissions.some((p) => user.permissions.includes(p));
    },
    [user]
  );

  const hasAllPermissions = useCallback(
    (permissions: string[]): boolean => {
      if (!user) return false;
      return permissions.every((p) => user.permissions.includes(p));
    },
    [user]
  );

  const hasAnyRole = useCallback(
    (roles: string[]): boolean => {
      if (!user) return false;
      return roles.some((r) => user.roles.includes(r));
    },
    [user]
  );

  // Compute error state
  const error = useMemo(() => {
    if (loginMutation.error) {
      return isApiError(loginMutation.error) ? loginMutation.error : null;
    }
    if (userError && isApiError(userError)) {
      // Ignore 401 errors during initial load
      if (userError.status === 401) return null;
      return userError;
    }
    return null;
  }, [loginMutation.error, userError]);

  const value: AuthContextValue = useMemo(
    () => ({
      user: user ?? null,
      isAuthenticated,
      isLoading,
      error,
      login,
      logout,
      isLoggingIn: loginMutation.isPending,
      isLoggingOut: logoutMutation.isPending,
      hasPermission,
      hasRole,
      hasAnyPermission,
      hasAllPermissions,
      hasAnyRole,
    }),
    [
      user,
      isAuthenticated,
      isLoading,
      error,
      login,
      logout,
      loginMutation.isPending,
      logoutMutation.isPending,
      hasPermission,
      hasRole,
      hasAnyPermission,
      hasAllPermissions,
      hasAnyRole,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
