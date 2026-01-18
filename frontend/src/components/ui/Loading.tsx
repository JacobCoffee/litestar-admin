'use client';

import { forwardRef, type HTMLAttributes } from 'react';
import { cn } from '@/lib/utils';

export type SpinnerSize = 'sm' | 'md' | 'lg' | 'xl';

export interface SpinnerProps extends HTMLAttributes<SVGSVGElement> {
  size?: SpinnerSize;
}

const spinnerSizes: Record<SpinnerSize, string> = {
  sm: 'h-4 w-4',
  md: 'h-6 w-6',
  lg: 'h-8 w-8',
  xl: 'h-12 w-12',
};

export const Spinner = forwardRef<SVGSVGElement, SpinnerProps>(
  ({ size = 'md', className, ...props }, ref) => {
    return (
      <svg
        ref={ref}
        className={cn(
          'animate-spin text-[var(--color-primary)]',
          spinnerSizes[size],
          className
        )}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        role="status"
        aria-label="Loading"
        {...props}
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
  }
);

Spinner.displayName = 'Spinner';

export type SkeletonVariant = 'text' | 'rectangular' | 'circular';

export interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
  variant?: SkeletonVariant;
  width?: string | number;
  height?: string | number;
  lines?: number;
}

export const Skeleton = forwardRef<HTMLDivElement, SkeletonProps>(
  (
    { variant = 'text', width, height, lines = 1, className, style, ...props },
    ref
  ) => {
    const baseStyles = cn(
      'bg-[var(--color-card-hover)]',
      'animate-pulse'
    );

    const variantStyles: Record<SkeletonVariant, string> = {
      text: 'h-4 rounded-[var(--radius-sm)]',
      rectangular: 'rounded-[var(--radius-md)]',
      circular: 'rounded-full',
    };

    const computedStyle = {
      width: typeof width === 'number' ? `${width}px` : width,
      height: typeof height === 'number' ? `${height}px` : height,
      ...style,
    };

    if (variant === 'text' && lines > 1) {
      return (
        <div ref={ref} className={cn('space-y-2', className)} {...props}>
          {Array.from({ length: lines }).map((_, index) => (
            <div
              key={index}
              className={cn(baseStyles, variantStyles.text)}
              style={{
                ...computedStyle,
                width: index === lines - 1 ? '75%' : computedStyle.width,
              }}
            />
          ))}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn(baseStyles, variantStyles[variant], className)}
        style={computedStyle}
        {...props}
      />
    );
  }
);

Skeleton.displayName = 'Skeleton';

export interface LoadingOverlayProps extends HTMLAttributes<HTMLDivElement> {
  isLoading?: boolean;
  label?: string;
  spinnerSize?: SpinnerSize;
}

export const LoadingOverlay = forwardRef<HTMLDivElement, LoadingOverlayProps>(
  (
    { isLoading = true, label = 'Loading...', spinnerSize = 'lg', className, children, ...props },
    ref
  ) => {
    if (!isLoading) {
      return <>{children}</>;
    }

    return (
      <div ref={ref} className={cn('relative', className)} {...props}>
        {children}
        <div
          className={cn(
            'absolute inset-0 z-10',
            'flex flex-col items-center justify-center gap-3',
            'bg-[var(--color-background)]/80 backdrop-blur-sm',
            'rounded-[var(--radius-md)]'
          )}
        >
          <Spinner size={spinnerSize} />
          {label && (
            <p className="text-sm text-[var(--color-muted)]">{label}</p>
          )}
        </div>
      </div>
    );
  }
);

LoadingOverlay.displayName = 'LoadingOverlay';

export interface SkeletonTableProps {
  rows?: number;
  columns?: number;
  showHeader?: boolean;
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  showHeader = true,
}: SkeletonTableProps) {
  return (
    <div className="w-full overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)]">
      {showHeader && (
        <div className="flex gap-4 bg-[var(--color-card)] px-4 py-3 border-b border-[var(--color-border)]">
          {Array.from({ length: columns }).map((_, i) => (
            <Skeleton key={i} variant="text" className="flex-1" />
          ))}
        </div>
      )}
      <div className="divide-y divide-[var(--color-border)]">
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <div key={rowIndex} className="flex gap-4 px-4 py-3">
            {Array.from({ length: columns }).map((_, colIndex) => (
              <Skeleton key={colIndex} variant="text" className="flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export interface SkeletonCardProps {
  showHeader?: boolean;
  showFooter?: boolean;
  bodyLines?: number;
}

export function SkeletonCard({
  showHeader = true,
  showFooter = false,
  bodyLines = 3,
}: SkeletonCardProps) {
  return (
    <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-card)] overflow-hidden">
      {showHeader && (
        <div className="px-6 py-4 border-b border-[var(--color-border)]">
          <Skeleton variant="text" width="40%" height={20} />
        </div>
      )}
      <div className="px-6 py-4">
        <Skeleton variant="text" lines={bodyLines} />
      </div>
      {showFooter && (
        <div className="px-6 py-4 border-t border-[var(--color-border)] bg-[var(--color-background)]/50">
          <div className="flex gap-3 justify-end">
            <Skeleton variant="rectangular" width={80} height={36} />
            <Skeleton variant="rectangular" width={80} height={36} />
          </div>
        </div>
      )}
    </div>
  );
}
