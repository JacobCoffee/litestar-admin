'use client';

import { useEffect } from 'react';
import Link from 'next/link';

import { MainLayout } from '@/components/layout/MainLayout';
import { PageHeader } from '@/components/layout/PageHeader';
import type { BreadcrumbItem } from '@/components/layout/Breadcrumb';
import { Card, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

// ============================================================================
// Icons
// ============================================================================

const AlertTriangleIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    <line x1="12" y1="9" x2="12" y2="13" />
    <line x1="12" y1="17" x2="12.01" y2="17" />
  </svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M23 4v6h-6" />
    <path d="M1 20v-6h6" />
    <path d="M3.51 9a9 9 0 0114.85-3.36L23 10" />
    <path d="M20.49 15a9 9 0 01-14.85 3.36L1 14" />
  </svg>
);

const HomeIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
    <polyline points="9,22 9,12 15,12 15,22" />
  </svg>
);

// ============================================================================
// Types
// ============================================================================

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

// ============================================================================
// Component
// ============================================================================

/**
 * Error boundary page for the Model List route.
 * Displays a user-friendly error message with recovery options.
 */
export default function ModelListError({ error, reset }: ErrorProps) {
  // Log the error to an error reporting service in production
  useEffect(() => {
    console.error('Model list error:', error);
  }, [error]);

  const breadcrumbs: BreadcrumbItem[] = [
    { label: 'Dashboard', href: '/' },
    { label: 'Models', href: '/models' },
    { label: 'Error' },
  ];

  // Determine the error message to display
  const errorMessage = getErrorMessage(error);
  const errorTitle = getErrorTitle(error);

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Error"
          subtitle="Something went wrong"
          breadcrumbs={breadcrumbs}
        />

        <Card>
          <CardBody>
            <div className="flex flex-col items-center justify-center py-12 text-center">
              {/* Error Icon */}
              <div
                className={cn(
                  'w-20 h-20 mb-6 rounded-full',
                  'bg-[var(--color-error)]/10',
                  'flex items-center justify-center'
                )}
              >
                <AlertTriangleIcon className="h-10 w-10 text-[var(--color-error)]" />
              </div>

              {/* Error Title */}
              <h2 className="text-xl font-semibold text-[var(--color-foreground)] mb-2">
                {errorTitle}
              </h2>

              {/* Error Message */}
              <p className="text-sm text-[var(--color-muted)] mb-8 max-w-md">
                {errorMessage}
              </p>

              {/* Error Details (development only) */}
              {process.env.NODE_ENV === 'development' && error.message && (
                <div
                  className={cn(
                    'w-full max-w-lg mb-8 p-4',
                    'rounded-[var(--radius-md)]',
                    'bg-[var(--color-card-hover)]',
                    'border border-[var(--color-border)]',
                    'text-left'
                  )}
                >
                  <p className="text-xs font-mono text-[var(--color-error)] break-all">
                    {error.message}
                  </p>
                  {error.digest && (
                    <p className="text-xs font-mono text-[var(--color-muted)] mt-2">
                      Digest: {error.digest}
                    </p>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center gap-3">
                <Button
                  variant="primary"
                  onClick={reset}
                  leftIcon={<RefreshIcon className="h-4 w-4" />}
                >
                  Try Again
                </Button>
                <Link href="/">
                  <Button
                    variant="secondary"
                    leftIcon={<HomeIcon className="h-4 w-4" />}
                  >
                    Back to Dashboard
                  </Button>
                </Link>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Help Section */}
        <Card>
          <CardBody>
            <h3 className="text-sm font-medium text-[var(--color-foreground)] mb-3">
              What you can try:
            </h3>
            <ul className="space-y-2 text-sm text-[var(--color-muted)]">
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)] mt-1">1.</span>
                <span>
                  Click "Try Again" to reload the page. Sometimes a temporary issue
                  can be resolved by refreshing.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)] mt-1">2.</span>
                <span>
                  Check your network connection. Make sure you are connected to the
                  internet.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)] mt-1">3.</span>
                <span>
                  If the problem persists, try clearing your browser cache or using
                  a different browser.
                </span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-[var(--color-primary)] mt-1">4.</span>
                <span>
                  Contact your administrator if you continue to experience issues.
                </span>
              </li>
            </ul>
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Determines a user-friendly error title based on the error type.
 */
function getErrorTitle(error: Error): string {
  const message = error.message.toLowerCase();

  if (message.includes('network') || message.includes('fetch')) {
    return 'Connection Error';
  }

  if (message.includes('unauthorized') || message.includes('401')) {
    return 'Authentication Required';
  }

  if (message.includes('forbidden') || message.includes('403')) {
    return 'Access Denied';
  }

  if (message.includes('not found') || message.includes('404')) {
    return 'Model Not Found';
  }

  if (message.includes('timeout')) {
    return 'Request Timeout';
  }

  if (message.includes('server') || message.includes('500')) {
    return 'Server Error';
  }

  return 'Something Went Wrong';
}

/**
 * Determines a user-friendly error message based on the error type.
 */
function getErrorMessage(error: Error): string {
  const message = error.message.toLowerCase();

  if (message.includes('network') || message.includes('fetch')) {
    return 'Unable to connect to the server. Please check your internet connection and try again.';
  }

  if (message.includes('unauthorized') || message.includes('401')) {
    return 'Your session may have expired. Please log in again to continue.';
  }

  if (message.includes('forbidden') || message.includes('403')) {
    return 'You do not have permission to access this resource. Contact your administrator if you believe this is an error.';
  }

  if (message.includes('not found') || message.includes('404')) {
    return 'The requested model could not be found. It may have been removed or renamed.';
  }

  if (message.includes('timeout')) {
    return 'The request took too long to complete. The server may be experiencing high load. Please try again.';
  }

  if (message.includes('server') || message.includes('500')) {
    return 'The server encountered an unexpected error. Our team has been notified and is working on a fix.';
  }

  return 'An unexpected error occurred while loading the data. Please try again or contact support if the problem persists.';
}
