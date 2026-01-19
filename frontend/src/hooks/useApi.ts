/**
 * TanStack Query hooks for the Litestar Admin API.
 * Provides type-safe, cached data fetching with automatic refetching,
 * optimistic updates, and proper error handling.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
  type QueryKey,
} from "@tanstack/react-query";

import { api, apiClient, isApiError } from "@/lib/api";
import type {
  ActionInfo,
  ActionResult,
  ActivateDeactivateResponse,
  AdminUser,
  ApiError,
  ActivityItem,
  BulkActionRequest,
  BulkActionResponse,
  BulkDeleteRequest,
  BulkDeleteResponse,
  BulkExportRequest,
  CustomViewInfo,
  CustomViewListResponse,
  CustomViewSchemaResponse,
  DashboardStats,
  DeleteResponse,
  EmbedConfig,
  EmbedInfo,
  ExportFormat,
  LinkInfo,
  ListQueryParams,
  ListRecordsResponse,
  LoginCredentials,
  LoginResponse,
  ModelInfo,
  ModelRecord,
  ModelSchema,
  PageContent,
  PageInfo,
  PaginatedResponse,
  UserCreateRequest,
  UserListParams,
  UserListResponse,
  UserResponse,
  UserUpdateRequest,
} from "@/types";

// ============================================================================
// Query Keys Factory
// ============================================================================

/**
 * Centralized query key factory for consistent cache management.
 * All query keys are namespaced to avoid collisions.
 */
export const queryKeys = {
  // Auth
  auth: {
    all: ["auth"] as const,
    user: () => [...queryKeys.auth.all, "user"] as const,
  },

  // Models
  models: {
    all: ["models"] as const,
    list: () => [...queryKeys.models.all, "list"] as const,
    detail: (model: string) => [...queryKeys.models.all, "detail", model] as const,
    schema: (model: string) => [...queryKeys.models.all, "schema", model] as const,
  },

  // Records
  records: {
    all: ["records"] as const,
    model: (model: string) => [...queryKeys.records.all, model] as const,
    list: (model: string, params?: ListQueryParams) =>
      [...queryKeys.records.model(model), "list", params] as const,
    detail: (model: string, id: string | number) =>
      [...queryKeys.records.model(model), "detail", id] as const,
  },

  // Dashboard
  dashboard: {
    all: ["dashboard"] as const,
    stats: () => [...queryKeys.dashboard.all, "stats"] as const,
    activity: (limit?: number, modelName?: string, recordId?: string) =>
      [...queryKeys.dashboard.all, "activity", limit, modelName, recordId] as const,
  },

  // Custom Views
  customViews: {
    all: ["customViews"] as const,
    list: () => [...queryKeys.customViews.all, "list"] as const,
    view: (identity: string) => [...queryKeys.customViews.all, "view", identity] as const,
    items: (identity: string, params?: ListQueryParams) =>
      [...queryKeys.customViews.view(identity), "items", params] as const,
    item: (identity: string, itemId: string) =>
      [...queryKeys.customViews.view(identity), "item", itemId] as const,
    schema: (identity: string) => [...queryKeys.customViews.view(identity), "schema"] as const,
  },

  // Actions
  actions: {
    all: ["actions"] as const,
    list: () => [...queryKeys.actions.all, "list"] as const,
    detail: (identity: string) => [...queryKeys.actions.all, "detail", identity] as const,
  },

  // Pages
  pages: {
    all: ["pages"] as const,
    list: () => [...queryKeys.pages.all, "list"] as const,
    detail: (identity: string) => [...queryKeys.pages.all, "detail", identity] as const,
    content: (identity: string) => [...queryKeys.pages.all, "content", identity] as const,
  },

  // Links
  links: {
    all: ["links"] as const,
    list: () => [...queryKeys.links.all, "list"] as const,
  },

  // Embeds
  embeds: {
    all: ["embeds"] as const,
    list: () => [...queryKeys.embeds.all, "list"] as const,
    config: (identity: string) => [...queryKeys.embeds.all, "config", identity] as const,
    props: (identity: string) => [...queryKeys.embeds.all, "props", identity] as const,
  },

  // User Management
  users: {
    all: ["users"] as const,
    list: (params?: UserListParams) => [...queryKeys.users.all, "list", params] as const,
    detail: (userId: string) => [...queryKeys.users.all, "detail", userId] as const,
  },
} as const;

