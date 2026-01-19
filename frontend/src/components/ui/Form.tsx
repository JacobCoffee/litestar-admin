'use client';

import {
  forwardRef,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
  type ReactNode,
  type LabelHTMLAttributes,
} from 'react';
import { cn } from '@/lib/utils';

const baseInputStyles = cn(
  'w-full rounded-[var(--radius-md)]',
  'bg-[var(--color-card)] text-[var(--color-foreground)]',
  'border border-[var(--color-border)]',
  'placeholder:text-[var(--color-muted)]',
  'transition-colors duration-150',
  'hover:border-[var(--color-muted)]',
  'focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]',
  'focus:outline-none',
  'disabled:cursor-not-allowed disabled:opacity-50 disabled:bg-[var(--color-card-hover)]'
);

const errorInputStyles = cn(
  'border-[var(--color-error)]',
  'focus:border-[var(--color-error)] focus:ring-[var(--color-error)]'
);

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ error = false, className, type = 'text', ...props }, ref) => {
    return (
      <input
        ref={ref}
        type={type}
        className={cn(
          baseInputStyles,
          'h-10 px-3',
          error && errorInputStyles,
          className
        )}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      />
    );
  }
);

Input.displayName = 'Input';

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  placeholder?: string;
  error?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ options, placeholder, error = false, className, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={cn(
          baseInputStyles,
          'h-10 px-3 pr-8',
          'appearance-none bg-no-repeat bg-right',
          'bg-[length:1.25rem_1.25rem] bg-[right_0.5rem_center]',
          '[background-image:url("data:image/svg+xml,%3csvg%20xmlns%3d%27http%3a%2f%2fwww.w3.org%2f2000%2fsvg%27%20fill%3d%27none%27%20viewBox%3d%270%200%2024%2024%27%20stroke%3d%27%238b949e%27%20stroke-width%3d%272%27%3e%3cpath%20d%3d%27M7%2010l5%205%205-5%27%2f%3e%3c%2fsvg%3e")]',
          error && errorInputStyles,
          className
        )}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      >
        {placeholder && (
          <option value="" disabled>
            {placeholder}
          </option>
        )}
        {options.map((option) => (
          <option key={option.value} value={option.value} disabled={option.disabled}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }
);

Select.displayName = 'Select';

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label?: ReactNode;
  error?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ label, error = false, className, id, ...props }, ref) => {
    const checkboxId = id || `checkbox-${Math.random().toString(36).substring(2, 9)}`;

    return (
      <div className={cn('flex items-center gap-2', className)}>
        <input
          ref={ref}
          type="checkbox"
          id={checkboxId}
          className={cn(
            'h-4 w-4 rounded-[var(--radius-sm)]',
            'bg-[var(--color-card)] border border-[var(--color-border)]',
            'text-[var(--color-primary)]',
            'focus:ring-2 focus:ring-[var(--color-accent)] focus:ring-offset-2',
            'focus:ring-offset-[var(--color-background)]',
            'transition-colors duration-150',
            'cursor-pointer',
            'disabled:cursor-not-allowed disabled:opacity-50',
            error && 'border-[var(--color-error)]'
          )}
          aria-invalid={error ? 'true' : undefined}
          {...props}
        />
        {label && (
          <label
            htmlFor={checkboxId}
            className={cn(
              'text-sm text-[var(--color-foreground)]',
              'cursor-pointer select-none',
              props.disabled && 'cursor-not-allowed opacity-50'
            )}
          >
            {label}
          </label>
        )}
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';

export interface TextAreaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  error?: boolean;
}

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  ({ error = false, className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          baseInputStyles,
          'min-h-[100px] px-3 py-2 resize-y',
          error && errorInputStyles,
          className
        )}
        aria-invalid={error ? 'true' : undefined}
        {...props}
      />
    );
  }
);

TextArea.displayName = 'TextArea';

export interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
  required?: boolean;
  children?: ReactNode;
}

export const Label = forwardRef<HTMLLabelElement, LabelProps>(
  ({ required = false, className, children, ...props }, ref) => {
    return (
      <label
        ref={ref}
        className={cn(
          'block text-sm font-medium text-[var(--color-foreground)]',
          'mb-1.5',
          className
        )}
        {...props}
      >
        {children}
        {required && (
          <>
            <span className="ml-1 text-[var(--color-error)]" aria-hidden="true">
              *
            </span>
            <span className="sr-only">(required)</span>
          </>
        )}
      </label>
    );
  }
);

Label.displayName = 'Label';

export interface FormFieldProps {
  label?: string;
  htmlFor?: string;
  required?: boolean;
  error?: string;
  hint?: string;
  className?: string;
  children: ReactNode;
}

export const FormField = forwardRef<HTMLDivElement, FormFieldProps>(
  ({ label, htmlFor, required = false, error, hint, className, children }, ref) => {
    // Generate IDs for aria-describedby
    const hintId = htmlFor ? `${htmlFor}-hint` : undefined;
    const errorId = htmlFor ? `${htmlFor}-error` : undefined;

    return (
      <div ref={ref} className={cn('space-y-1.5', className)}>
        {label && (
          <Label htmlFor={htmlFor} required={required}>
            {label}
          </Label>
        )}
        {children}
        {hint && !error && (
          <p
            id={hintId}
            className="text-xs text-[var(--color-muted)]"
          >
            {hint}
          </p>
        )}
        {error && (
          <p
            id={errorId}
            className="text-xs text-[var(--color-error)]"
            role="alert"
            aria-live="polite"
          >
            {error}
          </p>
        )}
      </div>
    );
  }
);

FormField.displayName = 'FormField';
