/**
 * Core type definitions for the Litestar Admin frontend.
 * These types mirror the backend dataclass structures for type-safe API communication.
 */

// ============================================================================
// Authentication Types
// ============================================================================

/**
 * Credentials for user login.
 */
export interface LoginCredentials {
  readonly email: string;
  readonly password: string;
}

/**
 * Request payload for token refresh.
 */
export interface RefreshTokenRequest {
  readonly refresh_token: string;
}

/**
 * Response containing authentication tokens.
 */
export interface AuthTokens {
  readonly access_token: string;
  readonly refresh_token: string;
  readonly token_type: string;
  readonly expires_in: number | null;
}

/**
 * Authenticated user information from /auth/me endpoint.
 */
export interface AdminUser {
  readonly id: string | number;
  readonly email: string;
  readonly roles: readonly string[];
  readonly permissions: readonly string[];
}

/**
 * Combined login response with tokens and optional user info.
 */
export interface LoginResponse extends AuthTokens {
  readonly user?: AdminUser;
}

/**
 * Response for logout operation.
 */
export interface LogoutResponse {
  readonly success: boolean;
  readonly message: string;
}

// ============================================================================
// Model Types
// ============================================================================

/**
 * Permissions for model operations.
 */
export interface ModelPermissions {
  readonly canCreate: boolean;
  readonly canRead: boolean;
  readonly canUpdate: boolean;
  readonly canDelete: boolean;
  readonly canExport: boolean;
}

/**
 * Information about a registered model from the API.
 */
export interface ModelInfo {
  readonly name: string;
  readonly model_name: string;
  readonly icon: string;
  readonly category: string | null;
  readonly can_create: boolean;
  readonly can_edit: boolean;
  readonly can_delete: boolean;
  readonly can_view_details: boolean;
}

/**
 * Represents a registered model in the admin panel (frontend-friendly version).
 */
export interface AdminModel {
  readonly name: string;
  readonly identity: string;
  readonly displayName: string;
  readonly icon?: string;
  readonly category?: string;
  readonly permissions: ModelPermissions;
}

/**
 * Generic model record - a dictionary of field values.
 */
export type ModelRecord = Record<string, unknown>;

/**
 * Represents a column definition for model display.
 */
export interface ColumnDefinition {
  readonly name: string;
  readonly label: string;
  readonly type: ColumnType;
  readonly sortable: boolean;
  readonly searchable: boolean;
  readonly visible: boolean;
}

/**
 * Supported column types.
 */
export type ColumnType =
  | 'string'
  | 'number'
  | 'integer'
  | 'boolean'
  | 'date'
  | 'datetime'
  | 'email'
  | 'url'
  | 'json'
  | 'array'
  | 'object'
  | 'relation';

/**
 * JSON Schema property definition for form generation.
 */
export interface SchemaProperty {
  readonly type: string;
  readonly title?: string;
  readonly description?: string;
  readonly default?: unknown;
  readonly format?: string;
  readonly enum?: readonly unknown[];
  readonly minimum?: number;
  readonly maximum?: number;
  readonly minLength?: number;
  readonly maxLength?: number;
  readonly pattern?: string;
  readonly items?: SchemaProperty;
  readonly properties?: Record<string, SchemaProperty>;
  readonly required?: readonly string[];
  readonly readOnly?: boolean;
}

/**
 * JSON Schema for a model, used for form generation.
 */
export interface ModelSchema {
  readonly $schema?: string;
  readonly type: 'object';
  readonly title: string;
  readonly description?: string;
  readonly properties: Record<string, SchemaProperty>;
  readonly required: readonly string[];
}

// ============================================================================
// Pagination & Query Types
// ============================================================================

/**
 * Pagination parameters for list requests.
 */
export interface PaginationParams {
  readonly page?: number;
  readonly pageSize?: number;
  readonly offset?: number;
  readonly limit?: number;
}

/**
 * Sorting parameters for list requests.
 */
export interface SortParams {
  readonly sortBy?: string;
  readonly sortOrder?: 'asc' | 'desc';
}

/**
 * Search and filter parameters.
 */
export interface FilterParams {
  readonly search?: string;
  readonly filters?: Record<string, unknown>;
}

/**
 * Combined query parameters for listing records.
 */
export interface ListQueryParams extends PaginationParams, SortParams, FilterParams {}

