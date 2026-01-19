"use client";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardBody } from "@/components/ui/Card";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";

const ClipboardIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
    <rect x="8" y="2" width="8" height="4" rx="1" ry="1" />
    <path d="M12 11h4" />
    <path d="M12 16h4" />
    <path d="M8 11h.01" />
    <path d="M8 16h.01" />
  </svg>
);

export default function AuditPage() {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Audit Log"
            subtitle="View activity history and changes"
            breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Audit Log" }]}
          />

          <Card>
            <CardBody className="py-16 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                <ClipboardIcon className="h-8 w-8 text-[var(--color-muted)]" />
              </div>
              <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                Coming Soon
              </h2>
              <p className="text-sm text-[var(--color-muted)] max-w-md mx-auto">
                Full audit log viewing will be available in a future update. Activity feed is
                available on the dashboard.
              </p>
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
