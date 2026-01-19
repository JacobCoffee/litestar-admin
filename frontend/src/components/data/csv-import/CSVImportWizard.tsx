"use client";

import { useState, useCallback, useMemo } from "react";
import { cn } from "@/lib/utils";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CSVDropzone } from "./CSVDropzone";
import { ColumnMapper, autoDetectMappings } from "./ColumnMapper";
import { ImportPreview } from "./ImportPreview";
import type {
  CSVImportWizardProps,
  WizardStep,
  ParsedCSV,
  ColumnMapping,
  ValidationSummary,
  ImportProgress,
  ImportResult,
  RowValidationResult,
  FieldValidationError,
  ModelField,
} from "./types";

// ============================================================================
// Constants
// ============================================================================

const WIZARD_STEPS: { id: WizardStep; label: string; description: string }[] = [
  { id: "upload", label: "Upload", description: "Select CSV file" },
  { id: "mapping", label: "Mapping", description: "Map columns to fields" },
  { id: "validation", label: "Review", description: "Preview and validate" },
  { id: "import", label: "Import", description: "Import data" },
];

const DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const DEFAULT_MAX_ROWS = 10000;
const DEFAULT_PREVIEW_ROWS = 5;

// ============================================================================
// CSV Parsing
// ============================================================================

/**
 * Parses a CSV string into rows and columns.
 * Handles quoted values and escaped quotes.
 */
function parseCSV(text: string, hasHeaders = true): ParsedCSV {
  const lines: string[][] = [];
  let currentLine: string[] = [];
  let currentField = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    const nextChar = text[i + 1];

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          // Escaped quote
          currentField += '"';
          i++;
        } else {
          // End of quoted field
          inQuotes = false;
        }
      } else {
        currentField += char;
      }
    } else {
      if (char === '"') {
        inQuotes = true;
      } else if (char === ",") {
        currentLine.push(currentField.trim());
        currentField = "";
      } else if (char === "\n" || (char === "\r" && nextChar === "\n")) {
        currentLine.push(currentField.trim());
        if (currentLine.some((f) => f !== "")) {
          lines.push(currentLine);
        }
        currentLine = [];
        currentField = "";
        if (char === "\r") i++;
      } else if (char !== "\r") {
        currentField += char;
      }
    }
  }

  // Handle last field/line
  if (currentField || currentLine.length > 0) {
    currentLine.push(currentField.trim());
    if (currentLine.some((f) => f !== "")) {
      lines.push(currentLine);
    }
  }

  if (lines.length === 0) {
    return { headers: [], rows: [], totalRows: 0 };
  }

  const headers = hasHeaders ? lines[0] || [] : lines[0]?.map((_, i) => `Column ${i + 1}`) || [];
  const rows = hasHeaders ? lines.slice(1) : lines;

  return {
    headers,
    rows,
    totalRows: rows.length,
  };
}

/**
 * Reads a file as text.
 */
async function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsText(file);
  });
}

// ============================================================================
// Validation
// ============================================================================

/**
 * Validates data against model field definitions.
 */
function validateData(
  data: ParsedCSV,
  mappings: readonly ColumnMapping[],
  modelFields: readonly ModelField[],
): ValidationSummary {
  const results: RowValidationResult[] = [];

  for (let rowIndex = 0; rowIndex < data.rows.length; rowIndex++) {
    const row = data.rows[rowIndex];
    if (!row) continue;

    const errors: FieldValidationError[] = [];
    const warnings: { field: string; message: string; value: string }[] = [];

    // Check each mapped field
    for (const mapping of mappings) {
      if (!mapping.modelField) continue;

      const field = modelFields.find((f) => f.name === mapping.modelField);
      if (!field) continue;

      const columnIndex = data.headers.indexOf(mapping.csvColumn);
      const value = row[columnIndex] || "";

      // Required field check
      if (field.required && !value) {
        errors.push({
          field: field.name,
          message: `${field.label} is required`,
          value,
        });
        continue;
      }

      // Type validation
      if (value) {
        const typeError = validateFieldType(value, field);
        if (typeError) {
          errors.push({
            field: field.name,
            message: typeError,
            value,
          });
        }
      }
    }

    results.push({
      rowIndex,
      valid: errors.length === 0,
      errors,
      warnings,
    });
  }

  const validRows = results.filter((r) => r.valid && r.warnings.length === 0).length;
  const warningRows = results.filter((r) => r.valid && r.warnings.length > 0).length;
  const errorRows = results.filter((r) => !r.valid).length;

  return {
    totalRows: data.rows.length,
    validRows,
    warningRows,
    errorRows,
    results,
  };
}

