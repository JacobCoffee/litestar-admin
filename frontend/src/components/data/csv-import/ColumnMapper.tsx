"use client";

import { useCallback, useMemo, useId } from "react";
import { cn } from "@/lib/utils";
import type {
  ColumnMapperProps,
  ColumnMapping,
  ModelField,
  ColumnTransform,
  BackendColumnTypeInfo,
} from "./types";

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calculates similarity between two strings using Levenshtein distance.
 * Returns a score from 0 to 1 (1 being exact match).
 */
function calculateSimilarity(str1: string, str2: string): number {
  const s1 = str1.toLowerCase().replace(/[_-]/g, " ").trim();
  const s2 = str2.toLowerCase().replace(/[_-]/g, " ").trim();

  if (s1 === s2) return 1;
  if (s1.length === 0 || s2.length === 0) return 0;

  // Check if one contains the other
  if (s1.includes(s2) || s2.includes(s1)) {
    return 0.8;
  }

  // Simple word overlap check
  const words1 = s1.split(/\s+/);
  const words2 = s2.split(/\s+/);
  const commonWords = words1.filter((w) => words2.includes(w));
  if (commonWords.length > 0) {
    return 0.6 + (commonWords.length / Math.max(words1.length, words2.length)) * 0.3;
  }

  // Levenshtein distance
  const matrix: number[][] = [];

  for (let i = 0; i <= s1.length; i++) {
    matrix[i] = [i];
  }
  for (let j = 0; j <= s2.length; j++) {
    matrix[0]![j] = j;
  }

  for (let i = 1; i <= s1.length; i++) {
    for (let j = 1; j <= s2.length; j++) {
      const cost = s1[i - 1] === s2[j - 1] ? 0 : 1;
      matrix[i]![j] = Math.min(
        matrix[i - 1]![j]! + 1,
        matrix[i]![j - 1]! + 1,
        matrix[i - 1]![j - 1]! + cost,
      );
    }
  }

  const maxLen = Math.max(s1.length, s2.length);
  return 1 - matrix[s1.length]![s2.length]! / maxLen;
}

/**
 * Auto-detects column mappings based on name similarity.
 */
export function autoDetectMappings(
  csvColumns: readonly string[],
  modelFields: readonly ModelField[],
): ColumnMapping[] {
  const mappings: ColumnMapping[] = [];
  const usedFields = new Set<string>();

  for (const csvColumn of csvColumns) {
    let bestMatch: { field: string | null; confidence: number } = {
      field: null,
      confidence: 0,
    };

    for (const field of modelFields) {
      if (field.readOnly || usedFields.has(field.name)) continue;

      // Check similarity with field name
      const nameScore = calculateSimilarity(csvColumn, field.name);
      // Check similarity with field label
      const labelScore = calculateSimilarity(csvColumn, field.label);
      const score = Math.max(nameScore, labelScore);

      if (score > bestMatch.confidence && score >= 0.5) {
        bestMatch = { field: field.name, confidence: score };
      }
    }

    if (bestMatch.field) {
      usedFields.add(bestMatch.field);
    }

    mappings.push({
      csvColumn,
      modelField: bestMatch.field,
      confidence: bestMatch.confidence,
    });
  }

  return mappings;
}

// ============================================================================
// Icons
// ============================================================================

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

function AlertIcon({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  );
}

