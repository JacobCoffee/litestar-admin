'use client';

import { Fragment } from 'react';
import Link from 'next/link';
import { cn } from '@/lib/utils';

// Icons as inline SVGs
const HomeIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z"
      clipRule="evenodd"
    />
  </svg>
);

const ChevronRightIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z"
      clipRule="evenodd"
    />
  </svg>
);

export interface BreadcrumbItem {
  /** Display label */
  label: string;
  /** Navigation href (omit for current page) */
  href?: string | undefined;
}

export interface BreadcrumbProps {
  /** Array of breadcrumb items */
  items: readonly BreadcrumbItem[];
  /** Whether to show home icon as first item */
  showHome?: boolean;
  /** Home link href */
  homeHref?: string;
  /** Custom separator element */
  separator?: React.ReactNode;
  /** Additional CSS classes */
  className?: string;
}

export function Breadcrumb({
  items,
  showHome = true,
  homeHref = '/',
  separator,
  className,
}: BreadcrumbProps) {
  const defaultSeparator = (
    <ChevronRightIcon className="h-4 w-4 text-[var(--color-muted)]" />
  );

  const separatorElement = separator ?? defaultSeparator;

  return (
    <nav aria-label="Breadcrumb" className={className}>
      <ol className="flex items-center gap-2">
        {/* Home item */}
        {showHome && (
          <li className="flex items-center">
            <Link
              href={homeHref}
              className={cn(
                'rounded-[var(--radius-sm)] p-1',
                'text-[var(--color-muted)] hover:text-[var(--color-foreground)]',
                'transition-colors duration-150',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
              )}
              aria-label="Home"
            >
              <HomeIcon className="h-4 w-4" />
            </Link>
          </li>
        )}

        {/* Separator after home */}
        {showHome && items.length > 0 && (
          <li aria-hidden="true" className="flex items-center">
            {separatorElement}
          </li>
        )}

        {/* Breadcrumb items */}
        {items.map((item, index) => {
          const isLast = index === items.length - 1;

          return (
            <Fragment key={`${item.label}-${index}`}>
              <li className="flex items-center">
                {item.href && !isLast ? (
                  <Link
                    href={item.href}
                    className={cn(
                      'rounded-[var(--radius-sm)] px-1.5 py-0.5 text-sm',
                      'text-[var(--color-muted)] hover:text-[var(--color-foreground)]',
                      'transition-colors duration-150',
                      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
                    )}
                  >
                    {item.label}
                  </Link>
                ) : (
                  <span
                    className={cn(
                      'px-1.5 py-0.5 text-sm',
                      isLast
                        ? 'font-medium text-[var(--color-foreground)]'
                        : 'text-[var(--color-muted)]'
                    )}
                    aria-current={isLast ? 'page' : undefined}
                  >
                    {item.label}
                  </span>
                )}
              </li>

              {/* Separator between items */}
              {!isLast && (
                <li aria-hidden="true" className="flex items-center">
                  {separatorElement}
                </li>
              )}
            </Fragment>
          );
        })}
      </ol>
    </nav>
  );
}

/**
 * Helper function to generate breadcrumb items from a pathname.
 * Converts '/users/123' to [{ label: 'Users', href: '/users' }, { label: '123' }]
 */
export function generateBreadcrumbsFromPath(
  pathname: string,
  basePath: string = '/'
): BreadcrumbItem[] {
  // Remove base path and split into segments
  const relativePath = pathname.startsWith(basePath)
    ? pathname.slice(basePath.length)
    : pathname;

  const segments = relativePath.split('/').filter(Boolean);

  if (segments.length === 0) {
    return [];
  }

  return segments.map((segment, index) => {
    // Build href from base path + all segments up to and including current
    const href = `${basePath}/${segments.slice(0, index + 1).join('/')}`;

    // Format label: capitalize and replace hyphens/underscores with spaces
    const label = segment
      .replace(/[-_]/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase());

    // Last item doesn't need href (current page)
    const isLast = index === segments.length - 1;

    return {
      label,
      href: isLast ? undefined : href,
    };
  });
}
