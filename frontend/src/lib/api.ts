/**
 * Comprehensive API client for the Litestar Admin frontend.
 * Provides type-safe methods for all backend endpoints with built-in
 * token management, error handling, and request/response interceptors.
 */

import type {
  ActionInfo,
  ActionResult,
  ActivateDeactivateResponse,
  AdminUser,
  ApiError,
  ApiErrorResponse,
  AuthTokens,
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
  ActivityItem,
  EmbedConfig,
  EmbedInfo,
  ExportFormat,
  FileDeleteResponse,
  FileUploadResponse,
  ImportExecuteResponse,
  ImportPreviewResponse,
  ImportValidationResponse,
  LinkInfo,
  ListQueryParams,
  ListRecordsResponse,
  LoginCredentials,
  LoginResponse,
  LogoutResponse,
  ModelInfo,
  ModelRecord,
  ModelSchema,
  PageContent,
  PageInfo,
  PaginatedResponse,
  RelationshipSearchParams,
  RelationshipSearchResponse,
  UserCreateRequest,
  UserListParams,
  UserListResponse,
  UserResponse,
  UserUpdateRequest,
} from "@/types";

// ============================================================================
// Configuration
// ============================================================================

/**
 * API client configuration options.
 */
export interface ApiClientConfig {
  /** Base URL for all API requests. Defaults to '/admin' */
  baseUrl: string;
  /** Storage key for access token. Defaults to 'admin_access_token' */
  accessTokenKey: string;
  /** Storage key for refresh token. Defaults to 'admin_refresh_token' */
  refreshTokenKey: string;
  /** Default request timeout in milliseconds. Defaults to 30000 */
  timeout: number;
  /** Whether to automatically refresh tokens on 401. Defaults to true */
  autoRefresh: boolean;
}

const DEFAULT_CONFIG: ApiClientConfig = {
  baseUrl: process.env["NEXT_PUBLIC_ADMIN_API_URL"] ?? "/admin",
  accessTokenKey: "admin_access_token",
  refreshTokenKey: "admin_refresh_token",
  timeout: 30000,
  autoRefresh: true,
};

// ============================================================================
// Token Storage
// ============================================================================

/**
 * Token storage interface for managing authentication tokens.
 * Uses localStorage by default, can be replaced with other storage mechanisms.
 */
class TokenStorage {
  private readonly accessTokenKey: string;
  private readonly refreshTokenKey: string;

  constructor(accessTokenKey: string, refreshTokenKey: string) {
    this.accessTokenKey = accessTokenKey;
    this.refreshTokenKey = refreshTokenKey;
  }

  getAccessToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(this.accessTokenKey);
  }

  setAccessToken(token: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(this.accessTokenKey, token);
  }

  getRefreshToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(this.refreshTokenKey);
  }

  setRefreshToken(token: string): void {
    if (typeof window === "undefined") return;
    localStorage.setItem(this.refreshTokenKey, token);
  }

  setTokens(accessToken: string, refreshToken: string): void {
    this.setAccessToken(accessToken);
    this.setRefreshToken(refreshToken);
  }

  clearTokens(): void {
    if (typeof window === "undefined") return;
    localStorage.removeItem(this.accessTokenKey);
    localStorage.removeItem(this.refreshTokenKey);
  }

  hasTokens(): boolean {
    return this.getAccessToken() !== null;
  }
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Creates a typed API error from a response.
 */
function createApiError(
  message: string,
  status: number,
  statusText: string,
  response?: ApiErrorResponse,
): ApiError {
  const error = new Error(message) as ApiError;
  (error as { status: number }).status = status;
  (error as { statusText: string }).statusText = statusText;
  if (response?.detail !== undefined) {
    (error as { detail: string }).detail = response.detail;
  }
  if (response !== undefined) {
    (error as { response: ApiErrorResponse }).response = response;
  }
  return error;
}

/**
 * Parses an error response body.
 */
async function parseErrorResponse(response: Response): Promise<ApiErrorResponse | null> {
  try {
    const text = await response.text();
    if (!text) return null;
    return JSON.parse(text) as ApiErrorResponse;
  } catch {
    return null;
  }
}

/**
 * Type guard to check if an error is an ApiError.
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    error instanceof Error && "status" in error && typeof (error as ApiError).status === "number"
  );
}

// ============================================================================
// Request Interceptors
// ============================================================================

/**
 * Request interceptor function type.
 */
export type RequestInterceptor = (
  url: string,
  options: RequestInit,
) => Promise<{ url: string; options: RequestInit }> | { url: string; options: RequestInit };

/**
 * Response interceptor function type.
 */
export type ResponseInterceptor = (
  response: Response,
  request: { url: string; options: RequestInit },
) => Promise<Response> | Response;

/**
 * Error interceptor function type.
 */
export type ErrorInterceptor = (
  error: ApiError,
  request: { url: string; options: RequestInit },
) => Promise<void> | void;

// ============================================================================
// API Client Class
// ============================================================================

/**
 * Main API client class for communicating with the Litestar Admin backend.
 * Provides typed methods for all endpoints with built-in authentication handling.
 */
