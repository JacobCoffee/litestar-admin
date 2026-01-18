'use client';

import { useState, useRef, useEffect, useCallback, type ReactNode } from 'react';
import Link from 'next/link';

import { useAuthContext } from '@/contexts/AuthContext';
import { cn } from '@/lib/utils';

/**
 * Props for UserMenu component.
 */
export interface UserMenuProps {
  /** Additional class names for the container */
  className?: string;
  /** Custom avatar component */
  avatar?: ReactNode;
}

/**
 * User icon for default avatar.
 */
function UserIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

/**
 * Settings icon for menu item.
 */
function SettingsIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/**
 * Logout icon for menu item.
 */
function LogoutIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

/**
 * Chevron icon for dropdown indicator.
 */
function ChevronIcon({ className, isOpen }: { className?: string; isOpen: boolean }) {
  return (
    <svg
      className={cn(
        className,
        'transition-transform duration-150',
        isOpen && 'rotate-180'
      )}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}

/**
 * Get initials from user email.
 */
function getInitials(email: string): string {
  const localPart = email.split('@')[0] ?? '';
  const parts = localPart.split(/[._-]/);
  if (parts.length >= 2) {
    const first = parts[0] ?? '';
    const second = parts[1] ?? '';
    return ((first[0] ?? '') + (second[0] ?? '')).toUpperCase();
  }
  return email.slice(0, 2).toUpperCase();
}

/**
 * User menu dropdown component.
 * Shows current user info with dropdown for Profile, Settings, and Logout.
 *
 * @example
 * ```tsx
 * // Basic usage in header
 * <header>
 *   <nav>...</nav>
 *   <UserMenu />
 * </header>
 *
 * // With custom avatar
 * <UserMenu avatar={<img src={user.avatar} alt="" />} />
 * ```
 */
export function UserMenu({ className, avatar }: UserMenuProps) {
  const { user, logout, isLoggingOut } = useAuthContext();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close menu on escape key
  useEffect(() => {
    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsOpen(false);
        buttonRef.current?.focus();
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      return () => document.removeEventListener('keydown', handleEscape);
    }
  }, [isOpen]);

  const handleLogout = useCallback(async () => {
    setIsOpen(false);
    await logout();
  }, [logout]);

  const toggleMenu = useCallback(() => {
    setIsOpen((prev) => !prev);
  }, []);

  if (!user) {
    return null;
  }

  const initials = getInitials(user.email);

  return (
    <div className={cn('relative', className)}>
      <button
        ref={buttonRef}
        type="button"
        onClick={toggleMenu}
        className={cn(
          'flex items-center gap-2 rounded-[var(--radius-md)] p-2',
          'text-[var(--color-foreground)]',
          'hover:bg-[var(--color-card-hover)]',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]',
          'transition-colors duration-150'
        )}
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        {avatar ?? (
          <div
            className={cn(
              'flex h-8 w-8 items-center justify-center rounded-full',
              'bg-[var(--color-primary)] text-[var(--color-primary-foreground)]',
              'text-xs font-medium'
            )}
          >
            {initials}
          </div>
        )}
        <div className="hidden sm:block text-left">
          <p className="text-sm font-medium truncate max-w-[120px]">{user.email}</p>
          {user.roles.length > 0 && (
            <p className="text-xs text-[var(--color-muted)] truncate max-w-[120px]">
              {user.roles[0]}
            </p>
          )}
        </div>
        <ChevronIcon className="h-4 w-4 text-[var(--color-muted)] hidden sm:block" isOpen={isOpen} />
      </button>

      {isOpen && (
        <div
          ref={menuRef}
          className={cn(
            'absolute right-0 top-full mt-2 z-50',
            'w-56 rounded-[var(--radius-lg)]',
            'bg-[var(--color-card)] border border-[var(--color-border)]',
            'shadow-lg shadow-black/30',
            'animate-[scaleIn_150ms_ease-out]',
            'origin-top-right'
          )}
          role="menu"
          aria-orientation="vertical"
        >
          {/* User info section */}
          <div className="px-4 py-3 border-b border-[var(--color-border)]">
            <p className="text-sm font-medium text-[var(--color-foreground)] truncate">
              {user.email}
            </p>
            {user.roles.length > 0 && (
              <p className="text-xs text-[var(--color-muted)] mt-0.5">
                {user.roles.join(', ')}
              </p>
            )}
          </div>

          {/* Menu items */}
          <div className="py-1">
            <Link
              href="/admin/profile"
              onClick={() => setIsOpen(false)}
              className={cn(
                'flex items-center gap-3 px-4 py-2',
                'text-sm text-[var(--color-foreground)]',
                'hover:bg-[var(--color-card-hover)]',
                'transition-colors duration-150'
              )}
              role="menuitem"
            >
              <UserIcon className="h-4 w-4 text-[var(--color-muted)]" />
              Profile
            </Link>

            <Link
              href="/admin/settings"
              onClick={() => setIsOpen(false)}
              className={cn(
                'flex items-center gap-3 px-4 py-2',
                'text-sm text-[var(--color-foreground)]',
                'hover:bg-[var(--color-card-hover)]',
                'transition-colors duration-150'
              )}
              role="menuitem"
            >
              <SettingsIcon className="h-4 w-4 text-[var(--color-muted)]" />
              Settings
            </Link>
          </div>

          {/* Logout section */}
          <div className="py-1 border-t border-[var(--color-border)]">
            <button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className={cn(
                'flex w-full items-center gap-3 px-4 py-2',
                'text-sm text-[var(--color-error)]',
                'hover:bg-[var(--color-card-hover)]',
                'transition-colors duration-150',
                'disabled:opacity-50 disabled:cursor-not-allowed'
              )}
              role="menuitem"
            >
              <LogoutIcon className="h-4 w-4" />
              {isLoggingOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
