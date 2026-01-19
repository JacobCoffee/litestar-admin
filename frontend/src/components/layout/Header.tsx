'use client';

import { useCallback, useRef, useState, type ReactNode } from 'react';
import { cn } from '@/lib/utils';
import { useSidebar } from '@/contexts/LayoutContext';
import { useTheme } from '@/contexts/ThemeContext';

// Icons as inline SVGs
const MenuIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M2 4.75A.75.75 0 012.75 4h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 4.75zM2 10a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75A.75.75 0 012 10zm0 5.25a.75.75 0 01.75-.75h14.5a.75.75 0 010 1.5H2.75a.75.75 0 01-.75-.75z"
      clipRule="evenodd"
    />
  </svg>
);

const SearchIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z"
      clipRule="evenodd"
    />
  </svg>
);

const BellIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M10 2a6 6 0 00-6 6c0 1.887-.454 3.665-1.257 5.234a.75.75 0 00.515 1.076 32.91 32.91 0 003.256.508 3.5 3.5 0 006.972 0 32.903 32.903 0 003.256-.508.75.75 0 00.515-1.076A11.448 11.448 0 0116 8a6 6 0 00-6-6zM8.05 14.943a33.54 33.54 0 003.9 0 2 2 0 01-3.9 0z"
      clipRule="evenodd"
    />
  </svg>
);

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

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z"
      clipRule="evenodd"
    />
  </svg>
);

const LogoutIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M3 4.25A2.25 2.25 0 015.25 2h5.5A2.25 2.25 0 0113 4.25v2a.75.75 0 01-1.5 0v-2a.75.75 0 00-.75-.75h-5.5a.75.75 0 00-.75.75v11.5c0 .414.336.75.75.75h5.5a.75.75 0 00.75-.75v-2a.75.75 0 011.5 0v2A2.25 2.25 0 0110.75 18h-5.5A2.25 2.25 0 013 15.75V4.25z"
      clipRule="evenodd"
    />
    <path
      fillRule="evenodd"
      d="M19 10a.75.75 0 00-.75-.75H8.704l1.048-.943a.75.75 0 10-1.004-1.114l-2.5 2.25a.75.75 0 000 1.114l2.5 2.25a.75.75 0 101.004-1.114l-1.048-.943h9.546A.75.75 0 0019 10z"
      clipRule="evenodd"
    />
  </svg>
);

const SunIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      d="M10 2a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 2zM10 15a.75.75 0 01.75.75v1.5a.75.75 0 01-1.5 0v-1.5A.75.75 0 0110 15zM10 7a3 3 0 100 6 3 3 0 000-6zM15.657 5.404a.75.75 0 10-1.06-1.06l-1.061 1.06a.75.75 0 001.06 1.061l1.06-1.06zM6.464 14.596a.75.75 0 10-1.06-1.06l-1.06 1.06a.75.75 0 001.06 1.06l1.06-1.06zM18 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 0118 10zM5 10a.75.75 0 01-.75.75h-1.5a.75.75 0 010-1.5h1.5A.75.75 0 015 10zM14.596 15.657a.75.75 0 001.06-1.06l-1.06-1.061a.75.75 0 10-1.06 1.06l1.06 1.06zM5.404 6.464a.75.75 0 001.06-1.06l-1.06-1.06a.75.75 0 10-1.061 1.06l1.06 1.06z"
    />
  </svg>
);

const MoonIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    xmlns="http://www.w3.org/2000/svg"
    viewBox="0 0 20 20"
    fill="currentColor"
    aria-hidden="true"
  >
    <path
      fillRule="evenodd"
      d="M7.455 2.004a.75.75 0 01.26.77 7 7 0 009.958 7.967.75.75 0 011.067.853A8.5 8.5 0 116.647 1.921a.75.75 0 01.808.083z"
      clipRule="evenodd"
    />
  </svg>
);

