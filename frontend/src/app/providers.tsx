"use client";

import { useState, useEffect, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { AuthProvider } from "@/contexts/AuthContext";
import { LayoutProvider } from "@/contexts/LayoutContext";
import { ThemeProvider, useTheme } from "@/contexts/ThemeContext";
import { CommandPaletteProvider } from "@/contexts/CommandPaletteContext";
import { ToastProvider } from "@/components/ui/Toast";

const ACCENT_COLOR_KEY = "admin_accent_color";

const accentColors = [
  { value: "#f6821f", lightValue: "#d4690e" },
  { value: "#58a6ff", lightValue: "#0969da" },
  { value: "#3fb950", lightValue: "#1a7f37" },
  { value: "#a371f7", lightValue: "#8250df" },
  { value: "#f778ba", lightValue: "#bf3989" },
  { value: "#f85149", lightValue: "#cf222e" },
  { value: "#2dd4bf", lightValue: "#14b8a6" },
  { value: "#e3b341", lightValue: "#9a6700" },
];

/**
 * Adjust the brightness of a hex color.
 */
function adjustBrightness(hex: string, percent: number): string {
  const color = hex.replace("#", "");
  const r = parseInt(color.substring(0, 2), 16);
  const g = parseInt(color.substring(2, 4), 16);
  const b = parseInt(color.substring(4, 6), 16);

  const adjust = (value: number) => {
    const adjusted = Math.round(value + (value * percent) / 100);
    return Math.max(0, Math.min(255, adjusted));
  };

  const toHex = (value: number) => value.toString(16).padStart(2, "0");
  return `#${toHex(adjust(r))}${toHex(adjust(g))}${toHex(adjust(b))}`;
}

/**
 * Component that loads and applies saved accent color on mount.
 * Uses a <style> element for reliable CSS variable overrides.
 */
function AccentColorLoader({ children }: { children: ReactNode }) {
  const { resolvedTheme } = useTheme();
  const [accentStyles, setAccentStyles] = useState<string | null>(null);

  useEffect(() => {
    try {
      const stored = localStorage.getItem(ACCENT_COLOR_KEY);
      if (stored) {
        const color = accentColors.find((c) => c.value === stored);
        if (color) {
          const colorValue = resolvedTheme === "light" ? color.lightValue : color.value;
          const hoverColor = adjustBrightness(colorValue, -15);

          // Create CSS that overrides the theme variables
          setAccentStyles(`
            :root, .dark, .light {
              --color-primary: ${colorValue} !important;
              --color-primary-hover: ${hoverColor} !important;
              --color-accent: ${colorValue} !important;
            }
          `);
        }
      } else {
        setAccentStyles(null);
      }
    } catch {
      // localStorage not available
      setAccentStyles(null);
    }
  }, [resolvedTheme]);

  return (
    <>
      {accentStyles && <style dangerouslySetInnerHTML={{ __html: accentStyles }} />}
      {children}
    </>
  );
}

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
        refetchOnWindowFocus: process.env["NODE_ENV"] === "production",
        // Don't refetch on reconnect unless explicitly needed
        refetchOnReconnect: false,
        // Don't refetch on mount if data is fresh
        refetchOnMount: false,
        // Retry failed requests up to 2 times with exponential backoff
        retry: (failureCount, error) => {
          // Don't retry on 4xx errors (except 408 and 429)
          if (error && typeof error === "object" && "status" in error) {
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
  if (typeof window === "undefined") {
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
 * - Command palette (Cmd/Ctrl + K) for global search and navigation
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
      <ThemeProvider defaultTheme="dark">
        <AccentColorLoader>
          <AuthProvider>
            <LayoutProvider>
              <ToastProvider defaultDuration={5000} maxToasts={5}>
                <CommandPaletteProvider>
                  {children}
                </CommandPaletteProvider>
              </ToastProvider>
            </LayoutProvider>
          </AuthProvider>
        </AccentColorLoader>
      </ThemeProvider>
    </QueryClientProvider>
  );
}