// ============================================================================
// Type Helpers
// ============================================================================

/**
 * Options for query hooks, excluding queryKey and queryFn.
 */
type QueryOptions<TData, TError = ApiError> = Omit<
  UseQueryOptions<TData, TError, TData, QueryKey>,
  "queryKey" | "queryFn"
>;

/**
 * Options for mutation hooks.
 */
type MutationOptions<TData, TVariables, TError = ApiError> = Omit<
  UseMutationOptions<TData, TError, TVariables>,
  "mutationFn"
>;

// ============================================================================
// Authentication Hooks
// ============================================================================

/**
 * Hook to get the current authenticated user.
 *
 * @example
 * ```tsx
 * const { data: user, isLoading, error } = useCurrentUser();
 * if (user) {
 *   console.log(`Logged in as ${user.email}`);
 * }
 * ```
 */
export function useCurrentUser(options?: QueryOptions<AdminUser>) {
  return useQuery({
    queryKey: queryKeys.auth.user(),
    queryFn: () => api.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // Consider fresh for 5 minutes
    retry: (failureCount, error) => {
      // Don't retry on 401/403
      if (isApiError(error) && (error.status === 401 || error.status === 403)) {
        return false;
      }
      return failureCount < 3;
    },
    ...options,
  });
}

/**
 * Hook to login a user.
 *
 * @example
 * ```tsx
 * const login = useLogin({
 *   onSuccess: (data) => {
 *     router.push('/admin/dashboard');
 *   },
 * });
 *
 * login.mutate({ email: 'user@example.com', password: 'secret' });
 * ```
 */
export function useLogin(options?: MutationOptions<LoginResponse, LoginCredentials>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (credentials: LoginCredentials) => api.login(credentials),
    onSuccess: () => {
      // Invalidate user query to refetch with new credentials
      queryClient.invalidateQueries({ queryKey: queryKeys.auth.user() });
    },
    ...options,
  });
}

/**
 * Hook to logout the current user.
 *
 * @example
 * ```tsx
 * const logout = useLogout({
 *   onSuccess: () => {
 *     router.push('/admin/login');
 *   },
 * });
 *
 * logout.mutate();
 * ```
 */
export function useLogout(options?: MutationOptions<void, void>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      await api.logout();
    },
    onSuccess: () => {
      // Clear all cached data on logout
      queryClient.clear();
    },
    ...options,
  });
}

// ============================================================================
// Models Hooks
// ============================================================================

/**
 * Hook to list all registered models.
 *
 * @example
 * ```tsx
 * const { data: models, isLoading } = useModels();
 * ```
 */
export function useModels(options?: QueryOptions<ModelInfo[]>) {
  return useQuery({
    queryKey: queryKeys.models.list(),
    queryFn: () => api.listModels(),
    staleTime: 10 * 60 * 1000, // Models rarely change, cache for 10 minutes
    ...options,
  });
}

/**
 * Hook to get the JSON schema for a model.
 *
 * @example
 * ```tsx
 * const { data: schema } = useModelSchema('User', 'create');
 * ```
 */
export function useModelSchema(
  model: string,
  mode: "create" | "edit" = "create",
  options?: QueryOptions<ModelSchema>,
) {
  return useQuery({
    queryKey: [...queryKeys.models.schema(model), mode],
    queryFn: () => api.getModelSchema(model, mode),
    staleTime: 30 * 60 * 1000, // Schema rarely changes
    enabled: !!model,
    ...options,
  });
}

// ============================================================================
// Records Hooks
// ============================================================================

/**
 * Hook to list records for a model with pagination and filtering.
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useRecords('User', {
 *   page: 1,
 *   pageSize: 20,
 *   sortBy: 'created_at',
 *   sortOrder: 'desc',
 *   search: 'john',
 * });
 * ```
 */
