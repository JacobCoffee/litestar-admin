'use client';

import type { ReactNode } from 'react';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/LayoutContext';
import { Sidebar, type SidebarProps } from './Sidebar';
import { Header, type HeaderProps } from './Header';
import { Breadcrumb, generateBreadcrumbsFromPath } from './Breadcrumb';

export interface MainLayoutProps {
  /** Main content */
  children: ReactNode;
  /** Sidebar configuration */
  sidebar?: Omit<SidebarProps, 'className'>;
  /** Header configuration */
  header?: Omit<HeaderProps, 'breadcrumb' | 'className'>;
  /** Whether to show breadcrumbs in header */
  showBreadcrumbs?: boolean;
  /** Base path for breadcrumb generation */
  basePath?: string;
  /** Additional CSS classes for the main content area */
  contentClassName?: string;
  /** Additional CSS classes for the layout wrapper */
  className?: string;
}

export function MainLayout({
  children,
  sidebar,
  header,
  showBreadcrumbs = true,
  basePath = '/admin',
  contentClassName,
  className,
}: MainLayoutProps) {
  const { isCollapsed, isMobile } = useSidebar();
  const pathname = usePathname();

  // Generate breadcrumbs from current path
  const breadcrumbItems = showBreadcrumbs
    ? generateBreadcrumbsFromPath(pathname, basePath)
    : [];

  const breadcrumb =
    showBreadcrumbs && breadcrumbItems.length > 0 ? (
      <Breadcrumb items={breadcrumbItems} homeHref={basePath} />
    ) : undefined;

  return (
    <div className={cn('min-h-screen bg-[var(--color-background)]', className)}>
      {/* Skip to main content link - visible only on focus for keyboard users */}
      <a
        href="#main-content"
        className={cn(
          'sr-only focus:not-sr-only',
          'fixed top-4 left-4 z-[100]',
          'px-4 py-2 rounded-[var(--radius-md)]',
          'bg-[var(--color-primary)] text-[var(--color-primary-foreground)]',
          'font-medium text-sm',
          'focus:outline-none focus-visible:ring-2',
          'focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2',
          'focus-visible:ring-offset-[var(--color-background)]'
        )}
      >
        Skip to main content
      </a>

      {/* Sidebar */}
      <Sidebar {...sidebar} />

      {/* Main content wrapper */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          // Offset for sidebar width on desktop
          !isMobile && (isCollapsed ? 'ml-16' : 'ml-64')
        )}
      >
        {/* Header */}
        <Header {...header} breadcrumb={breadcrumb} />

        {/* Main content area */}
        <main
          id="main-content"
          tabIndex={-1}
          className={cn(
            'flex-1 overflow-y-auto p-4 md:p-6',
            'focus:outline-none',
            contentClassName
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
