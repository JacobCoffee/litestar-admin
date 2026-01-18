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
          className={cn(
            'flex-1 overflow-y-auto p-4 md:p-6',
            contentClassName
          )}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
