'use client';

import { Suspense } from 'react';
import { useSearchParams, usePathname } from 'next/navigation';
import { ModelListPage } from '@/components/pages/ModelListPage';
import { RecordDetailPage } from '@/components/pages/RecordDetailPage';
import { CreateRecordPage } from '@/components/pages/CreateRecordPage';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardBody } from '@/components/ui/Card';
import { PageHeader } from '@/components/layout/PageHeader';
import { Spinner } from '@/components/ui/Loading';

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

/**
 * Models index page - shows when navigating to /models without params
 */
function ModelsIndexPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Models"
          subtitle="Select a model from the sidebar to view its records"
          breadcrumbs={[
            { label: 'Dashboard', href: '/' },
            { label: 'Models' },
          ]}
        />

        <Card>
          <CardBody className="py-16 text-center">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
              <svg
                className="h-8 w-8 text-[var(--color-muted)]"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <rect x="3" y="3" width="7" height="7" />
                <rect x="14" y="3" width="7" height="7" />
                <rect x="14" y="14" width="7" height="7" />
                <rect x="3" y="14" width="7" height="7" />
              </svg>
            </div>
            <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
              Select a Model
            </h2>
            <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
              Use the sidebar navigation to select a model and view its records.
              Each model represents a database table you can browse, search, and manage.
            </p>
          </CardBody>
        </Card>
      </div>
    </MainLayout>
  );
}
