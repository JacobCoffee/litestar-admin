"use client";

import {
  createContext,
  useContext,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

/**
 * Admin panel settings interface.
 */
export interface AdminSettings {
  /** Show keyboard navigation hints in data tables */
  showKeyboardHints: boolean;
  /** Enable keyboard navigation in data tables */
  enableKeyboardNavigation: boolean;
  /** Show row numbers in tables */
  showRowNumbers: boolean;
  /** Default page size for tables */
  defaultPageSize: number;
  /** Enable compact table mode */
  compactTables: boolean;
}

/**
 * Default admin settings.
 */
export const DEFAULT_ADMIN_SETTINGS: AdminSettings = {
  showKeyboardHints: true,
  enableKeyboardNavigation: true,
  showRowNumbers: false,
  defaultPageSize: 10,
  compactTables: false,
};

/**
 * Admin settings context value interface.
 */
export interface AdminSettingsContextValue {
  /** Current settings */
  settings: AdminSettings;
  /** Update a single setting */
  updateSetting: <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => void;
  /** Update multiple settings at once */
  updateSettings: (updates: Partial<AdminSettings>) => void;
  /** Reset all settings to defaults */
  resetSettings: () => void;
}

/**
 * Storage key for persisting admin settings.
 */
const SETTINGS_STORAGE_KEY = "admin_settings";

/**
 * Default context value for SSR and before mount.
 */
const defaultContextValue: AdminSettingsContextValue = {
  settings: DEFAULT_ADMIN_SETTINGS,
  updateSetting: () => {},
  updateSettings: () => {},
  resetSettings: () => {},
};

const AdminSettingsContext = createContext<AdminSettingsContextValue>(defaultContextValue);

/**
 * Hook to access admin settings context.
 * Safe to use anywhere - returns default values if outside provider.
 *
 * @example
 * ```tsx
 * const { settings, updateSetting } = useAdminSettings();
 *
 * // Access a setting
 * if (settings.showKeyboardHints) {
 *   // show hints
 * }
 *
 * // Update a setting
 * updateSetting('showKeyboardHints', false);
 * ```
 */
export function useAdminSettings(): AdminSettingsContextValue {
  return useContext(AdminSettingsContext);
}

/**
 * Props for AdminSettingsProvider component.
 */
export interface AdminSettingsProviderProps {
  children: ReactNode;
  /** Override default settings */
  defaultSettings?: Partial<AdminSettings>;
}

/**
 * Load settings from localStorage with fallback to defaults.
 */
function loadSettings(defaults: AdminSettings): AdminSettings {
  if (typeof window === "undefined") return defaults;

  try {
    const stored = localStorage.getItem(SETTINGS_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to handle new settings added over time
      return { ...defaults, ...parsed };
    }
  } catch {
    // localStorage not available or invalid JSON
  }

  return defaults;
}

/**
 * Save settings to localStorage.
 */
function saveSettings(settings: AdminSettings): void {
  try {
    localStorage.setItem(SETTINGS_STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // localStorage not available
  }
}

/**
 * Provider component that wraps the app and provides admin settings state.
 * Handles settings persistence to localStorage.
 *
 * @example
 * ```tsx
 * function App() {
 *   return (
 *     <AdminSettingsProvider>
 *       <YourApp />
 *     </AdminSettingsProvider>
 *   );
 * }
 * ```
 */
export function AdminSettingsProvider({
  children,
  defaultSettings,
}: AdminSettingsProviderProps) {
  const mergedDefaults = useMemo(
    () => ({ ...DEFAULT_ADMIN_SETTINGS, ...defaultSettings }),
    [defaultSettings],
  );

  const [settings, setSettings] = useState<AdminSettings>(mergedDefaults);
  const [mounted, setMounted] = useState(false);

  // Load settings from storage on mount
  useEffect(() => {
    setSettings(loadSettings(mergedDefaults));
    setMounted(true);
  }, [mergedDefaults]);

  // Save settings when they change (after initial mount)
  useEffect(() => {
    if (mounted) {
      saveSettings(settings);
    }
  }, [settings, mounted]);

  const updateSetting = useCallback(
    <K extends keyof AdminSettings>(key: K, value: AdminSettings[K]) => {
      setSettings((prev) => ({ ...prev, [key]: value }));
    },
    [],
  );

  const updateSettings = useCallback((updates: Partial<AdminSettings>) => {
    setSettings((prev) => ({ ...prev, ...updates }));
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(mergedDefaults);
  }, [mergedDefaults]);

  const value: AdminSettingsContextValue = useMemo(
    () => ({
      settings,
      updateSetting,
      updateSettings,
      resetSettings,
    }),
    [settings, updateSetting, updateSettings, resetSettings],
  );

  return (
    <AdminSettingsContext.Provider value={value}>
      {children}
    </AdminSettingsContext.Provider>
  );
}