function SparkleIcon({ className }: { className?: string }) {
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
      <path d="M12 3l1.5 5.5L19 10l-5.5 1.5L12 17l-1.5-5.5L5 10l5.5-1.5L12 3z" />
    </svg>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

/** Available transform options */
const TRANSFORM_OPTIONS: { value: ColumnTransform; label: string }[] = [
  { value: "none", label: "None" },
  { value: "trim", label: "Trim whitespace" },
  { value: "lowercase", label: "Lowercase" },
  { value: "uppercase", label: "Uppercase" },
];

interface MappingRowProps {
  mapping: ColumnMapping;
  modelFields: readonly ModelField[];
  usedFields: Set<string>;
  onMappingChange: (csvColumn: string, modelField: string | null, transform?: ColumnTransform) => void;
  index: number;
  showAutoDetection?: boolean | undefined;
  columnTypeInfo?: BackendColumnTypeInfo | undefined;
  showTransforms?: boolean | undefined;
}

/** Get type compatibility between CSV detected type and model field type */
function getTypeCompatibility(
  csvType: string | undefined,
  modelType: string | undefined,
): "compatible" | "convertible" | "incompatible" | "unknown" {
  if (!csvType || !modelType) return "unknown";

  // Normalize types
  const csv = csvType.toLowerCase();
  const model = modelType.toLowerCase();

  // Direct matches
  if (csv === model) return "compatible";

  // String is compatible with most types
  if (csv === "string") return "convertible";

  // Integer to number is compatible
  if (csv === "integer" && model === "number") return "compatible";

  // Float/number to integer needs checking
  if (csv === "float" && model === "integer") return "convertible";

  // Date/datetime conversions
  if ((csv === "date" || csv === "datetime") && (model === "string")) return "convertible";

  // Boolean conversions
  if (csv === "boolean" && model === "string") return "convertible";

  return "incompatible";
}

function MappingRow({
  mapping,
  modelFields,
  usedFields,
  onMappingChange,
  index,
  showAutoDetection = true,
  columnTypeInfo,
  showTransforms = true,
}: MappingRowProps) {
  const selectId = useId();
  const transformId = useId();
  const isMapped = mapping.modelField !== null;
  const isAutoDetected = showAutoDetection && mapping.confidence && mapping.confidence >= 0.5;

  // Find if the mapped field is required
  const mappedField = modelFields.find((f) => f.name === mapping.modelField);
  const isRequired = mappedField?.required ?? false;

  // Get type compatibility
  const detectedType = columnTypeInfo?.detected_type || mapping.detectedType;
  const typeCompatibility = getTypeCompatibility(detectedType, mappedField?.type);

  // Available fields for this mapping (not used by other mappings, or current selection)
  const availableFields = modelFields.filter(
    (f) => !f.readOnly && (!usedFields.has(f.name) || f.name === mapping.modelField),
  );

  return (
    <div
      className={cn(
        "flex flex-col gap-2 p-3 rounded-[var(--radius-md)]",
        "bg-[var(--color-card)] border border-[var(--color-border)]",
        "transition-colors duration-150",
        isMapped && "border-[var(--color-success)]/30 bg-[var(--color-success)]/5",
      )}
    >
      <div className="flex items-center gap-3">
        {/* Row number */}
        <span className="flex-shrink-0 w-6 text-xs text-[var(--color-muted)] text-center">
          {index + 1}
        </span>

        {/* CSV Column */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--color-foreground)] truncate">
              {mapping.csvColumn}
            </span>
            {isAutoDetected && (
              <span
                className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-[var(--color-accent)]/10 text-[var(--color-accent)]"
                title={`Auto-detected with ${Math.round((mapping.confidence || 0) * 100)}% confidence`}
              >
                <SparkleIcon className="w-3 h-3" />
                Auto
              </span>
            )}
          </div>
          {/* Detected type badge */}
          {detectedType && (
            <span className="text-[10px] text-[var(--color-muted)]">
              Detected: {detectedType}
              {columnTypeInfo?.nullable && " (nullable)"}
            </span>
          )}
        </div>

        {/* Arrow */}
        <ArrowRightIcon className="flex-shrink-0 w-4 h-4 text-[var(--color-muted)]" />

        {/* Model Field Select */}
        <div className="flex-1 min-w-0">
          <select
            id={selectId}
            value={mapping.modelField || ""}
            onChange={(e) =>
              onMappingChange(mapping.csvColumn, e.target.value || null, mapping.transform)
            }
            className={cn(
              "w-full h-9 px-3 pr-8 text-sm rounded-[var(--radius-md)]",
              "bg-[var(--color-background)] text-[var(--color-foreground)]",
              "border border-[var(--color-border)]",
              "appearance-none bg-no-repeat bg-right",
              "bg-[length:1.25rem_1.25rem] bg-[right_0.5rem_center]",
              '[background-image:url("data:image/svg+xml,%3csvg%20xmlns%3d%27http%3a%2f%2fwww.w3.org%2f2000%2fsvg%27%20fill%3d%27none%27%20viewBox%3d%270%200%2024%2024%27%20stroke%3d%27%238b949e%27%20stroke-width%3d%272%27%3e%3cpath%20d%3d%27M7%2010l5%205%205-5%27%2f%3e%3c%2fsvg%3e")]',
              "transition-colors duration-150",
              "hover:border-[var(--color-muted)]",
              "focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]",
              "focus:outline-none",
            )}
            aria-label={`Map CSV column "${mapping.csvColumn}" to model field`}
          >
            <option value="">-- Skip this column --</option>
            {availableFields.map((field) => (
              <option key={field.name} value={field.name}>
                {field.label}
                {field.required ? " *" : ""}
              </option>
            ))}
          </select>
          {/* Model field type indicator */}
          {mappedField && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-[10px] text-[var(--color-muted)]">
                Type: {mappedField.type}
              </span>
              {typeCompatibility !== "unknown" && (
                <span
                  className={cn(
                    "text-[10px] px-1 py-0.5 rounded",
                    typeCompatibility === "compatible" &&
                      "bg-[var(--color-success)]/10 text-[var(--color-success)]",
                    typeCompatibility === "convertible" &&
                      "bg-[var(--color-warning)]/10 text-[var(--color-warning)]",
                    typeCompatibility === "incompatible" &&
                      "bg-[var(--color-error)]/10 text-[var(--color-error)]",
                  )}
                >
                  {typeCompatibility}
                </span>
              )}
            </div>
          )}
        </div>

        {/* Status indicator */}
        <div className="flex-shrink-0 w-6">
          {isMapped ? (
            <CheckIcon className="w-4 h-4 text-[var(--color-success)]" />
          ) : isRequired ? (
            <AlertIcon className="w-4 h-4 text-[var(--color-warning)]" />
          ) : null}
        </div>
      </div>

      {/* Transform dropdown (only shown when mapped and transforms enabled) */}
      {isMapped && showTransforms && (
        <div className="flex items-center gap-2 ml-9">
          <label
            htmlFor={transformId}
            className="text-xs text-[var(--color-muted)] whitespace-nowrap"
          >
            Transform:
          </label>
          <select
            id={transformId}
            value={mapping.transform || "none"}
            onChange={(e) =>
              onMappingChange(
                mapping.csvColumn,
                mapping.modelField,
                e.target.value as ColumnTransform,
              )
            }
            className={cn(
              "h-7 px-2 pr-6 text-xs rounded-[var(--radius-md)]",
              "bg-[var(--color-background)] text-[var(--color-foreground)]",
              "border border-[var(--color-border)]",
              "appearance-none bg-no-repeat bg-right",
              "bg-[length:1rem_1rem] bg-[right_0.25rem_center]",
              '[background-image:url("data:image/svg+xml,%3csvg%20xmlns%3d%27http%3a%2f%2fwww.w3.org%2f2000%2fsvg%27%20fill%3d%27none%27%20viewBox%3d%270%200%2024%2024%27%20stroke%3d%27%238b949e%27%20stroke-width%3d%272%27%3e%3cpath%20d%3d%27M7%2010l5%205%205-5%27%2f%3e%3c%2fsvg%3e")]',
              "transition-colors duration-150",
              "hover:border-[var(--color-muted)]",
              "focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]",
              "focus:outline-none",
            )}
            aria-label={`Transform for "${mapping.csvColumn}"`}
          >
            {TRANSFORM_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          {/* Sample values preview */}
          {columnTypeInfo?.sample_values && columnTypeInfo.sample_values.length > 0 && (
            <span
              className="text-[10px] text-[var(--color-muted)] truncate max-w-[150px]"
              title={columnTypeInfo.sample_values.join(", ")}
            >
              Sample: {columnTypeInfo.sample_values.slice(0, 2).join(", ")}
              {columnTypeInfo.sample_values.length > 2 && "..."}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Column mapping interface for mapping CSV columns to model fields.
 *
 * Features:
 * - Dropdown selection for each CSV column
 * - Auto-detection of mappings based on column name similarity
 * - Visual indicators for mapped/unmapped columns
 * - Required field indicators
 * - Prevents duplicate mappings
 *
 * @example
 * ```tsx
 * <ColumnMapper
 *   csvColumns={["name", "email", "age"]}
 *   modelFields={[
 *     { name: "full_name", label: "Full Name", type: "string", required: true },
 *     { name: "email", label: "Email", type: "email", required: true },
 *     { name: "age", label: "Age", type: "integer", required: false },
 *   ]}
 *   mappings={mappings}
 *   onMappingsChange={setMappings}
 * />
 * ```
 */
export function ColumnMapper({
  csvColumns,
  modelFields,
  mappings,
  onMappingsChange,
  showAutoDetection = true,
  columnTypes,
  showTransforms = true,
  className,
}: ColumnMapperProps) {
  // Build column type lookup map
  const columnTypeMap = useMemo(() => {
    const map = new Map<string, BackendColumnTypeInfo>();
    if (columnTypes) {
      for (const ct of columnTypes) {
        map.set(ct.csv_column, ct);
      }
    }
    return map;
  }, [columnTypes]);
  // Calculate which fields are currently used
  const usedFields = useMemo(() => {
    const used = new Set<string>();
    for (const mapping of mappings) {
      if (mapping.modelField) {
        used.add(mapping.modelField);
      }
    }
    return used;
  }, [mappings]);

  // Count mapped and required fields
  const stats = useMemo(() => {
    const mappedCount = mappings.filter((m) => m.modelField !== null).length;
    const requiredFields = modelFields.filter((f) => f.required && !f.readOnly);
    const mappedRequiredCount = requiredFields.filter((f) =>
      mappings.some((m) => m.modelField === f.name),
    ).length;

    return {
      total: csvColumns.length,
      mapped: mappedCount,
      required: requiredFields.length,
      mappedRequired: mappedRequiredCount,
    };
  }, [csvColumns.length, mappings, modelFields]);

  // Handle mapping change
  const handleMappingChange = useCallback(
    (csvColumn: string, modelField: string | null, transform?: ColumnTransform) => {
      const newMappings = mappings.map((m) =>
        m.csvColumn === csvColumn
          ? {
              ...m,
              modelField,
              confidence: modelField ? 1 : 0,
              transform: transform || m.transform || "none",
            }
          : m,
      );
      onMappingsChange(newMappings);
    },
    [mappings, onMappingsChange],
  );

  // Auto-detect all mappings
  const handleAutoDetect = useCallback(() => {
    const detected = autoDetectMappings(csvColumns, modelFields);
    onMappingsChange(detected);
  }, [csvColumns, modelFields, onMappingsChange]);

  // Clear all mappings
  const handleClearAll = useCallback(() => {
    const cleared = mappings.map((m) => ({
      ...m,
      modelField: null,
      confidence: 0,
    }));
    onMappingsChange(cleared);
  }, [mappings, onMappingsChange]);

  const allRequiredMapped = stats.mappedRequired === stats.required;

  return (
    <div className={cn("space-y-4", className)}>
      {/* Header with stats and actions */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <h3 className="text-sm font-medium text-[var(--color-foreground)]">
            Column Mapping
          </h3>
          <p className="text-xs text-[var(--color-muted)]">
            {stats.mapped} of {stats.total} columns mapped
            {stats.required > 0 && (
              <span
                className={cn(
                  "ml-2",
                  allRequiredMapped ? "text-[var(--color-success)]" : "text-[var(--color-warning)]",
                )}
              >
                ({stats.mappedRequired}/{stats.required} required)
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {showAutoDetection && (
            <button
              type="button"
              onClick={handleAutoDetect}
              className={cn(
                "inline-flex items-center gap-1.5 px-3 py-1.5",
                "text-xs font-medium text-[var(--color-accent)]",
                "rounded-[var(--radius-md)] border border-[var(--color-accent)]/30",
                "bg-[var(--color-accent)]/5",
                "hover:bg-[var(--color-accent)]/10 hover:border-[var(--color-accent)]/50",
                "transition-colors duration-150",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
              )}
            >
              <SparkleIcon className="w-3.5 h-3.5" />
              Auto-detect
            </button>
          )}
          <button
            type="button"
            onClick={handleClearAll}
            disabled={stats.mapped === 0}
            className={cn(
              "text-xs text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
              "disabled:opacity-50 disabled:cursor-not-allowed",
              "transition-colors duration-150",
            )}
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Mapping list */}
      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {mappings.map((mapping, index) => (
          <MappingRow
            key={mapping.csvColumn}
            mapping={mapping}
            modelFields={modelFields}
            usedFields={usedFields}
            onMappingChange={handleMappingChange}
            index={index}
            showAutoDetection={showAutoDetection}
            columnTypeInfo={columnTypeMap.get(mapping.csvColumn)}
            showTransforms={showTransforms}
          />
        ))}
      </div>

      {/* Required fields warning */}
      {!allRequiredMapped && (
        <div
          className={cn(
            "flex items-start gap-2 p-3 rounded-[var(--radius-md)]",
            "bg-[var(--color-warning)]/10 text-[var(--color-warning)]",
            "text-xs",
          )}
          role="alert"
        >
          <AlertIcon className="w-4 h-4 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Required fields not mapped</p>
            <p className="mt-0.5 text-[var(--color-muted)]">
              The following required fields need to be mapped:{" "}
              {modelFields
                .filter(
                  (f) =>
                    f.required &&
                    !f.readOnly &&
                    !mappings.some((m) => m.modelField === f.name),
                )
                .map((f) => f.label)
                .join(", ")}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

ColumnMapper.displayName = "ColumnMapper";
