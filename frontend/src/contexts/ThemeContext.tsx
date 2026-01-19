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

/**
 * Theme options for the admin panel.
 */
export type Theme = 'dark' | 'light' | 'system';

/**
 * Resolved theme after considering system preference.
 */
export type ResolvedTheme = 'dark' | 'light';

/**
 * Theme context value interface.
 */
export interface ThemeContextValue {
  /** Current theme setting */
  theme: Theme;
  /** Resolved theme after considering system preference */
  resolvedTheme: ResolvedTheme;
  /** Set the theme */
  setTheme: (theme: Theme) => void;
  /** Toggle between light and dark (ignores system) */
  toggleTheme: () => void;
}

/**
 * Storage key for persisting theme preference.
 */
const THEME_STORAGE_KEY = 'admin_theme';

/**
 * Default context value for SSR and before mount.
 */
const defaultContextValue: ThemeContextValue = {
  theme: 'dark',
  resolvedTheme: 'dark',
  setTheme: () => {},
  toggleTheme: () => {},
};

const ThemeContext = createContext<ThemeContextValue>(defaultContextValue);

/**
 * Hook to access theme context.
 * Safe to use anywhere - returns default values if outside provider.
 *
 * @example
 * ```tsx
 * const { theme, toggleTheme, resolvedTheme } = useTheme();
 * ```
 */
export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext);
}

/**
 * Props for ThemeProvider component.
 */
export interface ThemeProviderProps {
  children: ReactNode;
  /** Default theme if none is stored */
  defaultTheme?: Theme;
}

/**
 * Get the system color scheme preference.
 */
function getSystemTheme(): ResolvedTheme {
  if (typeof window === 'undefined') return 'dark';
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'dark';
  }
}

/**
 * Provider component that wraps the app and provides theme state.
 * Handles theme persistence and system preference detection.
 *
 * @example
 * ```tsx
 * function App() {
 *   return (
 *     <ThemeProvider defaultTheme="dark">
 *       <YourApp />
 *     </ThemeProvider>
 *   );
 * }
 * ```
 */
export function ThemeProvider({ children, defaultTheme = 'dark' }: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(defaultTheme);
  const [systemTheme, setSystemTheme] = useState<ResolvedTheme>('dark');
  const [mounted, setMounted] = useState(false);

  // Load theme from storage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
      if (stored && ['dark', 'light', 'system'].includes(stored)) {
        setThemeState(stored);
      }
      setSystemTheme(getSystemTheme());
    } catch {
      // localStorage not available, use default
    }
    setMounted(true);
  }, []);

  // Listen for system theme changes
  useEffect(() => {
    if (typeof window === 'undefined') return;

    try {
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

      const handleChange = (e: MediaQueryListEvent) => {
        setSystemTheme(e.matches ? 'dark' : 'light');
      };

      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    } catch {
      // matchMedia not available
    }
  }, []);

  // Compute resolved theme
  const resolvedTheme: ResolvedTheme = useMemo(() => {
    if (theme === 'system') return systemTheme;
    return theme;
  }, [theme, systemTheme]);

  // Apply theme class to document
  useEffect(() => {
    if (!mounted || typeof document === 'undefined') return;

    try {
      const root = document.documentElement;
      root.classList.remove('light', 'dark');
      root.classList.add(resolvedTheme);

      // Update meta theme-color
      const metaThemeColor = document.querySelector('meta[name="theme-color"]');
      if (metaThemeColor) {
        metaThemeColor.setAttribute(
          'content',
          resolvedTheme === 'dark' ? '#0d1117' : '#ffffff'
        );
      }
    } catch {
      // DOM manipulation failed
    }
  }, [resolvedTheme, mounted]);

  const setTheme = useCallback((newTheme: Theme) => {
    setThemeState(newTheme);
    try {
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    } catch {
      // localStorage not available
    }
  }, []);

  const toggleTheme = useCallback(() => {
    setTheme(resolvedTheme === 'dark' ? 'light' : 'dark');
  }, [resolvedTheme, setTheme]);

  const value: ThemeContextValue = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      toggleTheme,
    }),
    [theme, resolvedTheme, setTheme, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