/**
 * Paginated response from the API (backend format).
 */
export interface ListRecordsResponse<T = ModelRecord> {
  readonly items: readonly T[];
  readonly total: number;
  readonly offset: number;
  readonly limit: number;
}

/**
 * Paginated response with computed page info (frontend format).
 */
export interface PaginatedResponse<T = ModelRecord> {
  readonly items: readonly T[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
}

// ============================================================================
// Dashboard Types
// ============================================================================

/**
 * Statistics for a single registered model.
 */
export interface ModelStats {
  readonly name: string;
  readonly model_name: string;
  readonly count: number;
  readonly icon: string;
  readonly category: string | null;
}

/**
 * Data for a custom dashboard widget.
 */
export interface WidgetData {
  readonly id: string;
  readonly type: 'metric' | 'chart' | 'list' | 'custom';
  readonly title: string;
  readonly data: Record<string, unknown>;
  readonly config: Record<string, unknown>;
}

/**
 * Complete dashboard statistics response.
 */
export interface DashboardStats {
  readonly models: readonly ModelStats[];
  readonly total_records: number;
  readonly total_models: number;
  readonly widgets: readonly WidgetData[];
}

/**
 * A single activity log entry.
 */
export interface ActivityItem {
  readonly action: 'create' | 'update' | 'delete' | string;
  readonly model: string;
  readonly record_id: string | number | null;
  readonly timestamp: string;
  readonly user: string | null;
  readonly details: Record<string, unknown>;
}

// ============================================================================
// Export Types
// ============================================================================

/**
 * Supported export formats.
 */
export type ExportFormat = 'csv' | 'json';

/**
 * Request for bulk export operation.
 */
export interface BulkExportRequest {
  readonly ids: readonly (string | number)[];
  readonly format: ExportFormat;
}

// ============================================================================
// Bulk Action Types
// ============================================================================

/**
 * Request body for bulk delete operations.
 */
export interface BulkDeleteRequest {
  readonly ids: readonly (string | number)[];
  readonly soft_delete?: boolean;
}

/**
 * Response for bulk delete operations.
 */
export interface BulkDeleteResponse {
  readonly deleted: number;
  readonly success: boolean;
}

/**
 * Request body for custom bulk actions.
 */
export interface BulkActionRequest {
  readonly ids: readonly (string | number)[];
  readonly params?: Record<string, unknown>;
}

/**
 * Response for custom bulk actions.
 */
export interface BulkActionResponse {
  readonly success: boolean;
  readonly affected: number;
  readonly result: Record<string, unknown>;
}

// ============================================================================
// Error Types
// ============================================================================

/**
 * Standard API error response structure.
 */
export interface ApiErrorResponse {
  readonly status_code: number;
  readonly detail: string;
  readonly extra?: Record<string, unknown>;
}

/**
 * Extended Error with API-specific properties.
 */
export interface ApiError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly detail?: string;
  readonly response?: ApiErrorResponse;
}

/**
 * Validation error for a specific field.
 */
export interface FieldError {
  readonly field: string;
  readonly message: string;
  readonly code?: string;
}

/**
 * Validation error response containing field-level errors.
 */
export interface ValidationErrorResponse extends ApiErrorResponse {
  readonly errors: readonly FieldError[];
}

// ============================================================================
// Configuration Types
// ============================================================================

/**
 * Admin panel configuration.
 */
export interface AdminConfig {
  readonly title: string;
  readonly logo?: string;
  readonly favicon?: string;
  readonly primaryColor?: string;
  readonly models: readonly AdminModel[];
}

/**
 * User session information (extended from AdminUser).
 */
export interface UserSession extends AdminUser {
  readonly name?: string;
  readonly avatar?: string;
}

// ============================================================================
// Delete Response Types
// ============================================================================

/**
 * Response for single record delete operation.
 */
export interface DeleteResponse {
  readonly success: boolean;
  readonly message: string;
}

// ============================================================================
// Navigation Types
// ============================================================================

/**
 * A single navigation item in the sidebar.
 */
export interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly href: string;
  readonly icon?: React.ComponentType<{ className?: string }>;
  readonly badge?: string | number;
}

/**
 * A category of navigation items with collapsible behavior.
 */
export interface NavCategory {
  readonly id: string;
  readonly label: string;
  readonly items: readonly NavItem[];
  readonly defaultOpen?: boolean;
}