export interface HeaderProps {
  /** Callback when search is submitted */
  onSearch?: (query: string) => void;
  /** Search placeholder text */
  searchPlaceholder?: string;
  /** User avatar URL */
  userAvatar?: string;
  /** User display name */
  userName?: string;
  /** User email */
  userEmail?: string;
  /** Number of unread notifications */
  notificationCount?: number;
  /** Callback when notifications bell is clicked */
  onNotificationsClick?: () => void;
  /** Callback for profile menu item */
  onProfileClick?: () => void;
  /** Callback for settings menu item */
  onSettingsClick?: () => void;
  /** Callback for logout menu item */
  onLogoutClick?: () => void;
  /** Breadcrumb component to render */
  breadcrumb?: ReactNode;
  /** Additional CSS classes */
  className?: string;
}

interface UserDropdownProps {
  userAvatar?: string | undefined;
  userName?: string | undefined;
  userEmail?: string | undefined;
  onProfileClick?: (() => void) | undefined;
  onSettingsClick?: (() => void) | undefined;
  onLogoutClick?: (() => void) | undefined;
}

function UserDropdown({
  userAvatar,
  userName,
  userEmail,
  onProfileClick,
  onSettingsClick,
  onLogoutClick,
}: UserDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const toggleDropdown = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  const closeDropdown = useCallback(() => {
    setIsOpen(false);
  }, []);

  // Close on outside click
  const handleBlur = useCallback(
    (event: React.FocusEvent) => {
      if (!dropdownRef.current?.contains(event.relatedTarget as Node)) {
        closeDropdown();
      }
    },
    [closeDropdown]
  );

  const menuItems = [
    { label: 'Profile', icon: UserCircleIcon, onClick: onProfileClick },
    { label: 'Settings', icon: SettingsIcon, onClick: onSettingsClick },
    { label: 'Logout', icon: LogoutIcon, onClick: onLogoutClick },
  ];

  return (
    <div ref={dropdownRef} className="relative" onBlur={handleBlur}>
      <button
        type="button"
        onClick={toggleDropdown}
        className={cn(
          'flex items-center gap-2 rounded-[var(--radius-md)] p-1.5',
          'hover:bg-[var(--color-card-hover)] transition-colors duration-150',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
        )}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {userAvatar ? (
          <img src={userAvatar} alt="" className="h-8 w-8 rounded-full object-cover" />
        ) : (
          <UserCircleIcon className="h-8 w-8 text-[var(--color-muted)]" />
        )}
        <span className="hidden text-sm font-medium md:inline">{userName ?? 'User'}</span>
        <ChevronDownIcon
          className={cn('h-4 w-4 text-[var(--color-muted)] transition-transform', isOpen && 'rotate-180')}
        />
      </button>

      {/* Dropdown menu */}
      <div
        className={cn(
          'absolute right-0 top-full z-50 mt-2 w-56',
          'rounded-[var(--radius-lg)] border border-[var(--color-border)]',
          'bg-[var(--color-card)] shadow-lg',
          'transition-all duration-150 origin-top-right',
          isOpen ? 'scale-100 opacity-100' : 'pointer-events-none scale-95 opacity-0'
        )}
        role="menu"
        aria-orientation="vertical"
      >
        {/* User info */}
        {(userName || userEmail) && (
          <div className="border-b border-[var(--color-border)] px-4 py-3">
            {userName && (
              <p className="text-sm font-medium text-[var(--color-foreground)]">{userName}</p>
            )}
            {userEmail && <p className="text-xs text-[var(--color-muted)]">{userEmail}</p>}
          </div>
        )}

        {/* Menu items */}
        <div className="py-1">
          {menuItems.map((item) => (
            <button
              key={item.label}
              type="button"
              onClick={() => {
                closeDropdown();
                item.onClick?.();
              }}
              className={cn(
                'flex w-full items-center gap-3 px-4 py-2',
                'text-sm text-[var(--color-foreground)]',
                'hover:bg-[var(--color-card-hover)] transition-colors duration-150'
              )}
              role="menuitem"
            >
              <item.icon className="h-4 w-4 text-[var(--color-muted)]" />
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

export function Header({
  onSearch,
  searchPlaceholder = 'Search...',
  userAvatar,
  userName,
  userEmail,
  notificationCount,
  onNotificationsClick,
  onProfileClick,
  onSettingsClick,
  onLogoutClick,
  breadcrumb,
  className,
}: HeaderProps) {
  const { isMobile, toggle } = useSidebar();
  const { resolvedTheme, toggleTheme } = useTheme();
  const [searchQuery, setSearchQuery] = useState('');

  const handleSearchSubmit = useCallback(
    (event: React.FormEvent) => {
      event.preventDefault();
      onSearch?.(searchQuery);
    },
    [onSearch, searchQuery]
  );

  const handleSearchChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  }, []);

  return (
    <header
      className={cn(
        'sticky top-0 z-20 flex h-16 items-center gap-4',
        'border-b border-[var(--color-border)] bg-[var(--color-background)]',
        'px-4 md:px-6',
        className
      )}
    >
      {/* Mobile menu toggle */}
      {isMobile && (
        <button
          type="button"
          onClick={toggle}
          className={cn(
            'rounded-[var(--radius-md)] p-2',
            'hover:bg-[var(--color-card-hover)] transition-colors duration-150',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
          )}
          aria-label="Toggle menu"
        >
          <MenuIcon className="h-5 w-5" />
        </button>
      )}

      {/* Breadcrumb */}
      {breadcrumb && <div className="hidden md:block">{breadcrumb}</div>}

      {/* Search */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-md ml-auto md:ml-0">
        <div className="relative">
          <SearchIcon className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--color-muted)]" />
          <input
            type="search"
            value={searchQuery}
            onChange={handleSearchChange}
            placeholder={searchPlaceholder}
            className={cn(
              'w-full rounded-[var(--radius-md)] border border-[var(--color-border)]',
              'bg-[var(--color-card)] py-2 pl-10 pr-4 text-sm',
              'text-[var(--color-foreground)] placeholder:text-[var(--color-muted)]',
              'focus:border-[var(--color-accent)] focus:outline-none focus:ring-1 focus:ring-[var(--color-accent)]',
              'transition-colors duration-150'
            )}
            aria-label="Search"
          />
        </div>
      </form>

      {/* Right section */}
      <div className="flex items-center gap-2">
        {/* Theme toggle */}
        <button
          type="button"
          onClick={toggleTheme}
          className={cn(
            'rounded-[var(--radius-md)] p-2',
            'hover:bg-[var(--color-card-hover)] transition-colors duration-150',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
          )}
          aria-label={resolvedTheme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        >
          {resolvedTheme === 'dark' ? (
            <SunIcon className="h-5 w-5 text-[var(--color-muted)]" />
          ) : (
            <MoonIcon className="h-5 w-5 text-[var(--color-muted)]" />
          )}
        </button>

        {/* Notifications */}
        <button
          type="button"
          onClick={onNotificationsClick}
          className={cn(
            'relative rounded-[var(--radius-md)] p-2',
            'hover:bg-[var(--color-card-hover)] transition-colors duration-150',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]'
          )}
          aria-label={`Notifications${notificationCount ? ` (${notificationCount} unread)` : ''}`}
        >
          <BellIcon className="h-5 w-5 text-[var(--color-muted)]" />
          {notificationCount !== undefined && notificationCount > 0 && (
            <span
              className={cn(
                'absolute -right-0.5 -top-0.5 flex h-5 min-w-[1.25rem] items-center justify-center',
                'rounded-full bg-[var(--color-error)] px-1.5 text-xs font-medium text-white'
              )}
            >
              {notificationCount > 99 ? '99+' : notificationCount}
            </span>
          )}
        </button>

        {/* User dropdown */}
        <UserDropdown
          userAvatar={userAvatar}
          userName={userName}
          userEmail={userEmail}
          onProfileClick={onProfileClick}
          onSettingsClick={onSettingsClick}
          onLogoutClick={onLogoutClick}
        />
      </div>
    </header>
  );
}
