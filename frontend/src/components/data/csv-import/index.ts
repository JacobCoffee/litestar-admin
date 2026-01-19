/**
 * CSV Import Wizard Components
 *
 * A multi-step wizard for importing CSV data into models.
 *
 * @example
 * ```tsx
 * import { CSVImportWizard, CSVImportButton } from '@/components/data/csv-import';
 *
 * // Using the wizard directly
 * <CSVImportWizard
 *   model="users"
 *   fields={modelFields}
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSuccess={(result) => refetchData()}
 * />
 *
 * // Using the button with integrated wizard
 * <CSVImportButton
 *   model="users"
 *   fields={modelFields}
 *   onSuccess={(result) => refetchData()}
 * />
 * ```
 */

export { CSVImportWizard } from "./CSVImportWizard";
export { CSVImportButton } from "./CSVImportButton";
export { CSVDropzone } from "./CSVDropzone";
export { ColumnMapper, autoDetectMappings } from "./ColumnMapper";
export { ImportPreview } from "./ImportPreview";

export type {
  // Core types
  ParsedCSV,
  CSVRow,
  ColumnMapping,
  ModelField,
  ModelFieldType,
  // Validation types
  RowValidationResult,
  FieldValidationError,
  FieldValidationWarning,
  ValidationSummary,
  // Import types
  ImportStatus,
  ImportProgress,
  ImportResult,
  ImportError,
  // Config types
  WizardStep,
  CSVImportConfig,
  CSVParserOptions,
  // Component props
  CSVImportWizardProps,
  CSVDropzoneProps,
  ColumnMapperProps,
  ImportPreviewProps,
} from "./types";

export type { CSVImportButtonProps } from "./CSVImportButton";
