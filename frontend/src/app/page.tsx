"use client";

import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { StatsRow, ActivityFeed, QuickActions, ModelOverview } from "@/components/dashboard";
import { useDashboardStats, useActivity, useModels } from "@/hooks/useApi";

/**
 * Dashboard page - the main landing page for the admin panel.
 * Displays stats, recent activity, quick actions, and model overview.
 */
export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  // Fetch dashboard data
  const { data: stats, isLoading: isLoadingStats } = useDashboardStats();

  const { data: activities, isLoading: isLoadingActivity } = useActivity(10);

  const { data: models, isLoading: isLoadingModels } = useModels();

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page header */}
        <PageHeader
          title="Dashboard"
          subtitle="Overview of your admin panel"
          showBreadcrumbs={false}
        />

        {/* Stats row */}
        <StatsRow
          stats={stats?.models}
          totalRecords={stats?.total_records}
          totalModels={stats?.total_models}
          isLoading={isLoadingStats}
        />

        {/* Main content grid */}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Activity feed - 2 cols */}
          <div className="lg:col-span-2">
            <ActivityFeed activities={activities} isLoading={isLoadingActivity} maxItems={10} />
          </div>

          {/* Quick actions - 1 col */}
          <div>
            <QuickActions />
          </div>
        </div>

        {/* Model overview grid */}
        <ModelOverview
          models={stats?.models ?? convertModelsToStats(models)}
          isLoading={isLoadingStats || isLoadingModels}
          maxModels={6}
        />
      </div>
    </MainLayout>
  );
}

/**
 * Converts ModelInfo array to ModelStats array for ModelOverview.
 * This is used as a fallback when stats are not yet loaded.
 */
function convertModelsToStats(
  models?: readonly import("@/types").ModelInfo[],
): import("@/types").ModelStats[] {
  if (!models) return [];

  return models.map((model) => ({
    name: model.name,
    model_name: model.model_name,
    count: 0,
    icon: model.icon,
    category: model.category,
  }));
}
