'use client';

import Link from 'next/link';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

export interface QuickAction {
  /** Unique identifier */
  id: string;
  /** Display label */
  label: string;
  /** Description text */
  description?: string;
  /** Target URL */
  href: string;
  /** Icon component */
  icon?: React.ReactNode;
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'ghost';
}

export interface QuickActionsProps {
  /** Custom actions to display */
  actions?: readonly QuickAction[];
  /** Additional CSS classes */
  className?: string;
}

const defaultActions: QuickAction[] = [
  {
    id: 'browse-models',
    label: 'Browse Models',
    description: 'View and manage all models',
    href: '/models',
    icon: <ModelsIcon />,
    variant: 'primary',
  },
  {
    id: 'create-record',
    label: 'Create Record',
    description: 'Add a new record to any model',
    href: '/models',
    icon: <UserPlusIcon />,
    variant: 'secondary',
  },
  {
    id: 'export-data',
    label: 'Export Data',
    description: 'Export from model list pages',
    href: '/models',
    icon: <DownloadIcon />,
    variant: 'secondary',
  },
];

/**
 * Panel displaying quick action buttons for common operations.
 */
export function QuickActions({
  actions = defaultActions,
  className,
}: QuickActionsProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <h2 className="text-base font-semibold text-[var(--color-foreground)]">
          Quick Actions
        </h2>
        <p className="mt-0.5 text-sm text-[var(--color-muted)]">
          Common tasks and shortcuts
        </p>
      </CardHeader>
      <CardBody className="flex flex-col gap-2">
        {actions.map((action) => (
          <QuickActionButton key={action.id} action={action} />
        ))}
      </CardBody>
    </Card>
  );
}

interface QuickActionButtonProps {
  action: QuickAction;
}

function QuickActionButton({ action }: QuickActionButtonProps) {
  const isPrimary = action.variant === 'primary';

  return (
    <Link href={action.href} className="block">
      <Button
        variant={action.variant ?? 'secondary'}
        className={cn(
          'w-full justify-start gap-3 h-auto py-3 px-4',
          'text-left',
          !isPrimary && 'hover:bg-[var(--color-card-hover)]'
        )}
      >
        {action.icon && (
          <span
            className={cn(
              'flex h-8 w-8 shrink-0 items-center justify-center rounded-lg',
              isPrimary
                ? 'bg-white/20'
                : 'bg-[var(--color-card)] border border-[var(--color-border)]'
            )}
          >
            {action.icon}
          </span>
        )}
        <span className="flex-1 min-w-0">
          <span
            className={cn(
              'block text-sm font-medium',
              isPrimary ? 'text-white' : 'text-[var(--color-foreground)]'
            )}
          >
            {action.label}
          </span>
          {action.description && (
            <span
              className={cn(
                'block text-xs mt-0.5',
                isPrimary ? 'text-white/80' : 'text-[var(--color-muted)]'
              )}
            >
              {action.description}
            </span>
          )}
        </span>
        <ChevronRightIcon
          className={cn(
            'h-4 w-4',
            isPrimary ? 'text-white/70' : 'text-[var(--color-muted)]'
          )}
        />
      </Button>
    </Link>
  );
}

// Icon components
function ModelsIcon() {
  return (
    <svg
      className="h-4 w-4 text-white"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
      />
    </svg>
  );
}

function UserPlusIcon() {
  return (
    <svg
      className="h-4 w-4 text-white"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"
      />
    </svg>
  );
}

function DownloadIcon() {
  return (
    <svg
      className="h-4 w-4 text-[var(--color-accent)]"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
      />
    </svg>
  );
}

function ClipboardIcon() {
  return (
    <svg
      className="h-4 w-4 text-[var(--color-accent)]"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01"
      />
    </svg>
  );
}

function SettingsIcon() {
  return (
    <svg
      className="h-4 w-4 text-[var(--color-muted)]"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
      />
    </svg>
  );
}

function ChevronRightIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 5l7 7-7 7"
      />
    </svg>
  );
}
