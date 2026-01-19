"use client";

import {
  useState,
  useCallback,
  useMemo,
  type FormEvent,
  type ChangeEvent,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";
import {
  Input,
  Select,
  Checkbox,
  TextArea,
  FormField,
  type SelectOption,
} from "@/components/ui/Form";
import { Button } from "@/components/ui/Button";
import type { ModelSchema, SchemaProperty } from "@/types";

// ============================================================================
// Types
// ============================================================================

export type FormMode = "create" | "edit" | "view";

export interface RecordFormProps<T = Record<string, unknown>> {
  /** JSON Schema describing the model structure */
  schema: ModelSchema;
  /** Initial values for form fields */
  initialValues?: Partial<T>;
  /** Callback when form is submitted */
  onSubmit: (values: T) => void | Promise<void>;
  /** Callback when cancel button is clicked */
  onCancel?: () => void;
  /** Whether form submission is in progress */
  isSubmitting?: boolean;
  /** Form mode: create, edit, or view (read-only) */
  mode?: FormMode;
  /** Server-side validation errors keyed by field name */
  errors?: Record<string, string>;
  /** Additional CSS classes */
  className?: string;
  /** Related records for relationship fields */
  relatedRecords?: Record<string, RelatedRecord[]>;
  /** Custom field renderer for overriding default field rendering */
  renderField?: (field: FieldConfig, defaultRender: () => ReactNode) => ReactNode;
}

export interface RelatedRecord {
  id: string | number;
  label: string;
}

export interface FieldConfig {
  name: string;
  property: SchemaProperty;
  required: boolean;
  value: unknown;
  error: string | undefined;
  disabled: boolean;
}

interface ValidationResult {
  valid: boolean;
  errors: Record<string, string>;
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Determines the input type based on schema property.
 */
function getInputType(property: SchemaProperty): string {
  const { type, format } = property;

  if (type === "boolean") return "checkbox";
  if (type === "integer" || type === "number") return "number";

  if (type === "string") {
    switch (format) {
      case "email":
        return "email";
      case "uri":
      case "url":
        return "url";
      case "date":
        return "date";
      case "date-time":
        return "datetime-local";
      case "time":
        return "time";
      case "password":
        return "password";
      case "textarea":
        return "textarea";
      default:
        return "text";
    }
  }

  return "text";
}

/**
 * Converts enum values to select options.
 */
function enumToOptions(enumValues: readonly unknown[]): SelectOption[] {
  return enumValues.map((value) => ({
    value: String(value),
    label: formatLabel(String(value)),
  }));
}

/**
 * Formats a field name or enum value as a human-readable label.
 */
function formatLabel(str: string): string {
  return str
    .replace(/_/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

/**
 * Coerces a value to the appropriate type based on schema.
 */
function coerceValue(value: unknown, property: SchemaProperty): unknown {
  const { type } = property;

  if (value === "" || value === undefined || value === null) {
    return property.default ?? null;
  }

  switch (type) {
    case "integer":
      return Number.isNaN(Number(value)) ? null : Math.floor(Number(value));
    case "number":
      return Number.isNaN(Number(value)) ? null : Number(value);
    case "boolean":
      return Boolean(value);
    default:
      return value;
  }
}

/**
 * Gets the initial form values from schema defaults and provided initial values.
 */
function getInitialFormValues(
  schema: ModelSchema,
  initialValues?: Record<string, unknown>,
): Record<string, unknown> {
  const values: Record<string, unknown> = {};

  for (const [name, property] of Object.entries(schema.properties)) {
    if (initialValues?.[name] !== undefined) {
      values[name] = initialValues[name];
    } else if (property.default !== undefined) {
      values[name] = property.default;
    } else if (property.type === "boolean") {
      values[name] = false;
    } else {
      values[name] = "";
    }
  }

  return values;
}

/**
 * Validates form values against the schema.
 */
function validateForm(values: Record<string, unknown>, schema: ModelSchema): ValidationResult {
  const errors: Record<string, string> = {};

  for (const [name, property] of Object.entries(schema.properties)) {
    const value = values[name];
    const isRequired = schema.required.includes(name);

    // Skip read-only fields
    if (property.readOnly) continue;

    // Required validation
    if (isRequired && (value === null || value === undefined || value === "")) {
      errors[name] = `${property.title || formatLabel(name)} is required`;
      continue;
    }

    // Skip further validation if value is empty and not required
    if (value === null || value === undefined || value === "") continue;

    // String validations
    if (property.type === "string" && typeof value === "string") {
      if (property.minLength !== undefined && value.length < property.minLength) {
        errors[name] = `Minimum length is ${property.minLength} characters`;
      }
      if (property.maxLength !== undefined && value.length > property.maxLength) {
        errors[name] = `Maximum length is ${property.maxLength} characters`;
      }
      if (property.pattern) {
        const regex = new RegExp(property.pattern);
        if (!regex.test(value)) {
          errors[name] = `Invalid format`;
        }
      }
      // Email format validation
      if (property.format === "email") {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        if (!emailRegex.test(value)) {
          errors[name] = "Invalid email address";
        }
      }
      // URL format validation
      if (property.format === "uri" || property.format === "url") {
        try {
          new URL(value);
        } catch {
          errors[name] = "Invalid URL";
        }
      }
    }

    // Number validations
    if ((property.type === "integer" || property.type === "number") && typeof value === "number") {
      if (property.minimum !== undefined && value < property.minimum) {
        errors[name] = `Minimum value is ${property.minimum}`;
      }
      if (property.maximum !== undefined && value > property.maximum) {
        errors[name] = `Maximum value is ${property.maximum}`;
      }
    }
  }

  return {
    valid: Object.keys(errors).length === 0,
    errors,
  };
}

/**
 * Formats a value for display in view mode.
 */
function formatDisplayValue(value: unknown, property: SchemaProperty): string {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (property.type === "boolean") {
    return value ? "Yes" : "No";
  }

  if (property.format === "date" && typeof value === "string") {
    return new Date(value).toLocaleDateString();
  }

  if (property.format === "date-time" && typeof value === "string") {
    return new Date(value).toLocaleString();
  }

  if (Array.isArray(value)) {
    return value.join(", ");
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

// ============================================================================
// Field Components
// ============================================================================

interface FieldRendererProps {
  config: FieldConfig;
  onChange: (name: string, value: unknown) => void;
  relatedRecords: RelatedRecord[] | undefined;
  mode: FormMode;
}

function FieldRenderer({ config, onChange, relatedRecords, mode }: FieldRendererProps) {
  const { name, property, required, value, error, disabled } = config;
  const inputType = getInputType(property);
  const label = property.title || formatLabel(name);
  const hint = property.description;
  const isViewMode = mode === "view";
  const fieldId = `field-${name}`;

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
      const target = e.target;
      let newValue: unknown;

      if (target instanceof HTMLInputElement && target.type === "checkbox") {
        newValue = target.checked;
      } else if (target instanceof HTMLInputElement && target.type === "number") {
        newValue = target.value === "" ? "" : Number(target.value);
      } else {
        newValue = target.value;
      }

      onChange(name, newValue);
    },
    [name, onChange],
  );

  // Build aria-describedby attribute
  const getAriaDescribedBy = (hasError: boolean, hasHint: boolean): string | undefined => {
    if (hasError) return `${fieldId}-error`;
    if (hasHint) return `${fieldId}-hint`;
    return undefined;
  };

  // View mode: display value only
  if (isViewMode) {
    return (
      <FormField label={label} htmlFor={fieldId} className="col-span-1">
        <div
          className={cn(
            "min-h-[40px] px-3 py-2 rounded-[var(--radius-md)]",
            "bg-[var(--color-card-hover)] text-[var(--color-foreground)]",
            "border border-[var(--color-border)]",
          )}
        >
          {formatDisplayValue(value, property)}
        </div>
      </FormField>
    );
  }

  // Read-only field (not view mode)
  if (property.readOnly) {
    return (
      <FormField label={label} htmlFor={fieldId} {...(hint ? { hint } : {})} className="col-span-1">
        <Input
          id={fieldId}
          value={String(value ?? "")}
          disabled
          aria-describedby={getAriaDescribedBy(false, !!hint)}
        />
      </FormField>
    );
  }

  // Enum field -> Select
  if (property.enum && property.enum.length > 0) {
    const options = enumToOptions(property.enum);
    return (
      <FormField
        label={label}
        htmlFor={fieldId}
        required={required}
        {...(error ? { error } : {})}
        {...(hint ? { hint } : {})}
        className="col-span-1"
      >
        <Select
          id={fieldId}
          options={options}
          value={String(value ?? "")}
          onChange={handleChange}
          disabled={disabled}
          error={!!error}
          placeholder={`Select ${label.toLowerCase()}`}
          aria-describedby={getAriaDescribedBy(!!error, !!hint)}
        />
      </FormField>
    );
  }

  // Relationship field with related records
  if (relatedRecords && relatedRecords.length > 0) {
    const options: SelectOption[] = relatedRecords.map((record) => ({
      value: String(record.id),
      label: record.label,
    }));
    return (
      <FormField
        label={label}
        htmlFor={fieldId}
        required={required}
        {...(error ? { error } : {})}
        {...(hint ? { hint } : {})}
        className="col-span-1"
      >
        <Select
          id={fieldId}
          options={options}
          value={String(value ?? "")}
          onChange={handleChange}
          disabled={disabled}
          error={!!error}
          placeholder={`Select ${label.toLowerCase()}`}
          aria-describedby={getAriaDescribedBy(!!error, !!hint)}
        />
      </FormField>
    );
  }

  // Boolean -> Checkbox
  if (inputType === "checkbox") {
    return (
      <FormField
        htmlFor={fieldId}
        {...(error ? { error } : {})}
        {...(hint ? { hint } : {})}
        className="col-span-1 flex items-end"
      >
        <Checkbox
          id={fieldId}
          checked={Boolean(value)}
          onChange={handleChange}
          disabled={disabled}
          error={!!error}
          label={label}
          aria-describedby={getAriaDescribedBy(!!error, !!hint)}
        />
      </FormField>
    );
  }

  // Textarea
  if (inputType === "textarea") {
    return (
      <FormField
        label={label}
        htmlFor={fieldId}
        required={required}
        {...(error ? { error } : {})}
        {...(hint ? { hint } : {})}
        className="col-span-full"
      >
        <TextArea
          id={fieldId}
          value={String(value ?? "")}
          onChange={handleChange}
          disabled={disabled}
          error={!!error}
          placeholder={property.description || `Enter ${label.toLowerCase()}`}
          minLength={property.minLength}
          maxLength={property.maxLength}
          aria-describedby={getAriaDescribedBy(!!error, !!hint)}
        />
      </FormField>
    );
  }

  // Number input
  if (inputType === "number") {
    return (
      <FormField
        label={label}
        htmlFor={fieldId}
        required={required}
        {...(error ? { error } : {})}
        {...(hint ? { hint } : {})}
        className="col-span-1"
      >
        <Input
          id={fieldId}
          type="number"
          value={value === null || value === undefined ? "" : String(value)}
          onChange={handleChange}
          disabled={disabled}
          error={!!error}
          min={property.minimum}
          max={property.maximum}
          step={property.type === "integer" ? 1 : "any"}
          placeholder={property.description || `Enter ${label.toLowerCase()}`}
          aria-describedby={getAriaDescribedBy(!!error, !!hint)}
        />
      </FormField>
    );
  }

  // Default: text-like inputs (text, email, url, date, datetime-local, time, password)
  return (
    <FormField
      label={label}
      htmlFor={fieldId}
      required={required}
      {...(error ? { error } : {})}
      {...(hint ? { hint } : {})}
      className="col-span-1"
    >
      <Input
        id={fieldId}
        type={inputType}
        value={String(value ?? "")}
        onChange={handleChange}
        disabled={disabled}
        error={!!error}
        minLength={property.minLength}
        maxLength={property.maxLength}
        pattern={property.pattern}
        placeholder={property.description || `Enter ${label.toLowerCase()}`}
        aria-describedby={getAriaDescribedBy(!!error, !!hint)}
      />
    </FormField>
  );
}

// ============================================================================
// Main Component
// ============================================================================

/**
 * Dynamic form component that generates fields from a JSON Schema.
 *
 * Features:
 * - Automatic field type detection based on schema
 * - Client-side validation with error display
 * - Support for create, edit, and view modes
 * - Relationship field handling with selects
 * - Accessible with proper ARIA attributes
 *
 * @example
 * ```tsx
 * <RecordForm
 *   schema={userSchema}
 *   initialValues={{ name: 'John' }}
 *   onSubmit={(values) => createUser(values)}
 *   mode="create"
 * />
 * ```
 */
export function RecordForm<T extends Record<string, unknown> = Record<string, unknown>>({
  schema,
  initialValues,
  onSubmit,
  onCancel,
  isSubmitting = false,
  mode = "create",
  errors: serverErrors = {},
  className,
  relatedRecords = {},
  renderField,
}: RecordFormProps<T>) {
  const [formValues, setFormValues] = useState<Record<string, unknown>>(() =>
    getInitialFormValues(schema, initialValues as Record<string, unknown>),
  );
  const [clientErrors, setClientErrors] = useState<Record<string, string>>({});
  const [touched, setTouched] = useState<Set<string>>(new Set());

  // Merge server and client errors
  const allErrors = useMemo(
    () => ({ ...clientErrors, ...serverErrors }),
    [clientErrors, serverErrors],
  );

  // Get ordered fields (required first, then alphabetical)
  const orderedFields = useMemo(() => {
    const entries = Object.entries(schema.properties);
    const requiredSet = new Set(schema.required);

    return entries.sort(([aName], [bName]) => {
      const aRequired = requiredSet.has(aName);
      const bRequired = requiredSet.has(bName);

      if (aRequired && !bRequired) return -1;
      if (!aRequired && bRequired) return 1;
      return aName.localeCompare(bName);
    });
  }, [schema.properties, schema.required]);

  const handleFieldChange = useCallback((name: string, value: unknown) => {
    setFormValues((prev) => ({ ...prev, [name]: value }));
    setTouched((prev) => new Set(prev).add(name));
    // Clear client error for this field on change
    setClientErrors((prev) => {
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();

      if (mode === "view") return;

      // Coerce values to proper types
      const coercedValues: Record<string, unknown> = {};
      for (const [name, property] of Object.entries(schema.properties)) {
        if (!property.readOnly) {
          coercedValues[name] = coerceValue(formValues[name], property);
        }
      }

      // Validate
      const validation = validateForm(coercedValues, schema);

      if (!validation.valid) {
        setClientErrors(validation.errors);
        // Mark all fields as touched to show errors
        setTouched(new Set(Object.keys(schema.properties)));
        return;
      }

      setClientErrors({});
      await onSubmit(coercedValues as T);
    },
    [formValues, mode, onSubmit, schema],
  );

  const isViewMode = mode === "view";
  const submitLabel = mode === "create" ? "Create" : "Save Changes";

  return (
    <form onSubmit={handleSubmit} className={cn("space-y-6", className)} noValidate>
      {/* Form Fields Grid */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {orderedFields.map(([name, property]) => {
          const errorValue = touched.has(name) || serverErrors[name] ? allErrors[name] : undefined;
          const fieldConfig: FieldConfig = {
            name,
            property,
            required: schema.required.includes(name),
            value: formValues[name],
            error: errorValue,
            disabled: isSubmitting,
          };

          const defaultRender = () => (
            <FieldRenderer
              key={name}
              config={fieldConfig}
              onChange={handleFieldChange}
              relatedRecords={relatedRecords[name]}
              mode={mode}
            />
          );

          if (renderField) {
            return <div key={name}>{renderField(fieldConfig, defaultRender)}</div>;
          }

          return defaultRender();
        })}
      </div>

      {/* Form Actions */}
      {!isViewMode && (
        <div
          className={cn("flex items-center gap-3 pt-4", "border-t border-[var(--color-border)]")}
        >
          <Button type="submit" variant="primary" loading={isSubmitting} disabled={isSubmitting}>
            {submitLabel}
          </Button>
          {onCancel && (
            <Button type="button" variant="secondary" onClick={onCancel} disabled={isSubmitting}>
              Cancel
            </Button>
          )}
        </div>
      )}

      {/* View Mode: Back/Edit Actions */}
      {isViewMode && onCancel && (
        <div
          className={cn("flex items-center gap-3 pt-4", "border-t border-[var(--color-border)]")}
        >
          <Button type="button" variant="secondary" onClick={onCancel}>
            Back
          </Button>
        </div>
      )}
    </form>
  );
}

RecordForm.displayName = "RecordForm";
