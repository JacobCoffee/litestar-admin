'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody } from '@/components/ui/Card';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const DownloadIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
);

export default function ExportPage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Export Data"
            subtitle="Export your data in various formats"
            breadcrumbs={[
              { label: 'Dashboard', href: '/' },
              { label: 'Export' },
            ]}
          />

          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <DownloadIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                Coming Soon
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Bulk data export will be available in a future update.
                Individual model exports are available from the model list page.
              </p>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
