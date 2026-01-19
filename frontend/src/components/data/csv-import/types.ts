/**
 * Types for CSV Import Wizard components.
 */

// ============================================================================
// Backend API Types
// ============================================================================

/**
 * Transform options for column mapping.
 */
export type ColumnTransform = "none" | "lowercase" | "uppercase" | "trim";

/**
 * Column type information from backend type detection.
 */
export interface BackendColumnTypeInfo {
  /** CSV column header name */
  readonly csv_column: string;
  /** Detected data type (string, integer, float, boolean, date, datetime) */
  readonly detected_type: string;
  /** Sample values from this column */
  readonly sample_values: string[];
  /** Whether null/empty values were detected */
  readonly nullable: boolean;
}

/**
 * Model field information from backend schema.
 */
export interface BackendModelFieldInfo {
  /** Field/column name */
  readonly name: string;
  /** JSON schema type */
  readonly type: string;
  /** Optional format (date, datetime, email, etc.) */
  readonly format?: string;
  /** Whether the field is nullable */
  readonly nullable: boolean;
  /** Whether the field is required */
  readonly required: boolean;
  /** Whether this is a primary key */
  readonly primary_key: boolean;
  /** Maximum length for string fields */
  readonly max_length?: number;
}

/**
 * Response from the preview endpoint.
 */
export interface ImportPreviewResponse {
  /** CSV column headers */
  readonly headers: string[];
  /** First N rows of data as objects */
  readonly preview_rows: Record<string, unknown>[];
  /** Detected type information for each column */
  readonly column_types: BackendColumnTypeInfo[];
  /** Model field information for mapping */
  readonly model_schema: BackendModelFieldInfo[];
  /** Detected delimiter character */
  readonly delimiter: string;
  /** Detected file encoding */
  readonly encoding: string;
  /** Total number of data rows */
  readonly total_rows: number;
}

/**
 * Column mapping to send to backend.
 */
export interface BackendColumnMapping {
  /** CSV column header name */
  readonly csv_column: string;
  /** Target model field name */
  readonly model_field: string;
  /** Optional transformation to apply */
  readonly transform?: ColumnTransform;
}

/**
 * Row-level validation error from backend.
 */
export interface BackendRowError {
  /** 1-indexed row number in CSV */
  readonly row_number: number;
  /** Field name where error occurred */
  readonly field: string;
  /** The problematic value */
  readonly value: string | null;
  /** Error description */
  readonly error: string;
}

/**
 * Response from the validate endpoint.
 */
export interface ImportValidationResponse {
  /** List of validation errors */
  readonly errors: BackendRowError[];
  /** Number of rows that passed validation */
  readonly valid_count: number;
  /** Number of rows that failed validation */
  readonly invalid_count: number;
  /** Total number of rows processed */
  readonly total_rows: number;
  /** Sample of valid rows for preview */
  readonly sample_valid_rows: Record<string, unknown>[];
}

/**
 * Response from the execute endpoint.
 */
export interface ImportExecuteResponse {
  /** Whether the import was initiated successfully */
  readonly success: boolean;
  /** Status message */
  readonly message: string;
  /** Optional job ID for async tracking */
  readonly job_id?: string | null;
}

// ============================================================================
// CSV Parsing Types
// ============================================================================

/**
 * Represents a parsed CSV file.
 */
export interface ParsedCSV {
  /** Column headers from the CSV */
  readonly headers: readonly string[];
  /** Data rows (excluding header row) */
  readonly rows: readonly CSVRow[];
  /** Total number of rows (excluding header) */
  readonly totalRows: number;
}

/**
 * A single row of CSV data.
 */
export type CSVRow = readonly string[];

/**
 * Column mapping configuration.
 */
export interface ColumnMapping {
  /** CSV column name/index */
  readonly csvColumn: string;
  /** Target model field name */
  readonly modelField: string | null;
  /** Whether this mapping is required */
  readonly required?: boolean | undefined;
  /** Auto-detected confidence score (0-1) */
  readonly confidence?: number | undefined;
  /** Transformation to apply to values */
  readonly transform?: ColumnTransform | undefined;
  /** Detected type from backend */
  readonly detectedType?: string | undefined;
}

// ============================================================================
// Model Field Types
// ============================================================================

/**
 * Represents a model field that can be mapped to.
 */
export interface ModelField {
  /** Field name/key */
  readonly name: string;
  /** Display label */
  readonly label: string;
  /** Field type for validation */
  readonly type: ModelFieldType;
  /** Whether the field is required */
  readonly required: boolean;
  /** Whether the field is read-only (can't be imported) */
  readonly readOnly?: boolean;
}

/**
 * Supported model field types for validation.
 */
export type ModelFieldType =
  | "string"
  | "number"
  | "integer"
  | "boolean"
  | "date"
  | "datetime"
  | "email"
  | "url"
  | "json"
  | "array";

// ============================================================================
// Validation Types
// ============================================================================

/**
 * Result of validating a single row.
 */
export interface RowValidationResult {
  /** Row index (0-based, from data rows) */
  readonly rowIndex: number;
  /** Whether the row is valid */
  readonly valid: boolean;
  /** Field-level errors */
  readonly errors: readonly FieldValidationError[];
  /** Field-level warnings */
  readonly warnings: readonly FieldValidationWarning[];
}

/**
 * A validation error for a specific field.
 */
export interface FieldValidationError {
  /** Field name */
  readonly field: string;
  /** Error message */
  readonly message: string;
  /** The invalid value */
  readonly value: string;
}

/**
 * A validation warning for a specific field.
 */
export interface FieldValidationWarning {
  /** Field name */
  readonly field: string;
  /** Warning message */
  readonly message: string;
  /** The value that triggered the warning */
  readonly value: string;
}