export function useRecords<T = ModelRecord>(
  model: string,
  params: ListQueryParams = {},
  options?: QueryOptions<ListRecordsResponse<T>>,
) {
  return useQuery({
    queryKey: queryKeys.records.list(model, params),
    queryFn: () => api.listRecords<T>(model, params),
    enabled: !!model,
    ...options,
  });
}

/**
 * Hook to list records with computed pagination info.
 *
 * @example
 * ```tsx
 * const { data } = useRecordsPaginated('User', { page: 1, pageSize: 20 });
 * console.log(`Page ${data.page} of ${data.totalPages}`);
 * ```
 */
export function useRecordsPaginated<T = ModelRecord>(
  model: string,
  params: ListQueryParams = {},
  options?: QueryOptions<PaginatedResponse<T>>,
) {
  return useQuery({
    queryKey: queryKeys.records.list(model, params),
    queryFn: () => api.listRecordsPaginated<T>(model, params),
    enabled: !!model,
    ...options,
  });
}

/**
 * Hook to get a single record by ID.
 *
 * @example
 * ```tsx
 * const { data: user, isLoading } = useRecord('User', userId);
 * ```
 */
export function useRecord<T = ModelRecord>(
  model: string,
  id: string | number | undefined | null,
  options?: QueryOptions<T>,
) {
  return useQuery({
    queryKey: queryKeys.records.detail(model, id ?? ""),
    queryFn: () => api.getRecord<T>(model, id!),
    enabled: !!model && id !== undefined && id !== null,
    ...options,
  });
}

/**
 * Hook to create a new record.
 *
 * @example
 * ```tsx
 * const createUser = useCreateRecord('User', {
 *   onSuccess: (newUser) => {
 *     toast.success('User created successfully');
 *   },
 * });
 *
 * createUser.mutate({ email: 'new@example.com', name: 'New User' });
 * ```
 */
export function useCreateRecord<T = ModelRecord>(
  model: string,
  options?: MutationOptions<T, Partial<T>>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<T>) => api.createRecord<T>(model, data),
    onSuccess: () => {
      // Invalidate the list queries to refetch
      queryClient.invalidateQueries({ queryKey: queryKeys.records.model(model) });
      // Also invalidate dashboard stats as counts may have changed
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
    ...options,
  });
}

/**
 * Hook to update a record (full replacement).
 *
 * @example
 * ```tsx
 * const updateUser = useUpdateRecord('User', {
 *   onSuccess: () => {
 *     toast.success('User updated');
 *   },
 * });
 *
 * updateUser.mutate({ id: userId, data: updatedUserData });
 * ```
 */
export function useUpdateRecord<T = ModelRecord>(
  model: string,
  options?: MutationOptions<T, { id: string | number; data: Partial<T> }>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string | number; data: Partial<T> }) =>
      api.updateRecord<T>(model, id, data),
    onSuccess: (data, variables) => {
      // Update the cached record
      queryClient.setQueryData(queryKeys.records.detail(model, variables.id), data);
      // Invalidate list queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.records.model(model),
        refetchType: "active",
      });
    },
    ...options,
  });
}

/**
 * Hook to partially update a record (PATCH).
 *
 * @example
 * ```tsx
 * const patchUser = usePatchRecord('User');
 * patchUser.mutate({ id: userId, data: { is_active: true } });
 * ```
 */
export function usePatchRecord<T = ModelRecord>(
  model: string,
  options?: MutationOptions<T, { id: string | number; data: Partial<T> }>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string | number; data: Partial<T> }) =>
      api.patchRecord<T>(model, id, data),
    onSuccess: (data, variables) => {
      // Update the cached record
      queryClient.setQueryData(queryKeys.records.detail(model, variables.id), data);
      // Invalidate list queries
      queryClient.invalidateQueries({
        queryKey: queryKeys.records.model(model),
        refetchType: "active",
      });
    },
    ...options,
  });
}

/**
 * Hook to delete a record.
 *
 * @example
 * ```tsx
 * const deleteUser = useDeleteRecord('User', {
 *   onSuccess: () => {
 *     toast.success('User deleted');
 *   },
 * });
 *
 * deleteUser.mutate({ id: userId });
 * ```
 */
