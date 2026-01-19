'use client';

import { useMemo, type ReactNode } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/LayoutContext';
import { useAuthContext } from '@/contexts/AuthContext';
import { useModels } from '@/hooks/useApi';
import { Sidebar, type SidebarProps } from './Sidebar';
import { Header, type HeaderProps } from './Header';
import { Breadcrumb, generateBreadcrumbsFromPath } from './Breadcrumb';
import type { NavCategory } from '@/types';

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

// Default model icon component
const TableIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 20 20"
    fill="currentColor"
  >
    <path
      fillRule="evenodd"
      d="M3 3a1 1 0 011-1h12a1 1 0 011 1v14a1 1 0 01-1 1H4a1 1 0 01-1-1V3zm2 0v4h10V3H5zm10 6H5v8h10V9z"
      clipRule="evenodd"
    />
  </svg>
);

export function MainLayout({
  children,
  sidebar,
  header,
  showBreadcrumbs = true,
  basePath = '/',
  contentClassName,
  className,
}: MainLayoutProps) {
  const { isCollapsed, isMobile } = useSidebar();
  const { user, logout } = useAuthContext();
  const pathname = usePathname();
  const router = useRouter();

  // Fetch models for sidebar
  const { data: models } = useModels();

  // Build sidebar categories from models
  const sidebarCategories = useMemo<NavCategory[]>(() => {
    if (!models || models.length === 0) {
      return [{
        id: 'models',
        label: 'Models',
        items: [],
      }];
    }

    // Group models by category
    const grouped = new Map<string, typeof models>();
    for (const model of models) {
      const category = model.category ?? 'Models';
      if (!grouped.has(category)) {
        grouped.set(category, []);
      }
      grouped.get(category)!.push(model);
    }

    // Convert to NavCategory format
    const categories: NavCategory[] = [];
    for (const [categoryName, categoryModels] of grouped) {
      categories.push({
        id: categoryName.toLowerCase().replace(/\s+/g, '-'),
        label: categoryName,
        items: categoryModels.map((model) => ({
          id: model.model_name,
          label: model.name,
          href: `/models/${model.model_name}`,
          icon: TableIcon,
        })),
      });
    }

    return categories;
  }, [models]);

  // Generate breadcrumbs from current path
  const breadcrumbItems = showBreadcrumbs
    ? generateBreadcrumbsFromPath(pathname, basePath)
    : [];

  const breadcrumb =
    showBreadcrumbs && breadcrumbItems.length > 0 ? (
      <Breadcrumb items={breadcrumbItems} homeHref={basePath} />
    ) : undefined;

  // User info for sidebar and header
  // AdminUser doesn't have name field, derive from email
  const userName = user?.email?.split('@')[0] ?? 'User';
  const userEmail = user?.email ?? '';

  const handleLogout = async () => {
    await logout();
  };

  const handleProfileClick = () => {
    router.push('/profile');
  };

  const handleSettingsClick = () => {
    router.push('/settings');
  };

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
      <Sidebar
        {...sidebar}
        categories={sidebar?.categories ?? sidebarCategories}
        userName={userName}
        userEmail={userEmail}
      />

      {/* Main content wrapper */}
      <div
        className={cn(
          'flex min-h-screen flex-col transition-all duration-300',
          // Offset for sidebar width on desktop
          !isMobile && (isCollapsed ? 'ml-16' : 'ml-64')
        )}
      >
        {/* Header */}
        <Header
          {...header}
          breadcrumb={breadcrumb}
          userName={userName}
          userEmail={userEmail}
          onLogoutClick={handleLogout}
          onProfileClick={handleProfileClick}
          onSettingsClick={handleSettingsClick}
        />

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
