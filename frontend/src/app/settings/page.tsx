'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody } from '@/components/ui/Card';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const SettingsIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="12" cy="12" r="3" />
    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z" />
  </svg>
);

export default function SettingsPage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Settings"
            subtitle="Configure your admin panel preferences"
            breadcrumbs={[
              { label: 'Dashboard', href: '/' },
              { label: 'Settings' },
            ]}
          />

          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <SettingsIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                Coming Soon
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Settings configuration will be available in a future update.
              </p>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