export function useDeleteRecord(
  model: string,
  options?: MutationOptions<DeleteResponse, { id: string | number; softDelete?: boolean }>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, softDelete }: { id: string | number; softDelete?: boolean }) =>
      api.deleteRecord(model, id, softDelete),
    onSuccess: (_data, variables) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: queryKeys.records.detail(model, variables.id) });
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: queryKeys.records.model(model) });
      // Invalidate dashboard stats
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
    ...options,
  });
}

// ============================================================================
// Dashboard Hooks
// ============================================================================

/**
 * Hook to get dashboard statistics.
 *
 * @example
 * ```tsx
 * const { data: stats, isLoading } = useDashboardStats();
 * console.log(`Total records: ${stats?.total_records}`);
 * ```
 */
export function useDashboardStats(options?: QueryOptions<DashboardStats>) {
  return useQuery({
    queryKey: queryKeys.dashboard.stats(),
    queryFn: () => api.getDashboardStats(),
    staleTime: 60 * 1000, // Stats can be stale for 1 minute
    ...options,
  });
}

/**
 * Hook to get recent activity with optional filtering.
 *
 * @example
 * ```tsx
 * // Get global activity
 * const { data: activity } = useActivity(20);
 *
 * // Get activity for a specific record
 * const { data: recordActivity } = useActivity(10, "User", "123");
 * ```
 */
export function useActivity(
  limit = 50,
  modelName?: string,
  recordId?: string,
  options?: QueryOptions<ActivityItem[]>,
) {
  return useQuery({
    queryKey: queryKeys.dashboard.activity(limit, modelName, recordId),
    queryFn: () => api.getActivity(limit, modelName, recordId),
    staleTime: 30 * 1000, // Activity can be stale for 30 seconds
    ...options,
  });
}

/**
 * Hook to get activity for a specific record.
 *
 * @example
 * ```tsx
 * const { data: activity } = useRecordActivity("User", "123");
 * ```
 */
export function useRecordActivity(
  modelName: string,
  recordId: string,
  limit = 20,
  options?: QueryOptions<ActivityItem[]>,
) {
  return useActivity(limit, modelName, recordId, options);
}

// ============================================================================
// Bulk Action Hooks
// ============================================================================

/**
 * Hook to bulk delete records.
 *
 * @example
 * ```tsx
 * const bulkDelete = useBulkDelete('User', {
 *   onSuccess: (response) => {
 *     toast.success(`Deleted ${response.deleted} records`);
 *   },
 * });
 *
 * bulkDelete.mutate({ ids: [1, 2, 3] });
 * ```
 */
export function useBulkDelete(
  model: string,
  options?: MutationOptions<BulkDeleteResponse, BulkDeleteRequest>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkDeleteRequest) => api.bulkDelete(model, request),
    onSuccess: (_data, variables) => {
      // Remove deleted records from cache
      for (const id of variables.ids) {
        queryClient.removeQueries({ queryKey: queryKeys.records.detail(model, id) });
      }
      // Invalidate list queries
      queryClient.invalidateQueries({ queryKey: queryKeys.records.model(model) });
      // Invalidate dashboard stats
      queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
    },
    ...options,
  });
}

/**
 * Hook to execute a custom bulk action.
 *
 * @example
 * ```tsx
 * const bulkActivate = useBulkAction('User', 'activate', {
 *   onSuccess: (response) => {
 *     toast.success(`Activated ${response.affected} users`);
 *   },
 * });
 *
 * bulkActivate.mutate({ ids: [1, 2, 3] });
 * ```
 */
export function useBulkAction(
  model: string,
  action: string,
  options?: MutationOptions<BulkActionResponse, BulkActionRequest>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: BulkActionRequest) => api.bulkAction(model, action, request),
    onSuccess: () => {
      // Invalidate list queries as records may have changed
      queryClient.invalidateQueries({ queryKey: queryKeys.records.model(model) });
    },
    ...options,
  });
}

// ============================================================================
// Export Hooks
// ============================================================================

/**
 * Hook to export records as a downloadable file.
 *
 * @example
 * ```tsx
 * const exportCsv = useExportRecords('User', {
 *   onSuccess: (blob) => {
 *     downloadBlob(blob, 'users.csv');
 *   },
 * });
 *
 * exportCsv.mutate({ format: 'csv' });
 * ```
 */
