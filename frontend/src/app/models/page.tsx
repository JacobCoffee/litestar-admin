'use client';

import { Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { ModelListPage } from '@/components/pages/ModelListPage';
import { RecordDetailPage } from '@/components/pages/RecordDetailPage';
import { CreateRecordPage } from '@/components/pages/CreateRecordPage';
import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardBody } from '@/components/ui/Card';
import { PageHeader } from '@/components/layout/PageHeader';
import { Spinner } from '@/components/ui/Loading';

/**
 * Models page - handles all model-related routes client-side via query params.
 *
 * URL structure:
 * - /models - Models index
 * - /models?model=users - Model list page
 * - /models?model=users&action=new - Create new record
 * - /models?model=users&id=123 - Record detail page
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

function ModelsContent() {
  const searchParams = useSearchParams();

  const model = searchParams.get('model');
  const id = searchParams.get('id');
  const action = searchParams.get('action');

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
