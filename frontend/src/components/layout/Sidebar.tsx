'use client';

import { useCallback, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/LayoutContext';
import type { NavCategory, NavItem } from '@/types';

// Icons as inline SVGs for zero dependencies
const ChevronDownIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
      clipRule="evenodd"
    />
  </svg>
);

const ChevronLeftIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M12.79 5.23a.75.75 0 01-.02 1.06L8.832 10l3.938 3.71a.75.75 0 11-1.04 1.08l-4.5-4.25a.75.75 0 010-1.08l4.5-4.25a.75.75 0 011.06.02z"
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

const DefaultModelIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm4.75 6.5a.75.75 0 00-1.5 0v2.25H5.5a.75.75 0 000 1.5h2.25v2.25a.75.75 0 001.5 0v-2.25h2.25a.75.75 0 000-1.5H9.25V8.5z"
      clipRule="evenodd"
    />
  </svg>
);

const XMarkIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
  </svg>
);

const UserCircleIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-5.5-2.5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM10 12a5.99 5.99 0 00-4.793 2.39A6.483 6.483 0 0010 16.5a6.483 6.483 0 004.793-2.11A5.99 5.99 0 0010 12z"
      clipRule="evenodd"
    />
  </svg>
);

export interface SidebarProps {
  /** Application logo/brand */
  logo?: ReactNode;
  /** Application title */
  title?: string;
  /** Navigation categories with items */
  categories?: readonly NavCategory[];
  /** User avatar URL */
  userAvatar?: string;
  /** User display name */
  userName?: string;
  /** User email */
  userEmail?: string;
  /** Callback when user menu is clicked */
  onUserMenuClick?: () => void;
  /** Additional CSS classes */
  className?: string;
}

interface CategorySectionProps {
  category: NavCategory;
  isCollapsed: boolean;
  pathname: string;
}