export function useExportRecords(
  model: string,
  options?: MutationOptions<Blob, { format?: ExportFormat }>,
) {
  return useMutation({
    mutationFn: ({ format = "csv" }: { format?: ExportFormat }) => api.exportRecords(model, format),
    ...options,
  });
}

/**
 * Hook to export selected records as a downloadable file.
 *
 * @example
 * ```tsx
 * const exportSelected = useExportSelected('User');
 * exportSelected.mutate({ ids: [1, 2, 3], format: 'json' });
 * ```
 */
export function useExportSelected(
  model: string,
  options?: MutationOptions<Blob, BulkExportRequest>,
) {
  return useMutation({
    mutationFn: (request: BulkExportRequest) => api.exportSelected(model, request),
    ...options,
  });
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook to prefetch records for a model.
 * Useful for prefetching data on hover or before navigation.
 *
 * @example
 * ```tsx
 * const prefetch = usePrefetchRecords();
 *
 * <Link
 *   href={`/admin/models/${model}`}
 *   onMouseEnter={() => prefetch(model, { page: 1 })}
 * >
 *   {model.name}
 * </Link>
 * ```
 */
export function usePrefetchRecords() {
  const queryClient = useQueryClient();

  return (model: string, params?: ListQueryParams) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.records.list(model, params),
      queryFn: () => api.listRecords(model, params),
      staleTime: 60 * 1000,
    });
  };
}

/**
 * Hook to prefetch a single record.
 *
 * @example
 * ```tsx
 * const prefetch = usePrefetchRecord();
 *
 * <tr onMouseEnter={() => prefetch('User', record.id)}>
 *   ...
 * </tr>
 * ```
 */
export function usePrefetchRecord() {
  const queryClient = useQueryClient();

  return (model: string, id: string | number) => {
    queryClient.prefetchQuery({
      queryKey: queryKeys.records.detail(model, id),
      queryFn: () => api.getRecord(model, id),
      staleTime: 60 * 1000,
    });
  };
}

/**
 * Hook to invalidate all caches for a model.
 * Useful when you need to force a refresh.
 *
 * @example
 * ```tsx
 * const invalidate = useInvalidateModel();
 *
 * <button onClick={() => invalidate('User')}>
 *   Refresh Users
 * </button>
 * ```
 */
export function useInvalidateModel() {
  const queryClient = useQueryClient();

  return (model: string) => {
    queryClient.invalidateQueries({ queryKey: queryKeys.records.model(model) });
    queryClient.invalidateQueries({ queryKey: queryKeys.models.schema(model) });
  };
}

/**
 * Hook to check if the user is authenticated.
 *
 * @example
 * ```tsx
 * const { isAuthenticated, isLoading } = useIsAuthenticated();
 *
 * if (!isAuthenticated && !isLoading) {
 *   router.push('/admin/login');
 * }
 * ```
 */
export function useIsAuthenticated() {
  const { data, isLoading, isError } = useCurrentUser({
    retry: false,
  });

  return {
    isAuthenticated: !!data && !isError,
    isLoading,
    user: data,
  };
}

// ============================================================================
// Custom View Hooks
// ============================================================================

/**
 * Hook to list all registered custom views.
 */
export function useCustomViews(options?: QueryOptions<CustomViewInfo[]>) {
  return useQuery({
    queryKey: queryKeys.customViews.list(),
    queryFn: () => api.listCustomViews(),
    staleTime: 10 * 60 * 1000,
    ...options,
  });
}

/**
 * Hook to get items from a custom view.
 */
export function useCustomViewItems<T = Record<string, unknown>>(
  identity: string,
  params: ListQueryParams = {},
  options?: QueryOptions<CustomViewListResponse<T>>,
) {
  return useQuery({
    queryKey: queryKeys.customViews.items(identity, params),
    queryFn: () => api.getCustomViewList<T>(identity, params),
    enabled: !!identity,
    ...options,
  });
}

/**
 * Hook to get a single item from a custom view.
 */