/**
 * Validates a value against a field type.
 */
function validateFieldType(value: string, field: ModelField): string | null {
  switch (field.type) {
    case "number":
    case "integer":
      if (isNaN(Number(value))) {
        return `${field.label} must be a valid number`;
      }
      if (field.type === "integer" && !Number.isInteger(Number(value))) {
        return `${field.label} must be an integer`;
      }
      break;

    case "boolean":
      const lower = value.toLowerCase();
      if (!["true", "false", "1", "0", "yes", "no"].includes(lower)) {
        return `${field.label} must be a boolean (true/false, 1/0, yes/no)`;
      }
      break;

    case "email":
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (!emailRegex.test(value)) {
        return `${field.label} must be a valid email address`;
      }
      break;

    case "url":
      try {
        new URL(value);
      } catch {
        return `${field.label} must be a valid URL`;
      }
      break;

    case "date":
    case "datetime":
      const date = new Date(value);
      if (isNaN(date.getTime())) {
        return `${field.label} must be a valid date`;
      }
      break;

    case "json":
      try {
        JSON.parse(value);
      } catch {
        return `${field.label} must be valid JSON`;
      }
      break;
  }

  return null;
}

// ============================================================================
// Icons
// ============================================================================

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20,6 9,17 4,12" />
    </svg>
  );
}

function UploadIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17,8 12,3 7,8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function ArrowLeftIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12,19 5,12 12,5" />
    </svg>
  );
}

function ArrowRightIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="5" y1="12" x2="19" y2="12" />
      <polyline points="12,5 19,12 12,19" />
    </svg>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface StepIndicatorProps {
  steps: typeof WIZARD_STEPS;
  currentStep: WizardStep;
  completedSteps: Set<WizardStep>;
}

