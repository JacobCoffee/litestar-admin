'use client';

import { Skeleton } from '@/components/ui/Loading';
import { Card, CardHeader, CardBody } from '@/components/ui/Card';

/**
 * Loading state for the record detail page.
 * Displays a skeleton layout matching the page structure.
 */
export default function RecordDetailLoading() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="space-y-4">
        <div className="flex items-center gap-2">
          <Skeleton variant="text" width={80} height={16} />
          <Skeleton variant="text" width={16} height={16} />
          <Skeleton variant="text" width={100} height={16} />
          <Skeleton variant="text" width={16} height={16} />
          <Skeleton variant="text" width={60} height={16} />
        </div>
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton variant="text" width={200} height={28} />
            <Skeleton variant="text" width={120} height={16} />
          </div>
          <div className="flex gap-3">
            <Skeleton variant="rectangular" width={100} height={36} />
            <Skeleton variant="rectangular" width={80} height={36} />
            <Skeleton variant="rectangular" width={80} height={36} />
          </div>
        </div>
      </div>

      {/* Content skeleton */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <Skeleton variant="text" width="30%" height={20} />
            </CardHeader>
            <CardBody>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="space-y-2">
                    <Skeleton variant="text" width="40%" height={14} />
                    <Skeleton variant="text" width="70%" height={18} />
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Related records skeleton */}
          <Card>
            <CardHeader>
              <Skeleton variant="text" width="50%" height={16} />
            </CardHeader>
            <CardBody>
              <div className="space-y-3">
                <Skeleton variant="text" width="80%" />
                <Skeleton variant="text" width="60%" />
              </div>
            </CardBody>
          </Card>

          {/* Audit log skeleton */}
          <Card>
            <CardHeader>
              <Skeleton variant="text" width="40%" height={16} />
            </CardHeader>
            <CardBody>
              <div className="space-y-4">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="flex gap-3">
                    <Skeleton variant="circular" width={32} height={32} />
                    <div className="flex-1 space-y-2">
                      <Skeleton variant="text" width="60%" />
                      <Skeleton variant="text" width="40%" />
                    </div>
                  </div>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  );
}
