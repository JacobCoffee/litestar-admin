'use client';

import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export type ButtonVariant = 'primary' | 'secondary' | 'danger' | 'ghost' | 'link';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  children?: ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary: cn(
    'bg-[var(--color-primary)] text-[var(--color-primary-foreground)]',
    'hover:bg-[var(--color-primary-hover)]',
    'focus-visible:ring-[var(--color-primary)]',
    'disabled:bg-[var(--color-primary)]/50'
  ),
  secondary: cn(
    'bg-[var(--color-card)] text-[var(--color-foreground)]',
    'border border-[var(--color-border)]',
    'hover:bg-[var(--color-card-hover)] hover:border-[var(--color-muted)]',
    'focus-visible:ring-[var(--color-accent)]',
    'disabled:bg-[var(--color-card)]/50'
  ),
  danger: cn(
    'bg-[var(--color-error)] text-white',
    'hover:bg-[var(--color-error)]/80',
    'focus-visible:ring-[var(--color-error)]',
    'disabled:bg-[var(--color-error)]/50'
  ),
  ghost: cn(
    'bg-transparent text-[var(--color-foreground)]',
    'hover:bg-[var(--color-card-hover)]',
    'focus-visible:ring-[var(--color-accent)]',
    'disabled:bg-transparent'
  ),
  link: cn(
    'bg-transparent text-[var(--color-accent)]',
    'hover:text-[var(--color-accent)]/80 hover:underline',
    'focus-visible:ring-[var(--color-accent)]',
    'disabled:text-[var(--color-accent)]/50',
    'p-0 h-auto'
  ),
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-10 px-4 text-sm gap-2',
  lg: 'h-12 px-6 text-base gap-2.5',
};

const Spinner = ({ className }: { className?: string }) => (
  <svg
    className={cn('animate-spin', className)}
    xmlns="http://www.w3.org/2000/svg"
    fill="none"
    viewBox="0 0 24 24"
    aria-hidden="true"
  >
    <circle
      className="opacity-25"
      cx="12"
      cy="12"
      r="10"
      stroke="currentColor"
      strokeWidth="4"
    />
    <path
      className="opacity-75"
      fill="currentColor"
      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
    />
  </svg>
);

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled,
      leftIcon,
      rightIcon,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        disabled={isDisabled}
        className={cn(
          'inline-flex items-center justify-center font-medium',
          'rounded-[var(--radius-md)]',
          'transition-colors duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2',
          'focus-visible:ring-offset-[var(--color-background)]',
          'disabled:cursor-not-allowed disabled:opacity-60',
          variantStyles[variant],
          variant !== 'link' && sizeStyles[size],
          className
        )}
        {...props}
      >
        {loading ? (
          <Spinner className={size === 'sm' ? 'h-4 w-4' : 'h-5 w-5'} />
        ) : (
          leftIcon
        )}
        {children}
        {!loading && rightIcon}
      </button>
    );
  }
);

Button.displayName = 'Button';
