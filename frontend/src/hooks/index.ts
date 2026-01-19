/**
 * Export all hooks for convenient imports.
 *
 * @example
 * ```tsx
 * import { useModels, useRecords, useCreateRecord, useAuth } from '@/hooks';
 * ```
 */

export {
  // Query keys
  queryKeys,

  // Auth hooks
  useCurrentUser,
  useLogin,
  useLogout,
  useIsAuthenticated,

  // Models hooks
  useModels,
  useModelSchema,

  // Records hooks
  useRecords,
  useRecordsPaginated,
  useRecord,
  useCreateRecord,
  useUpdateRecord,
  usePatchRecord,
  useDeleteRecord,

  // Dashboard hooks
  useDashboardStats,
  useActivity,
  useRecordActivity,

  // Bulk action hooks
  useBulkDelete,
  useBulkAction,

  // Export hooks
  useExportRecords,
  useExportSelected,

  // Utility hooks
  usePrefetchRecords,
  usePrefetchRecord,
  useInvalidateModel,

  // Relationship picker hooks
  useRelationshipSearch,
  useRelationshipOptions,
  usePrefetchRelationshipSearch,

  // Custom views hooks
  useCustomViews,
  useCustomViewItems,
  useCustomViewItem,
  useCustomViewSchema,

  // Actions hooks
  useActions,
  useAction,
  useExecuteAction,

  // Pages hooks
  usePages,
  usePage,
  usePageContent,

  // Links hooks
  useLinks,

  // Embeds hooks
  useEmbeds,
  useEmbedConfig,
  useEmbedProps,

  // Re-exports from api
  api,
  apiClient,
  isApiError,
} from "./useApi";

// Auth hook (standalone, wraps useApi hooks)
export { useAuth } from "./useAuth";
export type { UseAuthResult } from "./useAuth";

// Search and filter hook
export {
  useSearchFilter,
  getOperatorsForType,
  getOperatorLabel,
  getDefaultOperator,
  operatorRequiresValue,
  serializeFiltersToUrl,
  parseFiltersFromUrl,
  validateFilterValue,
} from "./useSearchFilter";
export type {
  FilterOperator,
  FilterableColumnType,
  FilterableColumn,
  ColumnFilter,
  DateRangeValue,
  FilterState,
  UseSearchFilterOptions,
  UseSearchFilterReturn,
} from "./useSearchFilter";

// Virtual list hook for large datasets
export { useVirtualList, estimateVisibleItems } from "./useVirtualList";
export type { UseVirtualListOptions, VirtualItem, UseVirtualListReturn } from "./useVirtualList";

// Keyboard shortcuts hooks
export {
  useKeyboardShortcuts,
  useShortcut,
  DEFAULT_SHORTCUTS,
} from "./useKeyboardShortcuts";
export type {
  KeyModifier,
  KeyboardShortcut,
  UseKeyboardShortcutsOptions,
  UseKeyboardShortcutsReturn,
} from "./useKeyboardShortcuts";
