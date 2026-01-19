'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardBody } from '@/components/ui/Card';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';

const UserIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

export default function ProfilePage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Profile"
            subtitle="Manage your account settings"
            breadcrumbs={[
              { label: 'Dashboard', href: '/' },
              { label: 'Profile' },
            ]}
          />

          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <UserIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                Coming Soon
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Profile management will be available in a future update.
              </p>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
