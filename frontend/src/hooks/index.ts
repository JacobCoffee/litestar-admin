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

  // Re-exports from api
  api,
  apiClient,
  isApiError,
} from './useApi';

// Auth hook (standalone, wraps useApi hooks)
export { useAuth } from './useAuth';
export type { UseAuthResult } from './useAuth';