export function useCustomViewItem<T = Record<string, unknown>>(
  identity: string,
  itemId: string | undefined | null,
  options?: QueryOptions<T>,
) {
  return useQuery({
    queryKey: queryKeys.customViews.item(identity, itemId ?? ""),
    queryFn: () => api.getCustomViewItem<T>(identity, itemId!),
    enabled: !!identity && !!itemId,
    ...options,
  });
}

/**
 * Hook to get the schema for a custom view.
 */
export function useCustomViewSchema(identity: string, options?: QueryOptions<CustomViewSchemaResponse>) {
  return useQuery({
    queryKey: queryKeys.customViews.schema(identity),
    queryFn: () => api.getCustomViewSchema(identity),
    staleTime: 30 * 60 * 1000,
    enabled: !!identity,
    ...options,
  });
}

/**
 * Hook to create an item in a custom view.
 */
export function useCreateCustomViewItem<T = Record<string, unknown>>(
  identity: string,
  options?: MutationOptions<T, Partial<T>>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Partial<T>) => api.createCustomViewItem<T>(identity, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.customViews.view(identity) });
    },
    ...options,
  });
}

/**
 * Hook to update an item in a custom view.
 */
export function useUpdateCustomViewItem<T = Record<string, unknown>>(
  identity: string,
  options?: MutationOptions<T, { itemId: string; data: Partial<T> }>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, data }: { itemId: string; data: Partial<T> }) =>
      api.updateCustomViewItem<T>(identity, itemId, data),
    onSuccess: (_data, variables) => {
      queryClient.setQueryData(queryKeys.customViews.item(identity, variables.itemId), _data);
      queryClient.invalidateQueries({
        queryKey: queryKeys.customViews.view(identity),
        refetchType: "active",
      });
    },
    ...options,
  });
}

/**
 * Hook to delete an item from a custom view.
 */
export function useDeleteCustomViewItem(identity: string, options?: MutationOptions<void, string>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (itemId: string) => api.deleteCustomViewItem(identity, itemId),
    onSuccess: (_data, itemId) => {
      queryClient.removeQueries({ queryKey: queryKeys.customViews.item(identity, itemId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.customViews.view(identity) });
    },
    ...options,
  });
}

// ============================================================================
// Action Hooks
// ============================================================================

/**
 * Hook to list all registered actions.
 */
export function useActions(options?: QueryOptions<ActionInfo[]>) {
  return useQuery({
    queryKey: queryKeys.actions.list(),
    queryFn: () => api.listActions(),
    staleTime: 10 * 60 * 1000,
    ...options,
  });
}

/**
 * Hook to get details of a specific action.
 */
export function useAction(identity: string, options?: QueryOptions<ActionInfo>) {
  return useQuery({
    queryKey: queryKeys.actions.detail(identity),
    queryFn: () => api.getAction(identity),
    staleTime: 10 * 60 * 1000,
    enabled: !!identity,
    ...options,
  });
}

/**
 * Hook to execute an action.
 */
export function useExecuteAction(
  identity: string,
  options?: MutationOptions<ActionResult, Record<string, unknown>>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.executeAction(identity, data),
    onSuccess: (result) => {
      if (result.refresh) {
        queryClient.invalidateQueries({ queryKey: queryKeys.records.all });
        queryClient.invalidateQueries({ queryKey: queryKeys.customViews.all });
        queryClient.invalidateQueries({ queryKey: queryKeys.dashboard.stats() });
      }
    },
    ...options,
  });
}

// ============================================================================
// Page Hooks
// ============================================================================

/**
 * Hook to list all registered pages.
 */
export function usePages(options?: QueryOptions<PageInfo[]>) {
  return useQuery({
    queryKey: queryKeys.pages.list(),
    queryFn: () => api.listPages(),
    staleTime: 10 * 60 * 1000,
    ...options,
  });
}

/**
 * Hook to get details of a specific page.
 */
export function usePage(identity: string, options?: QueryOptions<PageInfo>) {
  return useQuery({
    queryKey: queryKeys.pages.detail(identity),
    queryFn: () => api.getPage(identity),
    staleTime: 10 * 60 * 1000,
    enabled: !!identity,
    ...options,
  });
}

/**
 * Hook to get the content of a page.
 */