function CategorySection({ category, isCollapsed, pathname }: CategorySectionProps) {
  const [isExpanded, setIsExpanded] = useState(category.defaultOpen ?? true);

  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  if (isCollapsed) {
    // In collapsed mode, show only icons in a vertical list
    return (
      <div className="space-y-1">
        {category.items.map((item) => (
          <NavItemLink key={item.id} item={item} isCollapsed pathname={pathname} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <button
        type="button"
        onClick={toggleExpanded}
        className={cn(
          'flex w-full items-center justify-between px-3 py-2',
          'text-xs font-semibold uppercase tracking-wider',
          'text-[var(--color-muted)] hover:text-[var(--color-sidebar-foreground)]',
          'transition-colors duration-150'
        )}
        aria-expanded={isExpanded}
      >
        <span>{category.label}</span>
        <ChevronDownIcon
          className={cn(
            'h-4 w-4 transition-transform duration-200',
            isExpanded ? 'rotate-0' : '-rotate-90'
          )}
        />
      </button>
      <div
        className={cn(
          'overflow-hidden transition-all duration-200',
          isExpanded ? 'max-h-[1000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        <div className="space-y-1 pb-2">
          {category.items.map((item) => (
            <NavItemLink key={item.id} item={item} isCollapsed={false} pathname={pathname} />
          ))}
        </div>
      </div>
    </div>
  );
}

interface NavItemLinkProps {
  item: NavItem;
  isCollapsed: boolean;
  pathname: string;
}

function NavItemLink({ item, isCollapsed, pathname }: NavItemLinkProps) {
  const isActive = pathname === item.href || pathname.startsWith(`${item.href}/`);
  const Icon = item.icon ?? DefaultModelIcon;

  return (
    <Link
      href={item.href}
      className={cn(
        'group flex items-center gap-3 rounded-[var(--radius-md)] px-3 py-2',
        'text-sm font-medium transition-all duration-150',
        isActive
          ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]'
          : 'text-[var(--color-sidebar-foreground)] hover:bg-[var(--color-card-hover)] hover:text-[var(--color-foreground)]',
        isCollapsed && 'justify-center px-2'
      )}
      title={isCollapsed ? item.label : undefined}
      aria-current={isActive ? 'page' : undefined}
    >
      <Icon
        className={cn(
          'h-5 w-5 shrink-0 transition-colors',
          isActive ? 'text-[var(--color-primary)]' : 'text-[var(--color-muted)]'
        )}
      />
      {!isCollapsed && (
        <>
          <span className="truncate">{item.label}</span>
          {item.badge !== undefined && (
            <span
              className={cn(
                'ml-auto rounded-full px-2 py-0.5 text-xs font-medium',
                'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
              )}
            >
              {item.badge}
            </span>
          )}
        </>
      )}
    </Link>
  );
}

export function Sidebar({
  logo,
  title = 'Litestar Admin',
  categories = [],
  userAvatar,
  userName,
  userEmail,
  onUserMenuClick,
  className,
}: SidebarProps) {
  const { isOpen, isCollapsed, isMobile, close, toggleCollapse } = useSidebar();
  const pathname = usePathname();

  const sidebarContent = (
    <>
      {/* Header with logo and title */}
      <div
        className={cn(
          'flex h-16 items-center border-b border-[var(--color-sidebar-border)]',
          isCollapsed ? 'justify-center px-2' : 'gap-3 px-4'
        )}
      >
        {logo ?? (
          <div
            className={cn(
              'flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--radius-md)]',
              'bg-[var(--color-primary)] text-white font-bold text-lg'
            )}
          >
            L
          </div>
        )}
        {!isCollapsed && <span className="truncate text-lg font-semibold">{title}</span>}
        {isMobile && (
          <button
            type="button"
            onClick={close}
            className="ml-auto p-1.5 rounded-[var(--radius-md)] hover:bg-[var(--color-card-hover)]"
            aria-label="Close sidebar"
          >
            <XMarkIcon className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-4" aria-label="Main navigation">
        {/* Dashboard link */}
        <div className="mb-4">
          <NavItemLink
            item={{ id: 'dashboard', label: 'Dashboard', href: '/admin', icon: HomeIcon }}
            isCollapsed={isCollapsed}
            pathname={pathname}
          />
        </div>

        {/* Categories */}
        <div className="space-y-4">
          {categories.map((category) => (
            <CategorySection
              key={category.id}
              category={category}
              isCollapsed={isCollapsed}
              pathname={pathname}
            />
          ))}
        </div>
      </nav>

      {/* Collapse toggle (desktop only) */}
      {!isMobile && (
        <div className="border-t border-[var(--color-sidebar-border)] p-2">
          <button
            type="button"
            onClick={toggleCollapse}
            className={cn(
              'flex w-full items-center justify-center gap-2 rounded-[var(--radius-md)] p-2',
              'text-[var(--color-muted)] hover:bg-[var(--color-card-hover)] hover:text-[var(--color-sidebar-foreground)]',
              'transition-colors duration-150'
            )}
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRightIcon className="h-5 w-5" />
            ) : (
              <>
                <ChevronLeftIcon className="h-5 w-5" />
                <span className="text-sm">Collapse</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* User section */}
      <div className="border-t border-[var(--color-sidebar-border)] p-2">
        <button
          type="button"
          onClick={onUserMenuClick}
          className={cn(
            'flex w-full items-center gap-3 rounded-[var(--radius-md)] p-2',
            'hover:bg-[var(--color-card-hover)] transition-colors duration-150',
            isCollapsed && 'justify-center'
          )}
          aria-label="User menu"
        >
          {userAvatar ? (
            <img
              src={userAvatar}
              alt=""
              className="h-8 w-8 shrink-0 rounded-full object-cover"
            />
          ) : (
            <UserCircleIcon className="h-8 w-8 shrink-0 text-[var(--color-muted)]" />
          )}
          {!isCollapsed && (
            <div className="min-w-0 flex-1 text-left">
              {userName && (
                <p className="truncate text-sm font-medium text-[var(--color-sidebar-foreground)]">
                  {userName}
                </p>
              )}
              {userEmail && (
                <p className="truncate text-xs text-[var(--color-muted)]">{userEmail}</p>
              )}
            </div>
          )}
        </button>
      </div>
    </>
  );

  // Mobile: render as drawer with overlay
  if (isMobile) {
    return (
      <>
        {/* Overlay */}
        <div
          className={cn(
            'fixed inset-0 z-40 bg-black/50 transition-opacity duration-300',
            isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
          )}
          onClick={close}
          aria-hidden="true"
        />
        {/* Drawer */}
        <aside
          className={cn(
            'fixed inset-y-0 left-0 z-50 flex w-64 flex-col',
            'bg-[var(--color-sidebar)] text-[var(--color-sidebar-foreground)]',
            'transform transition-transform duration-300 ease-in-out',
            isOpen ? 'translate-x-0' : '-translate-x-full',
            className
          )}
          aria-label="Sidebar navigation"
        >
          {sidebarContent}
        </aside>
      </>
    );
  }

  // Desktop: render as fixed sidebar
  return (
    <aside
      className={cn(
        'fixed inset-y-0 left-0 z-30 flex flex-col',
        'bg-[var(--color-sidebar)] text-[var(--color-sidebar-foreground)]',
        'border-r border-[var(--color-sidebar-border)]',
        'transition-all duration-300 ease-in-out',
        isCollapsed ? 'w-16' : 'w-64',
        className
      )}
      aria-label="Sidebar navigation"
    >
      {sidebarContent}
    </aside>
  );
}
