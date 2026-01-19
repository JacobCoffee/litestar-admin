'use client';

import { useState, type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { AuthProvider } from '@/contexts/AuthContext';
import { LayoutProvider } from '@/contexts/LayoutContext';
import { ToastProvider } from '@/components/ui/Toast';

/**
 * Query client configuration with optimized defaults for performance.
 *
 * Performance optimizations:
 * - Longer staleTime reduces unnecessary refetches (2 minutes)
 * - gcTime keeps data in cache longer for instant back-navigation
 * - refetchOnMount: false prevents refetch when component remounts
 * - Structural sharing enabled by default for efficient re-renders
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Don't refetch on window focus in development for better DX
        refetchOnWindowFocus: process.env['NODE_ENV'] === 'production',
        // Don't refetch on reconnect unless explicitly needed
        refetchOnReconnect: false,
        // Don't refetch on mount if data is fresh
        refetchOnMount: false,
        // Retry failed requests up to 2 times with exponential backoff
        retry: (failureCount, error) => {
          // Don't retry on 4xx errors (except 408 and 429)
          if (error && typeof error === 'object' && 'status' in error) {
            const status = (error as { status: number }).status;
            if (status >= 400 && status < 500 && status !== 408 && status !== 429) {
              return false;
            }
          }
          return failureCount < 2;
        },
        // Use exponential backoff for retries (faster initial retry)
        retryDelay: (attemptIndex) => Math.min(500 * 2 ** attemptIndex, 15000),
        // Consider data stale after 2 minutes (increased from 1 min)
        staleTime: 2 * 60 * 1000,
        // Keep unused data in cache for 10 minutes for back navigation
        gcTime: 10 * 60 * 1000,
      },
      mutations: {
        // Don't retry mutations by default
        retry: false,
      },
    },
  });
}

// Global query client for SSR
let browserQueryClient: QueryClient | undefined;

function getQueryClient() {
  if (typeof window === 'undefined') {
    // Server: always make a new query client
    return makeQueryClient();
  }
  // Browser: make a new query client if we don't already have one
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

/**
 * Props for Providers component.
 */
export interface ProvidersProps {
  children: ReactNode;
}

/**
 * Root providers component that wraps the application with all necessary context providers.
 * This is a client component that provides:
 * - TanStack Query for data fetching and caching
 * - Auth context for authentication state
 * - Toast notifications
 *
 * @example
 * ```tsx
 * // In layout.tsx
 * export default function RootLayout({ children }: { children: React.ReactNode }) {
 *   return (
 *     <html lang="en">
 *       <body>
 *         <Providers>{children}</Providers>
 *       </body>
 *     </html>
 *   );
 * }
 * ```
 */
export function Providers({ children }: ProvidersProps) {
  // Use useState to ensure the same client is used across renders
  const [queryClient] = useState(() => getQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <LayoutProvider>
          <ToastProvider defaultDuration={5000} maxToasts={5}>
            {children}
          </ToastProvider>
        </LayoutProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}