export function usePageContent(
  identity: string,
  refreshInterval?: number | null,
  options?: QueryOptions<PageContent>,
) {
  return useQuery({
    queryKey: queryKeys.pages.content(identity),
    queryFn: () => api.getPageContent(identity),
    enabled: !!identity,
    ...(refreshInterval ? { refetchInterval: refreshInterval } : {}),
    ...options,
  });
}

// ============================================================================
// Link Hooks
// ============================================================================

/**
 * Hook to list all registered links.
 */
export function useLinks(options?: QueryOptions<LinkInfo[]>) {
  return useQuery({
    queryKey: queryKeys.links.list(),
    queryFn: () => api.listLinks(),
    staleTime: 10 * 60 * 1000,
    ...options,
  });
}

// ============================================================================
// Embed Hooks
// ============================================================================

/**
 * Hook to list all registered embeds.
 */
export function useEmbeds(options?: QueryOptions<EmbedInfo[]>) {
  return useQuery({
    queryKey: queryKeys.embeds.list(),
    queryFn: () => api.listEmbeds(),
    staleTime: 10 * 60 * 1000,
    ...options,
  });
}

/**
 * Hook to get configuration for an embed.
 */
export function useEmbedConfig(identity: string, options?: QueryOptions<EmbedConfig>) {
  return useQuery({
    queryKey: queryKeys.embeds.config(identity),
    queryFn: () => api.getEmbedConfig(identity),
    staleTime: 30 * 60 * 1000,
    enabled: !!identity,
    ...options,
  });
}

/**
 * Hook to get dynamic props for an embed component.
 */
export function useEmbedProps(identity: string, options?: QueryOptions<Record<string, unknown>>) {
  return useQuery({
    queryKey: queryKeys.embeds.props(identity),
    queryFn: () => api.getEmbedProps(identity),
    enabled: !!identity,
    ...options,
  });
}

// ============================================================================
// User Management Hooks
// ============================================================================

/**
 * Hook to list admin users with pagination and filtering.
 */
export function useUsers(params: UserListParams = {}, options?: QueryOptions<UserListResponse>) {
  return useQuery({
    queryKey: queryKeys.users.list(params),
    queryFn: () => api.listUsers(params),
    ...options,
  });
}

/**
 * Hook to get a single admin user by ID.
 */
export function useUser(userId: string | undefined | null, options?: QueryOptions<UserResponse>) {
  return useQuery({
    queryKey: queryKeys.users.detail(userId ?? ""),
    queryFn: () => api.getUser(userId!),
    enabled: !!userId,
    ...options,
  });
}

/**
 * Hook to create a new admin user.
 */
export function useCreateUser(options?: MutationOptions<UserResponse, UserCreateRequest>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: UserCreateRequest) => api.createUser(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
    ...options,
  });
}

/**
 * Hook to update an existing admin user.
 */
export function useUpdateUser(
  options?: MutationOptions<UserResponse, { userId: string; data: UserUpdateRequest }>,
) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UserUpdateRequest }) =>
      api.updateUser(userId, data),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(queryKeys.users.detail(variables.userId), data);
      queryClient.invalidateQueries({
        queryKey: queryKeys.users.all,
        refetchType: "active",
      });
    },
    ...options,
  });
}

/**
 * Hook to delete an admin user.
 */
export function useDeleteUser(options?: MutationOptions<void, string>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => api.deleteUser(userId),
    onSuccess: (_data, userId) => {
      queryClient.removeQueries({ queryKey: queryKeys.users.detail(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
    ...options,
  });
}

/**
 * Hook to activate an admin user.
 */
export function useActivateUser(options?: MutationOptions<ActivateDeactivateResponse, string>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => api.activateUser(userId),
    onSuccess: (_data, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
    ...options,
  });
}

/**
 * Hook to deactivate an admin user.
 */
export function useDeactivateUser(options?: MutationOptions<ActivateDeactivateResponse, string>) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (userId: string) => api.deactivateUser(userId),
    onSuccess: (_data, userId) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.users.detail(userId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.users.all });
    },
    ...options,
  });
}

// ============================================================================
// Re-exports
// ============================================================================

// Re-export the API client for direct access if needed
export { api, apiClient, isApiError };
