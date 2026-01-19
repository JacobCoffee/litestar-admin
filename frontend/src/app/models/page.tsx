'use client';

import { Suspense } from 'react';
import { useSearchParams, usePathname } from 'next/navigation';
import Link from 'next/link';
import { ModelListPage } from '@/components/pages/ModelListPage';
import { RecordDetailPage } from '@/components/pages/RecordDetailPage';
import { CreateRecordPage } from '@/components/pages/CreateRecordPage';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardBody } from '@/components/ui/Card';
import { PageHeader } from '@/components/layout/PageHeader';
import { Spinner, Skeleton } from '@/components/ui/Loading';
import { useModels } from '@/hooks/useApi';
import { cn } from '@/lib/utils';

/**
 * Models page - handles all model-related routes client-side.
 *
 * Supports both path-based and query param routing:
 *
 * Path-based (preferred for navigation):
 * - /models - Models index
 * - /models/User - User model list
 * - /models/User/create - Create new User
 * - /models/User/123 - User record detail
 *
 * Query params (fallback):
 * - /models?model=User - Model list page
 * - /models?model=User&action=new - Create new record
 * - /models?model=User&id=123 - Record detail page
 *
 * This approach enables static export while maintaining SPA-style navigation.
 */
export default function ModelsPage() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <ModelsContent />
    </Suspense>
  );
}

interface PathParams {
  model: string | null;
  id: string | null;
  action: string | null;
}

/**
 * Parse route parameters from pathname.
 * Handles paths like /models/User, /models/User/create, /models/User/123
 * Also handles basePath prefix: /admin/models/User
 */
function parsePathParams(pathname: string): PathParams {
  // Remove basePath (/admin) and /models prefix
  // usePathname() may or may not include basePath in static export
  const normalizedPath = pathname
    .replace(/^\/admin/, '') // Remove basePath if present
    .replace(/^\/models\/?/, ''); // Remove /models prefix

  if (!normalizedPath) return { model: null, id: null, action: null };

  const segments = normalizedPath.split('/').filter(Boolean);
  if (segments.length === 0) return { model: null, id: null, action: null };

  const model = segments[0] ?? null;
  const secondSegment = segments[1];

  if (!secondSegment) {
    return { model, id: null, action: null };
  }

  // Check if second segment is 'create' action or a record ID
  if (secondSegment === 'create') {
    return { model, id: null, action: 'new' };
  }

  // Otherwise it's a record ID
  return { model, id: secondSegment, action: null };
}

function ModelsContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  // First try to parse from pathname (path-based routing)
  const pathParams = parsePathParams(pathname);

  // Fall back to query params if not in path
  const model = pathParams.model ?? searchParams.get('model');
  const id = pathParams.id ?? searchParams.get('id');
  const action = pathParams.action ?? searchParams.get('action');

  // If no model is specified, show the index page
  if (!model) {
    return <ModelsIndexPage />;
  }

  // Create new record
  if (action === 'new') {
    return <CreateRecordPage model={model} />;
  }

  // Show record detail
  if (id) {
    return <RecordDetailPage model={model} id={id} />;
  }

  // Show model list
  return <ModelListPage model={model} />;
}

function LoadingFallback() {
  return (
    <MainLayout>
      <div className="flex items-center justify-center min-h-[400px]">
        <Spinner size="lg" />
      </div>
    </MainLayout>
  );
}

// Icon for model cards
const TableIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="3" y="3" width="18" height="18" rx="2" />
    <path d="M3 9h18" />
    <path d="M3 15h18" />
    <path d="M9 3v18" />
  </svg>
);

const ChevronRightIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M9 18l6-6-6-6" />
  </svg>
);

/**
 * Models index page - shows when navigating to /models without params
 */
function ModelsIndexPage() {
  const { data: models, isLoading, error } = useModels();

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Models"
          subtitle="Browse and manage your database models"
          breadcrumbs={[
            { label: 'Dashboard', href: '/' },
            { label: 'Models' },
          ]}
        />

        {/* Loading state */}
        {isLoading && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[...Array(6)].map((_, i) => (
              <Card key={i}>
                <CardBody className="p-4">
                  <Skeleton className="h-12 w-12 rounded-lg mb-3" />
                  <Skeleton className="h-5 w-24 mb-2" />
                  <Skeleton className="h-4 w-32" />
                </CardBody>
              </Card>
            ))}
          </div>
        )}

        {/* Error state */}
        {error && (
          <Card>
            <CardBody className="py-12 text-center">
              <p className="text-[var(--color-error)]">
                Failed to load models: {error.message}
              </p>
            </CardBody>
          </Card>
        )}

        {/* Models grid */}
        {!isLoading && !error && models && models.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {models.map((model) => (
              <Link
                key={model.model_name}
                href={`/models/${model.model_name}`}
                className="group"
              >
                <Card className="h-full transition-all duration-150 hover:border-[var(--color-primary)] hover:shadow-md">
                  <CardBody className="p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            'flex h-12 w-12 items-center justify-center rounded-lg',
                            'bg-[var(--color-primary)]/10 text-[var(--color-primary)]'
                          )}
                        >
                          <TableIcon className="h-6 w-6" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-[var(--color-foreground)] group-hover:text-[var(--color-primary)]">
                            {model.name}
                          </h3>
                          <p className="text-sm text-[var(--color-muted)]">
                            {model.model_name}
                          </p>
                        </div>
                      </div>
                      <ChevronRightIcon
                        className={cn(
                          'h-5 w-5 text-[var(--color-muted)]',
                          'transition-transform group-hover:translate-x-1 group-hover:text-[var(--color-primary)]'
                        )}
                      />
                    </div>
                    {model.category && (
                      <div className="mt-3">
                        <span
                          className={cn(
                            'inline-flex items-center rounded-full px-2 py-0.5',
                            'text-xs font-medium',
                            'bg-[var(--color-card-hover)] text-[var(--color-muted)]'
                          )}
                        >
                          {model.category}
                        </span>
                      </div>
                    )}
                  </CardBody>
                </Card>
              </Link>
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && (!models || models.length === 0) && (
          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <TableIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                No Models Registered
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Register your SQLAlchemy models with the admin panel to manage them here.
              </p>
            </CardBody>
          </Card>
        )}
      </div>
    </MainLayout>
  );
}
