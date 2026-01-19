/**
 * Contexts barrel export.
 *
 * @example
 * ```tsx
 * import { useAuthContext, useSidebar } from '@/contexts';
 * ```
 */

export { AuthProvider, useAuthContext } from "./AuthContext";
export type { AuthContextValue, AuthProviderProps } from "./AuthContext";

export { LayoutProvider, useSidebar } from "./LayoutContext";

export { CommandPaletteProvider, useCommandPalette } from "./CommandPaletteContext";
export type { CommandPaletteProviderProps } from "./CommandPaletteContext";

export {
  AdminSettingsProvider,
  useAdminSettings,
  DEFAULT_ADMIN_SETTINGS,
} from "./AdminSettingsContext";
export type {
  AdminSettings,
  AdminSettingsContextValue,
  AdminSettingsProviderProps,
} from "./AdminSettingsContext";
