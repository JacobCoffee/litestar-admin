'use client';

import { MainLayout } from '@/components/layout/MainLayout';
import { Card, CardBody } from '@/components/ui/Card';
import { Skeleton, SkeletonTable } from '@/components/ui/Loading';
import { cn } from '@/lib/utils';

/**
 * Loading skeleton for the Model List Page.
 * Displays a consistent loading state while data is being fetched.
 */
export default function ModelListLoading() {

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header Skeleton */}
        <div className="space-y-4">
          {/* Breadcrumb skeleton */}
          <div className="flex items-center gap-2">
            <Skeleton variant="rectangular" width={16} height={16} />
            <Skeleton variant="text" width={60} />
            <Skeleton variant="text" width={60} />
            <Skeleton variant="text" width={80} />
          </div>

          {/* Title row skeleton */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="space-y-2">
              <Skeleton variant="text" width={200} height={28} />
              <Skeleton variant="text" width={100} height={16} />
            </div>
            <div className="flex items-center gap-3">
              <Skeleton variant="rectangular" width={80} height={36} />
              <Skeleton variant="rectangular" width={140} height={36} />
            </div>
          </div>
        </div>

        {/* Search and Filter Card Skeleton */}
        <Card>
          <CardBody className="py-4">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Skeleton variant="rectangular" className="flex-1" height={40} />
              <div className="flex items-center gap-2">
                <Skeleton variant="rectangular" width={100} height={36} />
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Data Table Skeleton */}
        <Card>
          <SkeletonTable rows={10} columns={6} showHeader />
        </Card>

        {/* Pagination Skeleton */}
        <div
          className={cn(
            'flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between',
            'px-4 py-3',
            'border-t border-[var(--color-border)]',
            'bg-[var(--color-card)]/50',
            'rounded-b-[var(--radius-lg)]'
          )}
        >
          <Skeleton variant="text" width={180} />
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Skeleton variant="text" width={70} />
              <Skeleton variant="rectangular" width={60} height={32} />
            </div>
            <div className="flex items-center gap-1">
              <Skeleton variant="rectangular" width={36} height={36} />
              <Skeleton variant="text" width={80} />
              <Skeleton variant="rectangular" width={36} height={36} />
            </div>
          </div>
        </div>
      </div>
    </MainLayout>
  );
}