function StepIndicator({ steps, currentStep, completedSteps }: StepIndicatorProps) {
  const currentIndex = steps.findIndex((s) => s.id === currentStep);

  return (
    <nav aria-label="Import wizard progress" className="mb-6">
      <ol className="flex items-center justify-between">
        {steps.map((step, index) => {
          const isCompleted = completedSteps.has(step.id);
          const isCurrent = step.id === currentStep;
          const isPast = index < currentIndex;

          return (
            <li key={step.id} className="flex-1 flex items-center">
              <div className="flex flex-col items-center w-full">
                {/* Step circle */}
                <div
                  className={cn(
                    "flex items-center justify-center w-8 h-8 rounded-full",
                    "text-xs font-semibold transition-colors",
                    "border-2",
                    isCompleted
                      ? "bg-[var(--color-success)] border-[var(--color-success)] text-white"
                      : isCurrent
                        ? "bg-[var(--color-primary)] border-[var(--color-primary)] text-white"
                        : isPast
                          ? "bg-[var(--color-card-hover)] border-[var(--color-muted)] text-[var(--color-muted)]"
                          : "bg-[var(--color-card)] border-[var(--color-border)] text-[var(--color-muted)]",
                  )}
                  aria-current={isCurrent ? "step" : undefined}
                >
                  {isCompleted ? (
                    <CheckIcon className="w-4 h-4" />
                  ) : (
                    index + 1
                  )}
                </div>

                {/* Step label */}
                <div className="mt-2 text-center">
                  <p
                    className={cn(
                      "text-xs font-medium",
                      isCurrent
                        ? "text-[var(--color-foreground)]"
                        : "text-[var(--color-muted)]",
                    )}
                  >
                    {step.label}
                  </p>
                  <p className="text-[10px] text-[var(--color-muted)] hidden sm:block">
                    {step.description}
                  </p>
                </div>
              </div>

              {/* Connector line */}
              {index < steps.length - 1 && (
                <div
                  className={cn(
                    "flex-1 h-0.5 mx-2 -mt-6",
                    isPast || isCompleted
                      ? "bg-[var(--color-success)]"
                      : "bg-[var(--color-border)]",
                  )}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

interface ImportProgressDisplayProps {
  progress: ImportProgress;
}

function ImportProgressDisplay({ progress }: ImportProgressDisplayProps) {
  const percentage = progress.total > 0
    ? Math.round((progress.processed / progress.total) * 100)
    : 0;

  return (
    <div className="space-y-4">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--color-foreground)]">{progress.message}</span>
          <span className="text-[var(--color-muted)]">{percentage}%</span>
        </div>
        <div className="h-2 bg-[var(--color-card)] rounded-full overflow-hidden">
          <div
            className={cn(
              "h-full transition-all duration-300",
              progress.status === "error"
                ? "bg-[var(--color-error)]"
                : progress.status === "success"
                  ? "bg-[var(--color-success)]"
                  : "bg-[var(--color-primary)]",
            )}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-center gap-6 text-sm">
        <div className="text-center">
          <p className="text-lg font-semibold text-[var(--color-foreground)]">
            {progress.processed}
          </p>
          <p className="text-xs text-[var(--color-muted)]">Processed</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-[var(--color-success)]">
            {progress.successful}
          </p>
          <p className="text-xs text-[var(--color-muted)]">Successful</p>
        </div>
        <div className="text-center">
          <p className="text-lg font-semibold text-[var(--color-error)]">
            {progress.failed}
          </p>
          <p className="text-xs text-[var(--color-muted)]">Failed</p>
        </div>
      </div>
    </div>
  );
}

interface ImportResultDisplayProps {
  result: ImportResult;
  onClose: () => void;
}

function ImportResultDisplay({ result, onClose }: ImportResultDisplayProps) {
  return (
    <div className="text-center space-y-4">
      {/* Icon */}
      <div
        className={cn(
          "w-16 h-16 mx-auto rounded-full flex items-center justify-center",
          result.success
            ? "bg-[var(--color-success)]/10"
            : "bg-[var(--color-error)]/10",
        )}
      >
        {result.success ? (
          <CheckIcon className="w-8 h-8 text-[var(--color-success)]" />
        ) : (
          <svg
            className="w-8 h-8 text-[var(--color-error)]"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="15" y1="9" x2="9" y2="15" />
            <line x1="9" y1="9" x2="15" y2="15" />
          </svg>
        )}
      </div>

      {/* Message */}
      <div>
        <h3 className="text-lg font-semibold text-[var(--color-foreground)]">
          {result.success ? "Import Complete" : "Import Failed"}
        </h3>
        <p className="text-sm text-[var(--color-muted)] mt-1">
          {result.message}
        </p>
      </div>

      {/* Stats */}
      <div className="flex items-center justify-center gap-8 py-4">
        <div className="text-center">
          <p className="text-2xl font-bold text-[var(--color-success)]">
            {result.importedRows}
          </p>
          <p className="text-xs text-[var(--color-muted)]">Imported</p>
        </div>
        <div className="text-center">
          <p className="text-2xl font-bold text-[var(--color-error)]">
            {result.skippedRows}
          </p>
          <p className="text-xs text-[var(--color-muted)]">Skipped</p>
        </div>
      </div>

      {/* Close button */}
      <Button variant="primary" onClick={onClose}>
        Done
      </Button>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Multi-step CSV Import Wizard.
 *
 * Features:
 * - Step 1: File upload with drag-and-drop
 * - Step 2: Column mapping with auto-detection
 * - Step 3: Data preview with validation
 * - Step 4: Import progress and results
 *
 * @example
 * ```tsx
 * <CSVImportWizard
 *   model="users"
 *   fields={modelFields}
 *   isOpen={isOpen}
 *   onClose={() => setIsOpen(false)}
 *   onSuccess={(result) => {
 *     console.log("Import complete:", result);
 *     refetchData();
 *   }}
 * />
 * ```
 */
export function CSVImportWizard({
  model: _model, // Will be used for API calls in production
  fields,
  isOpen,
  onClose,
  onSuccess,
  maxFileSize = DEFAULT_MAX_FILE_SIZE,
  maxRows = DEFAULT_MAX_ROWS,
  className,
}: CSVImportWizardProps) {
  // Wizard state
  const [currentStep, setCurrentStep] = useState<WizardStep>("upload");
  const [completedSteps, setCompletedSteps] = useState<Set<WizardStep>>(new Set());

  // Data state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [parsedData, setParsedData] = useState<ParsedCSV | null>(null);
  const [mappings, setMappings] = useState<readonly ColumnMapping[]>([]);
  const [validation, setValidation] = useState<ValidationSummary | null>(null);

  // Import state
  const [importProgress, setImportProgress] = useState<ImportProgress>({
    status: "idle",
    processed: 0,
    total: 0,
    successful: 0,
    failed: 0,
    message: "",
  });
  const [importResult, setImportResult] = useState<ImportResult | null>(null);

  // Error state
  const [parseError, setParseError] = useState<string | null>(null);

  // Check if required fields are mapped
  const requiredFieldsMapped = useMemo(() => {
    const requiredFields = fields.filter((f) => f.required && !f.readOnly);
    return requiredFields.every((f) =>
      mappings.some((m) => m.modelField === f.name),
    );
  }, [fields, mappings]);

  // Handle file selection
  const handleFileSelect = useCallback(
    async (file: File | null) => {
      setSelectedFile(file);
      setParsedData(null);
      setMappings([]);
      setValidation(null);
      setParseError(null);

      if (!file) return;

      try {
        const text = await readFileAsText(file);
        const parsed = parseCSV(text);

        if (parsed.totalRows === 0) {
          setParseError("The CSV file appears to be empty");
          return;
        }

        if (parsed.totalRows > maxRows) {
          setParseError(`File exceeds maximum of ${maxRows.toLocaleString()} rows`);
          return;
        }

        setParsedData(parsed);

        // Auto-detect mappings
        const detectedMappings = autoDetectMappings(parsed.headers, fields);
        setMappings(detectedMappings);
      } catch (error) {
        setParseError(
          error instanceof Error ? error.message : "Failed to parse CSV file",
        );
      }
    },
    [fields, maxRows],
  );

  // Navigation handlers
  const handleNext = useCallback(() => {
    const stepIndex = WIZARD_STEPS.findIndex((s) => s.id === currentStep);
    if (stepIndex < WIZARD_STEPS.length - 1) {
      setCompletedSteps((prev) => new Set([...prev, currentStep]));

      const nextStep = WIZARD_STEPS[stepIndex + 1]?.id;
      if (nextStep) {
        setCurrentStep(nextStep);

        // Run validation when entering the validation step
        if (nextStep === "validation" && parsedData) {
          const validationResult = validateData(parsedData, mappings, fields);
          setValidation(validationResult);
        }
      }
    }
  }, [currentStep, fields, mappings, parsedData]);

  const handlePrevious = useCallback(() => {
    const stepIndex = WIZARD_STEPS.findIndex((s) => s.id === currentStep);
    if (stepIndex > 0) {
      const prevStep = WIZARD_STEPS[stepIndex - 1]?.id;
      if (prevStep) {
        setCurrentStep(prevStep);
      }
    }
  }, [currentStep]);

  // Import handler
  const handleImport = useCallback(async () => {
    if (!parsedData || !validation) return;

    setCurrentStep("import");
    setImportProgress({
      status: "importing",
      processed: 0,
      total: validation.validRows,
      successful: 0,
      failed: 0,
      message: "Preparing import...",
    });

    // Simulate import (in production, this would call the API)
    const validRows = validation.results.filter((r) => r.valid);
    let successful = 0;
    let failed = 0;

    for (let i = 0; i < validRows.length; i++) {
      // Simulate API delay
      await new Promise((resolve) => setTimeout(resolve, 50));

      // In production, create record via API here
      // For now, simulate 95% success rate
      if (Math.random() > 0.05) {
        successful++;
      } else {
        failed++;
      }

      setImportProgress({
        status: "importing",
        processed: i + 1,
        total: validRows.length,
        successful,
        failed,
        message: `Importing row ${i + 1} of ${validRows.length}...`,
      });
    }

    const result: ImportResult = {
      success: successful > 0,
      totalRows: parsedData.totalRows,
      importedRows: successful,
      skippedRows: failed + validation.errorRows,
      errors: [],
      message:
        successful > 0
          ? `Successfully imported ${successful} records`
          : "No records were imported",
    };

    setImportProgress({
      status: result.success ? "success" : "error",
      processed: validRows.length,
      total: validRows.length,
      successful,
      failed,
      message: result.message,
    });

    setImportResult(result);
    setCompletedSteps((prev) => new Set([...prev, "import"]));

    if (result.success) {
      onSuccess?.(result);
    }
  }, [parsedData, validation, onSuccess]);

  // Reset wizard
  const handleClose = useCallback(() => {
    // Reset all state
    setCurrentStep("upload");
    setCompletedSteps(new Set());
    setSelectedFile(null);
    setParsedData(null);
    setMappings([]);
    setValidation(null);
    setImportProgress({
      status: "idle",
      processed: 0,
      total: 0,
      successful: 0,
      failed: 0,
      message: "",
    });
    setImportResult(null);
    setParseError(null);

    onClose();
  }, [onClose]);

  // Determine if next button should be enabled
  const canProceed = useMemo(() => {
    switch (currentStep) {
      case "upload":
        return parsedData !== null && !parseError;
      case "mapping":
        return requiredFieldsMapped;
      case "validation":
        return validation !== null && validation.validRows > 0;
      case "import":
        return importResult !== null;
      default:
        return false;
    }
  }, [currentStep, parsedData, parseError, requiredFieldsMapped, validation, importResult]);

  const isImporting = importProgress.status === "importing";

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      closeOnOverlayClick={!isImporting}
      closeOnEscape={!isImporting}
      className={cn("max-w-2xl", className)}
    >
      {isImporting ? (
        <ModalHeader>Import CSV</ModalHeader>
      ) : (
        <ModalHeader onClose={handleClose}>Import CSV</ModalHeader>
      )}

      <ModalBody className="space-y-4">
        {/* Step indicator */}
        <StepIndicator
          steps={WIZARD_STEPS}
          currentStep={currentStep}
          completedSteps={completedSteps}
        />

        {/* Step content */}
        {currentStep === "upload" && (
          <div className="space-y-4">
            <CSVDropzone
              onFileSelect={handleFileSelect}
              selectedFile={selectedFile}
              maxFileSize={maxFileSize}
              error={parseError || undefined}
              disabled={isImporting}
            />
            {parsedData && (
              <div className="p-3 rounded-[var(--radius-md)] bg-[var(--color-success)]/10 border border-[var(--color-success)]/20">
                <p className="text-sm text-[var(--color-success)]">
                  <CheckIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
                  File parsed successfully: {parsedData.headers.length} columns,{" "}
                  {parsedData.totalRows.toLocaleString()} rows
                </p>
              </div>
            )}
          </div>
        )}

        {currentStep === "mapping" && parsedData && (
          <ColumnMapper
            csvColumns={parsedData.headers}
            modelFields={fields}
            mappings={mappings}
            onMappingsChange={setMappings}
            showAutoDetection
          />
        )}

        {currentStep === "validation" && parsedData && (
          <ImportPreview
            data={parsedData}
            mappings={mappings}
            modelFields={fields}
            validation={validation || undefined}
            previewRows={DEFAULT_PREVIEW_ROWS}
          />
        )}

        {currentStep === "import" && (
          <div className="py-8">
            {importResult ? (
              <ImportResultDisplay result={importResult} onClose={handleClose} />
            ) : (
              <ImportProgressDisplay progress={importProgress} />
            )}
          </div>
        )}
      </ModalBody>

      {!importResult && (
        <ModalFooter>
          {currentStep !== "upload" && (
            <Button
              variant="secondary"
              onClick={handlePrevious}
              disabled={isImporting}
              leftIcon={<ArrowLeftIcon className="w-4 h-4" />}
            >
              Back
            </Button>
          )}

          <div className="flex-1" />

          <Button variant="secondary" onClick={handleClose} disabled={isImporting}>
            Cancel
          </Button>

          {currentStep === "validation" ? (
            <Button
              variant="primary"
              onClick={handleImport}
              disabled={!canProceed || isImporting}
              loading={isImporting}
              leftIcon={!isImporting ? <UploadIcon className="w-4 h-4" /> : undefined}
            >
              {validation
                ? `Import ${validation.validRows.toLocaleString()} Row${validation.validRows !== 1 ? "s" : ""}`
                : "Import"}
            </Button>
          ) : currentStep !== "import" ? (
            <Button
              variant="primary"
              onClick={handleNext}
              disabled={!canProceed}
              rightIcon={<ArrowRightIcon className="w-4 h-4" />}
            >
              Next
            </Button>
          ) : null}
        </ModalFooter>
      )}
    </Modal>
  );
}

CSVImportWizard.displayName = "CSVImportWizard";