export class AdminApiClient {
  private readonly config: ApiClientConfig;
  private readonly tokenStorage: TokenStorage;
  private readonly requestInterceptors: RequestInterceptor[] = [];
  private readonly responseInterceptors: ResponseInterceptor[] = [];
  private readonly errorInterceptors: ErrorInterceptor[] = [];
  private refreshPromise: Promise<AuthTokens> | null = null;

  constructor(config: Partial<ApiClientConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.tokenStorage = new TokenStorage(this.config.accessTokenKey, this.config.refreshTokenKey);
  }

  // ==========================================================================
  // Interceptor Management
  // ==========================================================================

  /**
   * Add a request interceptor.
   */
  addRequestInterceptor(interceptor: RequestInterceptor): () => void {
    this.requestInterceptors.push(interceptor);
    return () => {
      const index = this.requestInterceptors.indexOf(interceptor);
      if (index > -1) {
        this.requestInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Add a response interceptor.
   */
  addResponseInterceptor(interceptor: ResponseInterceptor): () => void {
    this.responseInterceptors.push(interceptor);
    return () => {
      const index = this.responseInterceptors.indexOf(interceptor);
      if (index > -1) {
        this.responseInterceptors.splice(index, 1);
      }
    };
  }

  /**
   * Add an error interceptor.
   */
  addErrorInterceptor(interceptor: ErrorInterceptor): () => void {
    this.errorInterceptors.push(interceptor);
    return () => {
      const index = this.errorInterceptors.indexOf(interceptor);
      if (index > -1) {
        this.errorInterceptors.splice(index, 1);
      }
    };
  }

  // ==========================================================================
  // Token Management
  // ==========================================================================

  /**
   * Get the current access token.
   */
  getAccessToken(): string | null {
    return this.tokenStorage.getAccessToken();
  }

  /**
   * Get the current refresh token.
   */
  getRefreshToken(): string | null {
    return this.tokenStorage.getRefreshToken();
  }

  /**
   * Store authentication tokens.
   */
  setTokens(accessToken: string, refreshToken: string): void {
    this.tokenStorage.setTokens(accessToken, refreshToken);
  }

  /**
   * Store a single access token (used for OAuth callbacks).
   */
  setToken(accessToken: string): void {
    this.tokenStorage.setAccessToken(accessToken);
  }

  /**
   * Clear all stored tokens.
   */
  clearTokens(): void {
    this.tokenStorage.clearTokens();
  }

  /**
   * Check if the client has stored tokens.
   */
  isAuthenticated(): boolean {
    return this.tokenStorage.hasTokens();
  }

  // ==========================================================================
  // Core Request Method
  // ==========================================================================

  /**
   * Make an HTTP request to the API.
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit & { params?: Record<string, string | number | boolean | undefined> } = {},
    skipAuth = false,
  ): Promise<T> {
    const { params, ...fetchOptions } = options;

    // Build URL with query parameters
    let url = `${this.config.baseUrl}${endpoint}`;
    if (params) {
      const searchParams = new URLSearchParams();
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          searchParams.set(key, String(value));
        }
      }
      const queryString = searchParams.toString();
      if (queryString) {
        url += `?${queryString}`;
      }
    }

    // Prepare headers
    const headers = new Headers(fetchOptions.headers);
    if (!headers.has("Content-Type") && fetchOptions.body) {
      headers.set("Content-Type", "application/json");
    }

    // Add authorization header if authenticated
    if (!skipAuth) {
      const accessToken = this.tokenStorage.getAccessToken();
      if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }
    }

    let requestUrl = url;
    let requestOptions: RequestInit = {
      ...fetchOptions,
      headers,
    };

    // Run request interceptors
    for (const interceptor of this.requestInterceptors) {
      const result = await interceptor(requestUrl, requestOptions);
      requestUrl = result.url;
      requestOptions = result.options;
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.config.timeout);

    try {
      let response = await fetch(requestUrl, {
        ...requestOptions,
        signal: controller.signal,
        credentials: "include",
      });

      clearTimeout(timeoutId);

      // Run response interceptors
      for (const interceptor of this.responseInterceptors) {
        response = await interceptor(response, { url: requestUrl, options: requestOptions });
      }

      // Handle 401 Unauthorized - attempt token refresh
      if (response.status === 401 && this.config.autoRefresh && !skipAuth) {
        const refreshToken = this.tokenStorage.getRefreshToken();
        if (refreshToken) {
          try {
            await this.refreshAccessToken();
            // Retry the original request with the new token
            return this.request<T>(endpoint, options, false);
          } catch {
            // Refresh failed, clear tokens and throw original error
            this.clearTokens();
          }
        }
      }

      // Handle error responses
      if (!response.ok) {
        const errorResponse = await parseErrorResponse(response);
        const error = createApiError(
          errorResponse?.detail ?? response.statusText,
          response.status,
          response.statusText,
          errorResponse ?? undefined,
        );

        // Run error interceptors
        for (const interceptor of this.errorInterceptors) {
          await interceptor(error, { url: requestUrl, options: requestOptions });
        }

        throw error;
      }

      // Handle empty responses
      const text = await response.text();
      if (!text) {
        return undefined as T;
      }

      return JSON.parse(text) as T;
    } catch (error) {
      clearTimeout(timeoutId);

      // Handle abort/timeout
      if (error instanceof Error && error.name === "AbortError") {
        throw createApiError("Request timeout", 408, "Request Timeout");
      }

      throw error;
    }
  }

  // ==========================================================================
  // Authentication Endpoints
  // ==========================================================================

  /**
   * Authenticate with email and password.
   */
  async login(credentials: LoginCredentials): Promise<LoginResponse> {
    const response = await this.request<AuthTokens>(
      "/api/auth/login",
      {
        method: "POST",
        body: JSON.stringify(credentials),
      },
      true, // Skip auth for login
    );

    // Store tokens
    this.setTokens(response.access_token, response.refresh_token);

    return response as LoginResponse;
  }

  /**
   * End the current session and clear tokens.
   */
  async logout(): Promise<LogoutResponse> {
    try {
      const response = await this.request<LogoutResponse>("/api/auth/logout", {
        method: "POST",
      });
      return response;
    } finally {
      // Always clear tokens, even if the request fails
      this.clearTokens();
    }
  }

  /**
   * Change the current user's password.
   */
  async changePassword(
    currentPassword: string,
    newPassword: string,
  ): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
      }),
    });
  }

  /**
   * Refresh the access token using the refresh token.
   * This method is deduplicated - multiple concurrent calls will share the same promise.
   */
  async refreshAccessToken(): Promise<AuthTokens> {
    // If a refresh is already in progress, wait for it
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    const refreshToken = this.tokenStorage.getRefreshToken();
    if (!refreshToken) {
      throw createApiError("No refresh token available", 401, "Unauthorized");
    }

    this.refreshPromise = this.request<AuthTokens>(
      "/api/auth/refresh",
      {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      },
      true, // Skip auth for refresh
    )
      .then((response) => {
        this.setTokens(response.access_token, response.refresh_token);
        return response;
      })
      .finally(() => {
        this.refreshPromise = null;
      });

    return this.refreshPromise;
  }

  /**
   * Get the currently authenticated user's information.
   */
  async getCurrentUser(): Promise<AdminUser> {
    return this.request<AdminUser>("/api/auth/me");
  }

  // ==========================================================================
  // Models Endpoints
  // ==========================================================================

  /**
   * List all registered models.
   */
  async listModels(): Promise<ModelInfo[]> {
    return this.request<ModelInfo[]>("/api/models/");
  }

  /**
   * List records for a specific model with pagination and filtering.
   */
  async listRecords<T = ModelRecord>(
    model: string,
    params: ListQueryParams = {},
  ): Promise<ListRecordsResponse<T>> {
    const { page, pageSize, offset, limit, sortBy, sortOrder, search } = params;

    // Convert page/pageSize to offset/limit if provided
    const effectiveOffset = offset ?? (page && pageSize ? (page - 1) * pageSize : undefined);
    const effectiveLimit = limit ?? pageSize;

    return this.request<ListRecordsResponse<T>>(`/api/models/${encodeURIComponent(model)}`, {
      params: {
        offset: effectiveOffset,
        limit: effectiveLimit,
        sort_by: sortBy,
        sort_order: sortOrder,
        search,
      },
    });
  }

  /**
   * List records with pagination info computed.
   */
  async listRecordsPaginated<T = ModelRecord>(
    model: string,
    params: ListQueryParams = {},
  ): Promise<PaginatedResponse<T>> {
    const response = await this.listRecords<T>(model, params);
    const pageSize = params.pageSize ?? params.limit ?? 50;
    const page = Math.floor(response.offset / pageSize) + 1;
    const totalPages = Math.ceil(response.total / pageSize);

    return {
      items: response.items,
      total: response.total,
      page,
      pageSize,
      totalPages,
    };
  }

  /**
   * Get a single record by its primary key.
   */
  async getRecord<T = ModelRecord>(model: string, id: string | number): Promise<T> {
    return this.request<T>(
      `/api/models/${encodeURIComponent(model)}/${encodeURIComponent(String(id))}`,
    );
  }

  /**
   * Create a new record.
   */
  async createRecord<T = ModelRecord>(model: string, data: Partial<T>): Promise<T> {
    return this.request<T>(`/api/models/${encodeURIComponent(model)}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Full update a record (replace all fields).
   */
  async updateRecord<T = ModelRecord>(
    model: string,
    id: string | number,
    data: Partial<T>,
  ): Promise<T> {
    return this.request<T>(
      `/api/models/${encodeURIComponent(model)}/${encodeURIComponent(String(id))}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
    );
  }

  /**
   * Partial update a record (only provided fields).
   */
  async patchRecord<T = ModelRecord>(
    model: string,
    id: string | number,
    data: Partial<T>,
  ): Promise<T> {
    return this.request<T>(
      `/api/models/${encodeURIComponent(model)}/${encodeURIComponent(String(id))}`,
      {
        method: "PATCH",
        body: JSON.stringify(data),
      },
    );
  }

  /**
   * Delete a record.
   */
  async deleteRecord(
    model: string,
    id: string | number,
    softDelete = false,
  ): Promise<DeleteResponse> {
    return this.request<DeleteResponse>(
      `/api/models/${encodeURIComponent(model)}/${encodeURIComponent(String(id))}`,
      {
        method: "DELETE",
        params: { soft_delete: softDelete },
      },
    );
  }

  /**
   * Get the JSON schema for a model (used for form generation).
   * @param model - The model name
   * @param mode - Form mode: 'create' or 'edit' (affects required fields)
   */
  async getModelSchema(model: string, mode: "create" | "edit" = "create"): Promise<ModelSchema> {
    return this.request<ModelSchema>(`/api/models/${encodeURIComponent(model)}/schema`, {
      params: { mode },
    });
  }

  // ==========================================================================
  // Dashboard Endpoints
  // ==========================================================================

  /**
   * Get dashboard statistics including model counts.
   */
  async getDashboardStats(): Promise<DashboardStats> {
    return this.request<DashboardStats>("/api/dashboard/stats");
  }

  /**
   * Get recent activity from the audit log.
   * @param limit - Maximum number of entries to return
   * @param modelName - Optional filter by model name
   * @param recordId - Optional filter by record ID
   */
  async getActivity(
    limit = 50,
    modelName?: string,
    recordId?: string,
  ): Promise<ActivityItem[]> {
    return this.request<ActivityItem[]>("/api/dashboard/activity", {
      params: { limit, model_name: modelName, record_id: recordId },
    });
  }

  // ==========================================================================
  // Export Endpoints
  // ==========================================================================

  /**
   * Export all records from a model.
   * Returns a URL that can be used to download the export.
   */
  getExportUrl(model: string, format: ExportFormat = "csv"): string {
    const params = new URLSearchParams({ format });
    const token = this.getAccessToken();
    if (token) {
      params.set("token", token);
    }
    return `${this.config.baseUrl}/api/models/${encodeURIComponent(model)}/export?${params.toString()}`;
  }

  /**
   * Export all records from a model as a blob.
   */
  async exportRecords(model: string, format: ExportFormat = "csv"): Promise<Blob> {
    const response = await fetch(this.getExportUrl(model, format));
    if (!response.ok) {
      const errorResponse = await parseErrorResponse(response);
      throw createApiError(
        errorResponse?.detail ?? response.statusText,
        response.status,
        response.statusText,
        errorResponse ?? undefined,
      );
    }
    return response.blob();
  }

  /**
   * Export selected records by their IDs.
   */
  async exportSelected(model: string, request: BulkExportRequest): Promise<Blob> {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };
    const token = this.getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(
      `${this.config.baseUrl}/api/models/${encodeURIComponent(model)}/bulk/export`,
      {
        method: "POST",
        headers,
        body: JSON.stringify(request),
      },
    );

    if (!response.ok) {
      const errorResponse = await parseErrorResponse(response);
      throw createApiError(
        errorResponse?.detail ?? response.statusText,
        response.status,
        response.statusText,
        errorResponse ?? undefined,
      );
    }

    return response.blob();
  }

  // ==========================================================================
  // Bulk Action Endpoints
  // ==========================================================================

  /**
   * Delete multiple records.
   */
  async bulkDelete(model: string, request: BulkDeleteRequest): Promise<BulkDeleteResponse> {
    return this.request<BulkDeleteResponse>(
      `/api/models/${encodeURIComponent(model)}/bulk/delete`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    );
  }

  /**
   * Execute a custom bulk action.
   */
  async bulkAction(
    model: string,
    action: string,
    request: BulkActionRequest,
  ): Promise<BulkActionResponse> {
    return this.request<BulkActionResponse>(
      `/api/models/${encodeURIComponent(model)}/bulk/${encodeURIComponent(action)}`,
      {
        method: "POST",
        body: JSON.stringify(request),
      },
    );
  }

  // ==========================================================================
  // Custom View Endpoints
  // ==========================================================================

  /**
   * List all registered custom views.
   */
  async listCustomViews(): Promise<CustomViewInfo[]> {
    return this.request<CustomViewInfo[]>("/api/views/custom/");
  }

  /**
   * Get items from a custom view.
   */
  async getCustomViewList<T = Record<string, unknown>>(
    identity: string,
    params: ListQueryParams = {},
  ): Promise<CustomViewListResponse<T>> {
    const { page, pageSize, offset, limit, sortBy, sortOrder, search, filters } = params;
    const effectiveOffset = offset ?? (page && pageSize ? (page - 1) * pageSize : undefined);
    const effectiveLimit = limit ?? pageSize;

    return this.request<CustomViewListResponse<T>>(
      `/api/views/custom/${encodeURIComponent(identity)}`,
      {
        params: {
          offset: effectiveOffset,
          limit: effectiveLimit,
          sort_by: sortBy,
          sort_order: sortOrder,
          search,
          filters: filters ? JSON.stringify(filters) : undefined,
        },
      },
    );
  }

  /**
   * Get a single item from a custom view.
   */
  async getCustomViewItem<T = Record<string, unknown>>(
    identity: string,
    itemId: string,
  ): Promise<T> {
    return this.request<T>(
      `/api/views/custom/${encodeURIComponent(identity)}/${encodeURIComponent(itemId)}`,
    );
  }

  /**
   * Create a new item in a custom view.
   */
  async createCustomViewItem<T = Record<string, unknown>>(
    identity: string,
    data: Partial<T>,
  ): Promise<T> {
    return this.request<T>(`/api/views/custom/${encodeURIComponent(identity)}`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an item in a custom view.
   */
  async updateCustomViewItem<T = Record<string, unknown>>(
    identity: string,
    itemId: string,
    data: Partial<T>,
  ): Promise<T> {
    return this.request<T>(
      `/api/views/custom/${encodeURIComponent(identity)}/${encodeURIComponent(itemId)}`,
      {
        method: "PUT",
        body: JSON.stringify(data),
      },
    );
  }

  /**
   * Delete an item from a custom view.
   */
  async deleteCustomViewItem(identity: string, itemId: string): Promise<void> {
    return this.request<void>(
      `/api/views/custom/${encodeURIComponent(identity)}/${encodeURIComponent(itemId)}`,
      {
        method: "DELETE",
      },
    );
  }

  /**
   * Get the schema for a custom view (for form generation).
   */
  async getCustomViewSchema(identity: string): Promise<CustomViewSchemaResponse> {
    return this.request<CustomViewSchemaResponse>(
      `/api/views/custom/${encodeURIComponent(identity)}/schema`,
    );
  }

  // ==========================================================================
  // Action View Endpoints
  // ==========================================================================

  /**
   * List all registered actions.
   */
  async listActions(): Promise<ActionInfo[]> {
    return this.request<ActionInfo[]>("/api/views/actions/");
  }

  /**
   * Get details of a specific action.
   */
  async getAction(identity: string): Promise<ActionInfo> {
    return this.request<ActionInfo>(`/api/views/actions/${encodeURIComponent(identity)}`);
  }

  /**
   * Execute an action with form data.
   */
  async executeAction(identity: string, data: Record<string, unknown>): Promise<ActionResult> {
    return this.request<ActionResult>(
      `/api/views/actions/${encodeURIComponent(identity)}/execute`,
      {
        method: "POST",
        body: JSON.stringify(data),
      },
    );
  }

  // ==========================================================================
  // Page View Endpoints
  // ==========================================================================

  /**
   * List all registered pages.
   */
  async listPages(): Promise<PageInfo[]> {
    return this.request<PageInfo[]>("/api/views/pages/");
  }

  /**
   * Get details of a specific page.
   */
  async getPage(identity: string): Promise<PageInfo> {
    return this.request<PageInfo>(`/api/views/pages/${encodeURIComponent(identity)}`);
  }

  /**
   * Get the content of a page (for dynamic pages).
   */
  async getPageContent(identity: string): Promise<PageContent> {
    return this.request<PageContent>(`/api/views/pages/${encodeURIComponent(identity)}/content`);
  }

  // ==========================================================================
  // Link View Endpoints
  // ==========================================================================

  /**
   * List all registered links.
   */
  async listLinks(): Promise<LinkInfo[]> {
    return this.request<LinkInfo[]>("/api/views/links/");
  }

  // ==========================================================================
  // Embed View Endpoints
  // ==========================================================================

  /**
   * List all registered embeds.
   */
  async listEmbeds(): Promise<EmbedInfo[]> {
    return this.request<EmbedInfo[]>("/api/views/embeds/");
  }

  /**
   * Get configuration for an embed.
   */
  async getEmbedConfig(identity: string): Promise<EmbedConfig> {
    return this.request<EmbedConfig>(`/api/views/embeds/${encodeURIComponent(identity)}/config`);
  }

  /**
   * Get dynamic props for an embed component.
   */
  async getEmbedProps(identity: string): Promise<Record<string, unknown>> {
    return this.request<Record<string, unknown>>(
      `/api/views/embeds/${encodeURIComponent(identity)}/props`,
    );
  }

  // ==========================================================================
  // User Management Endpoints
  // ==========================================================================

  /**
   * List admin users with pagination and filtering.
   */
  async listUsers(params: UserListParams = {}): Promise<UserListResponse> {
    return this.request<UserListResponse>("/api/users/", {
      params: {
        page: params.page,
        page_size: params.page_size,
        email: params.email,
        active: params.active,
        role: params.role,
        sort_by: params.sort_by,
        sort_order: params.sort_order,
      },
    });
  }

  /**
   * Get a single admin user by ID.
   */
  async getUser(userId: string): Promise<UserResponse> {
    return this.request<UserResponse>(`/api/users/${encodeURIComponent(userId)}`);
  }

  /**
   * Create a new admin user.
   */
  async createUser(data: UserCreateRequest): Promise<UserResponse> {
    return this.request<UserResponse>("/api/users/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /**
   * Update an existing admin user.
   */
  async updateUser(userId: string, data: UserUpdateRequest): Promise<UserResponse> {
    return this.request<UserResponse>(`/api/users/${encodeURIComponent(userId)}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  /**
   * Delete an admin user.
   */
  async deleteUser(userId: string): Promise<void> {
    return this.request<void>(`/api/users/${encodeURIComponent(userId)}`, {
      method: "DELETE",
    });
  }

  /**
   * Activate an admin user.
   */
  async activateUser(userId: string): Promise<ActivateDeactivateResponse> {
    return this.request<ActivateDeactivateResponse>(
      `/api/users/${encodeURIComponent(userId)}/activate`,
      {
        method: "POST",
      },
    );
  }

  /**
   * Deactivate an admin user.
   */
  async deactivateUser(userId: string): Promise<ActivateDeactivateResponse> {
    return this.request<ActivateDeactivateResponse>(
      `/api/users/${encodeURIComponent(userId)}/deactivate`,
      {
        method: "POST",
      },
    );
  }

  // ==========================================================================
  // File Upload Endpoints
  // ==========================================================================

  /**
   * Upload a file with progress tracking.
   * @param file - The file to upload
   * @param options - Upload options including model/field names and progress callback
   * @returns Promise resolving to the uploaded file information
   */
  async uploadFile(
    file: File,
    options?: {
      modelName?: string | undefined;
      fieldName?: string | undefined;
      onProgress?: ((progress: number) => void) | undefined;
      generateThumbnail?: boolean | undefined;
    },
  ): Promise<FileUploadResponse> {
    const { modelName = "unknown", fieldName = "file", onProgress, generateThumbnail } = options ?? {};

    const formData = new FormData();
    formData.append("data", file);

    const accessToken = this.tokenStorage.getAccessToken();

    // Auto-detect if thumbnail should be generated for image files
    const isImage = file.type.startsWith("image/");
    const shouldGenerateThumbnail = generateThumbnail ?? isImage;

    // Build URL with query parameters for Litestar
    const queryParams = new URLSearchParams({
      model_name: modelName,
      field_name: fieldName,
      generate_thumbnail: shouldGenerateThumbnail ? "true" : "false",
    });

    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();

      xhr.upload.addEventListener("progress", (event) => {
        if (event.lengthComputable && onProgress) {
          const progress = Math.round((event.loaded / event.total) * 100);
          onProgress(progress);
        }
      });

      xhr.addEventListener("load", () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const response = JSON.parse(xhr.responseText) as FileUploadResponse;
            resolve(response);
          } catch {
            reject(createApiError("Invalid response format", xhr.status, xhr.statusText));
          }
        } else {
          let errorMessage = xhr.statusText;
          try {
            const errorResponse = JSON.parse(xhr.responseText) as ApiErrorResponse;
            errorMessage = errorResponse.detail || errorMessage;
          } catch {
            // Use default error message
          }
          reject(createApiError(errorMessage, xhr.status, xhr.statusText));
        }
      });

      xhr.addEventListener("error", () => {
        reject(createApiError("Network error during upload", 0, "Network Error"));
      });

      xhr.addEventListener("abort", () => {
        reject(createApiError("Upload aborted", 0, "Aborted"));
      });

      xhr.open("POST", `${this.config.baseUrl}/api/files/upload?${queryParams.toString()}`);

      if (accessToken) {
        xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
      }

      xhr.send(formData);
    });
  }

  /**
   * Upload multiple files with progress tracking.
   * @param files - Array of files to upload
   * @param options - Upload options including model/field names and progress callback
   * @returns Promise resolving to array of uploaded file information
   */
  async uploadFiles(
    files: File[],
    options?: {
      modelName?: string | undefined;
      fieldName?: string | undefined;
      onProgress?: ((progress: number) => void) | undefined;
      generateThumbnail?: boolean | undefined;
    },
  ): Promise<FileUploadResponse[]> {
    const { modelName, fieldName, onProgress, generateThumbnail } = options ?? {};
    const results: FileUploadResponse[] = [];
    const totalFiles = files.length;
    let completedCount = 0;

    for (const file of files) {
      const result = await this.uploadFile(file, {
        modelName,
        fieldName,
        generateThumbnail,
        onProgress: (fileProgress) => {
          if (onProgress) {
            const overallProgress = Math.round(
              ((completedCount + fileProgress / 100) / totalFiles) * 100,
            );
            onProgress(overallProgress);
          }
        },
      });
      results.push(result);
      completedCount++;
    }

    return results;
  }

  /**
   * Delete an uploaded file.
   * @param fileId - The ID of the file to delete
   */
  async deleteFile(fileId: string): Promise<FileDeleteResponse> {
    return this.request<FileDeleteResponse>(
      `/api/files/${encodeURIComponent(fileId)}`,
      {
        method: "DELETE",
      },
    );
  }

  /**
   * Get the URL for a file by its ID.
   * @param fileId - The ID of the file
   * @returns The URL to access the file
   */
  getFileUrl(fileId: string): string {
    return `${this.config.baseUrl}/api/files/${encodeURIComponent(fileId)}`;
  }

  /**
   * Get the thumbnail URL for a file by its ID.
   * @param fileId - The ID of the file
   * @returns The URL to access the file's thumbnail
   */
  getFileThumbnailUrl(fileId: string): string {
    return `${this.config.baseUrl}/api/files/${encodeURIComponent(fileId)}/thumbnail`;
  }

  // ==========================================================================
  // Relationship Picker Endpoints
  // ==========================================================================

  /**
   * Search related records for a relationship field.
   * Used for autocomplete in FK/relationship picker components.
   * @param model - The source model name
   * @param field - The relationship field name
   * @param params - Search parameters
   */
  async searchRelationship(
    model: string,
    field: string,
    params: RelationshipSearchParams = {},
  ): Promise<RelationshipSearchResponse> {
    return this.request<RelationshipSearchResponse>(
      `/api/models/${encodeURIComponent(model)}/relationships/${encodeURIComponent(field)}/search`,
      {
        params: {
          q: params.q,
          limit: params.limit,
          page: params.page,
        },
      },
    );
  }

  /**
   * Get specific related records by their IDs.
   * Used to resolve existing FK values for display in forms.
   * @param model - The source model name
   * @param field - The relationship field name
   * @param ids - Array of IDs to resolve
   */
  async getRelationshipOptions(
    model: string,
    field: string,
    ids: (string | number)[],
  ): Promise<RelationshipSearchResponse> {
    if (ids.length === 0) {
      return { items: [], total: 0, has_more: false };
    }
    return this.request<RelationshipSearchResponse>(
      `/api/models/${encodeURIComponent(model)}/relationships/${encodeURIComponent(field)}/options`,
      {
        params: {
          ids: ids.join(","),
        },
      },
    );
  }

  // ==========================================================================
  // CSV Import Endpoints
  // ==========================================================================

  /**
   * Preview a CSV file for import.
   * Parses the file and returns detected types, schema info, and preview rows.
   * @param model - The model name to import into
   * @param file - The CSV file to preview
   */
  async previewImport(model: string, file: File): Promise<ImportPreviewResponse> {
    const formData = new FormData();
    formData.append("data", file);

    const accessToken = this.tokenStorage.getAccessToken();
    const headers: HeadersInit = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const response = await fetch(
      `${this.config.baseUrl}/api/models/${encodeURIComponent(model)}/import/preview`,
      {
        method: "POST",
        headers,
        body: formData,
      },
    );

    if (!response.ok) {
      const errorResponse = await parseErrorResponse(response);
      throw createApiError(
        errorResponse?.detail ?? response.statusText,
        response.status,
        response.statusText,
        errorResponse ?? undefined,
      );
    }

    return response.json() as Promise<ImportPreviewResponse>;
  }

  /**
   * Validate CSV data with column mappings.
   * Returns validation errors and counts.
   * @param model - The model name to import into
   * @param file - The CSV file to validate
   * @param columnMappings - Array of column mappings
   */
  async validateImport(
    model: string,
    file: File,
    columnMappings: { csv_column: string; model_field: string; transform?: string }[],
  ): Promise<ImportValidationResponse> {
    const formData = new FormData();
    formData.append("data", file);

    const accessToken = this.tokenStorage.getAccessToken();
    const headers: HeadersInit = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    // Add column_mappings as query parameters (Litestar expects this for JSON body with file upload)
    const url = new URL(
      `${this.config.baseUrl}/api/models/${encodeURIComponent(model)}/import/validate`,
      window.location.origin,
    );
    url.searchParams.set("column_mappings", JSON.stringify(columnMappings));

    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorResponse = await parseErrorResponse(response);
      throw createApiError(
        errorResponse?.detail ?? response.statusText,
        response.status,
        response.statusText,
        errorResponse ?? undefined,
      );
    }

    return response.json() as Promise<ImportValidationResponse>;
  }

  /**
   * Execute CSV import with column mappings.
   * Currently a stub - will be implemented in task 9.7.4.
   * @param model - The model name to import into
   * @param file - The CSV file to import
   * @param columnMappings - Array of column mappings
   */
  async executeImport(
    model: string,
    file: File,
    columnMappings: { csv_column: string; model_field: string; transform?: string }[],
  ): Promise<ImportExecuteResponse> {
    const formData = new FormData();
    formData.append("data", file);

    const accessToken = this.tokenStorage.getAccessToken();
    const headers: HeadersInit = {};
    if (accessToken) {
      headers["Authorization"] = `Bearer ${accessToken}`;
    }

    const url = new URL(
      `${this.config.baseUrl}/api/models/${encodeURIComponent(model)}/import/execute`,
      window.location.origin,
    );
    url.searchParams.set("column_mappings", JSON.stringify(columnMappings));

    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const errorResponse = await parseErrorResponse(response);
      throw createApiError(
        errorResponse?.detail ?? response.statusText,
        response.status,
        response.statusText,
        errorResponse ?? undefined,
      );
    }

    return response.json() as Promise<ImportExecuteResponse>;
  }
}

// ============================================================================
// Default Instance
// ============================================================================

/**
 * Default API client instance.
 * Can be used directly or replaced with a custom configured instance.
 */
export const apiClient = new AdminApiClient();

/**
 * Convenience methods that use the default client.
 * These provide a simpler API for common operations.
 */
export const api = {
  // Auth
  login: (credentials: LoginCredentials) => apiClient.login(credentials),
  logout: () => apiClient.logout(),
  refreshToken: () => apiClient.refreshAccessToken(),
  getCurrentUser: () => apiClient.getCurrentUser(),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.changePassword(currentPassword, newPassword),

  // Models
  listModels: () => apiClient.listModels(),
  listRecords: <T = ModelRecord>(model: string, params?: ListQueryParams) =>
    apiClient.listRecords<T>(model, params),
  listRecordsPaginated: <T = ModelRecord>(model: string, params?: ListQueryParams) =>
    apiClient.listRecordsPaginated<T>(model, params),
  getRecord: <T = ModelRecord>(model: string, id: string | number) =>
    apiClient.getRecord<T>(model, id),
  createRecord: <T = ModelRecord>(model: string, data: Partial<T>) =>
    apiClient.createRecord<T>(model, data),
  updateRecord: <T = ModelRecord>(model: string, id: string | number, data: Partial<T>) =>
    apiClient.updateRecord<T>(model, id, data),
  patchRecord: <T = ModelRecord>(model: string, id: string | number, data: Partial<T>) =>
    apiClient.patchRecord<T>(model, id, data),
  deleteRecord: (model: string, id: string | number, softDelete?: boolean) =>
    apiClient.deleteRecord(model, id, softDelete),
  getModelSchema: (model: string, mode?: "create" | "edit") =>
    apiClient.getModelSchema(model, mode),

  // Dashboard
  getDashboardStats: () => apiClient.getDashboardStats(),
  getActivity: (limit?: number, modelName?: string, recordId?: string) =>
    apiClient.getActivity(limit, modelName, recordId),

  // Export
  getExportUrl: (model: string, format?: ExportFormat) => apiClient.getExportUrl(model, format),
  exportRecords: (model: string, format?: ExportFormat) => apiClient.exportRecords(model, format),
  exportSelected: (model: string, request: BulkExportRequest) =>
    apiClient.exportSelected(model, request),

  // Bulk Actions
  bulkDelete: (model: string, request: BulkDeleteRequest) => apiClient.bulkDelete(model, request),
  bulkAction: (model: string, action: string, request: BulkActionRequest) =>
    apiClient.bulkAction(model, action, request),

  // Custom Views
  listCustomViews: () => apiClient.listCustomViews(),
  getCustomViewList: <T = Record<string, unknown>>(identity: string, params?: ListQueryParams) =>
    apiClient.getCustomViewList<T>(identity, params),
  getCustomViewItem: <T = Record<string, unknown>>(identity: string, itemId: string) =>
    apiClient.getCustomViewItem<T>(identity, itemId),
  createCustomViewItem: <T = Record<string, unknown>>(identity: string, data: Partial<T>) =>
    apiClient.createCustomViewItem<T>(identity, data),
  updateCustomViewItem: <T = Record<string, unknown>>(
    identity: string,
    itemId: string,
    data: Partial<T>,
  ) => apiClient.updateCustomViewItem<T>(identity, itemId, data),
  deleteCustomViewItem: (identity: string, itemId: string) =>
    apiClient.deleteCustomViewItem(identity, itemId),
  getCustomViewSchema: (identity: string) => apiClient.getCustomViewSchema(identity),

  // Actions
  listActions: () => apiClient.listActions(),
  getAction: (identity: string) => apiClient.getAction(identity),
  executeAction: (identity: string, data: Record<string, unknown>) =>
    apiClient.executeAction(identity, data),

  // Pages
  listPages: () => apiClient.listPages(),
  getPage: (identity: string) => apiClient.getPage(identity),
  getPageContent: (identity: string) => apiClient.getPageContent(identity),

  // Links
  listLinks: () => apiClient.listLinks(),

  // Embeds
  listEmbeds: () => apiClient.listEmbeds(),
  getEmbedConfig: (identity: string) => apiClient.getEmbedConfig(identity),
  getEmbedProps: (identity: string) => apiClient.getEmbedProps(identity),

  // User Management
  listUsers: (params?: UserListParams) => apiClient.listUsers(params),
  getUser: (userId: string) => apiClient.getUser(userId),
  createUser: (data: UserCreateRequest) => apiClient.createUser(data),
  updateUser: (userId: string, data: UserUpdateRequest) => apiClient.updateUser(userId, data),
  deleteUser: (userId: string) => apiClient.deleteUser(userId),
  activateUser: (userId: string) => apiClient.activateUser(userId),
  deactivateUser: (userId: string) => apiClient.deactivateUser(userId),

  // File Upload
  uploadFile: (file: File, options?: { modelName?: string | undefined; fieldName?: string | undefined; onProgress?: ((progress: number) => void) | undefined; generateThumbnail?: boolean | undefined }) =>
    apiClient.uploadFile(file, options),
  uploadFiles: (files: File[], options?: { modelName?: string | undefined; fieldName?: string | undefined; onProgress?: ((progress: number) => void) | undefined; generateThumbnail?: boolean | undefined }) =>
    apiClient.uploadFiles(files, options),
  deleteFile: (fileId: string) => apiClient.deleteFile(fileId),
  getFileUrl: (fileId: string) => apiClient.getFileUrl(fileId),
  getFileThumbnailUrl: (fileId: string) => apiClient.getFileThumbnailUrl(fileId),

  // Relationship Picker
  searchRelationship: (model: string, field: string, params?: RelationshipSearchParams) =>
    apiClient.searchRelationship(model, field, params),
  getRelationshipOptions: (model: string, field: string, ids: (string | number)[]) =>
    apiClient.getRelationshipOptions(model, field, ids),

  // CSV Import
  previewImport: (model: string, file: File) => apiClient.previewImport(model, file),
  validateImport: (
    model: string,
    file: File,
    columnMappings: { csv_column: string; model_field: string; transform?: string }[],
  ) => apiClient.validateImport(model, file, columnMappings),
  executeImport: (
    model: string,
    file: File,
    columnMappings: { csv_column: string; model_field: string; transform?: string }[],
  ) => apiClient.executeImport(model, file, columnMappings),
};

// Re-export types for convenience
export type { ApiError };