/**
 * Summary of validation results.
 */
export interface ValidationSummary {
  /** Total number of rows validated */
  readonly totalRows: number;
  /** Number of valid rows */
  readonly validRows: number;
  /** Number of rows with errors */
  readonly errorRows: number;
  /** Number of rows with warnings only */
  readonly warningRows: number;
  /** Per-row validation results */
  readonly results: readonly RowValidationResult[];
}

// ============================================================================
// Import Progress Types
// ============================================================================

/**
 * Current state of the import process.
 */
export type ImportStatus =
  | "idle"
  | "parsing"
  | "validating"
  | "importing"
  | "success"
  | "error"
  | "partial";

/**
 * Progress information during import.
 */
export interface ImportProgress {
  /** Current status */
  readonly status: ImportStatus;
  /** Number of rows processed */
  readonly processed: number;
  /** Total number of rows to process */
  readonly total: number;
  /** Number of successful imports */
  readonly successful: number;
  /** Number of failed imports */
  readonly failed: number;
  /** Current operation description */
  readonly message: string;
}

/**
 * Result of the import operation.
 */
export interface ImportResult {
  /** Whether the overall import succeeded */
  readonly success: boolean;
  /** Total rows in the CSV */
  readonly totalRows: number;
  /** Number of successfully imported rows */
  readonly importedRows: number;
  /** Number of skipped rows (due to errors) */
  readonly skippedRows: number;
  /** Errors that occurred during import */
  readonly errors: readonly ImportError[];
  /** Human-readable summary message */
  readonly message: string;
}

/**
 * An error that occurred during import.
 */
export interface ImportError {
  /** Row index where the error occurred */
  readonly rowIndex: number;
  /** Error message */
  readonly message: string;
  /** The data that failed to import */
  readonly data?: Record<string, unknown>;
}

// ============================================================================
// Wizard Step Types
// ============================================================================

/**
 * Wizard step identifiers.
 */
export type WizardStep = "upload" | "mapping" | "validation" | "import";

/**
 * Configuration for the CSV Import Wizard.
 */
export interface CSVImportConfig {
  /** Model name/identity */
  readonly model: string;
  /** Available model fields for mapping */
  readonly fields: readonly ModelField[];
  /** Maximum file size in bytes (default: 10MB) */
  readonly maxFileSize?: number;
  /** Maximum number of rows to import (default: 10000) */
  readonly maxRows?: number;
  /** Number of preview rows to show (default: 5) */
  readonly previewRows?: number;
  /** Whether to show the column auto-detection */
  readonly showAutoDetection?: boolean;
  /** Custom CSV parsing options */
  readonly parserOptions?: CSVParserOptions;
}

/**
 * Options for CSV parsing.
 */
export interface CSVParserOptions {
  /** Field delimiter (default: comma) */
  readonly delimiter?: string;
  /** Text qualifier/quote character (default: double quote) */
  readonly quoteChar?: string;
  /** Whether the first row is headers (default: true) */
  readonly hasHeaders?: boolean;
  /** Skip empty rows (default: true) */
  readonly skipEmptyRows?: boolean;
  /** Trim whitespace from values (default: true) */
  readonly trimValues?: boolean;
}

// ============================================================================
// Component Props Types
// ============================================================================

/**
 * Props for the CSVImportWizard component.
 */
export interface CSVImportWizardProps {
  /** Model name/identity */
  model: string;
  /** Available model fields for mapping */
  fields: readonly ModelField[];
  /** Whether the wizard is open */
  isOpen: boolean;
  /** Callback when wizard is closed */
  onClose: () => void;
  /** Callback when import is successful */
  onSuccess?: ((result: ImportResult) => void) | undefined;
  /** Maximum file size in bytes */
  maxFileSize?: number | undefined;
  /** Maximum rows to import */
  maxRows?: number | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
}

/**
 * Props for the CSVDropzone component.
 */
export interface CSVDropzoneProps {
  /** Callback when a file is selected */
  onFileSelect: (file: File) => void;
  /** Currently selected file */
  selectedFile: File | null;
  /** Whether the dropzone is disabled */
  disabled?: boolean | undefined;
  /** Error message to display */
  error?: string | undefined;
  /** Maximum file size in bytes */
  maxFileSize?: number | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
}

/**
 * Props for the ColumnMapper component.
 */
export interface ColumnMapperProps {
  /** CSV column headers */
  csvColumns: readonly string[];
  /** Available model fields */
  modelFields: readonly ModelField[];
  /** Current column mappings */
  mappings: readonly ColumnMapping[];
  /** Callback when mappings change */
  onMappingsChange: (mappings: readonly ColumnMapping[]) => void;
  /** Whether to show auto-detection suggestions */
  showAutoDetection?: boolean | undefined;
  /** Column type information from backend */
  columnTypes?: readonly BackendColumnTypeInfo[] | undefined;
  /** Whether to show transform dropdowns */
  showTransforms?: boolean | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
}

/**
 * Props for the ImportPreview component.
 */
export interface ImportPreviewProps {
  /** Parsed CSV data */
  data: ParsedCSV;
  /** Column mappings */
  mappings: readonly ColumnMapping[];
  /** Model fields for display */
  modelFields: readonly ModelField[];
  /** Number of rows to preview */
  previewRows?: number | undefined;
  /** Validation results (optional - local validation) */
  validation?: ValidationSummary | undefined;
  /** Backend validation results */
  backendValidation?: ImportValidationResponse | undefined;
  /** Detected delimiter */
  delimiter?: string | undefined;
  /** Detected encoding */
  encoding?: string | undefined;
  /** Total rows in file */
  totalRows?: number | undefined;
  /** Additional CSS classes */
  className?: string | undefined;
}
