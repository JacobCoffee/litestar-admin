'use client';

import type { ReactNode } from 'react';
import Link from 'next/link';
import { Card, CardBody } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Loading';
import { Sparkline, SparklineSkeleton } from './Sparkline';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/utils';
import type { ModelStats } from '@/types';

export interface StatItemProps {
  /** Stat title/label */
  title: string;
  /** Current value */
  value: number | string;
  /** Previous value for trend calculation */
  previousValue?: number;
  /** Override trend direction */
  trend?: 'up' | 'down' | 'neutral';
  /** Override trend percentage */
  trendValue?: number;
  /** Sparkline data points */
  sparklineData?: readonly number[];
  /** Optional icon */
  icon?: ReactNode;
  /** Optional link */
  href?: string;
}

/**
 * A single stat card with value, trend indicator, and optional sparkline.
 */
export function StatItem({
  title,
  value,
  previousValue,
  trend: overrideTrend,
  trendValue: overrideTrendValue,
  sparklineData,
  icon,
  href,
}: StatItemProps) {
  // Calculate trend from previous value if not overridden
  const numericValue = typeof value === 'number' ? value : parseFloat(value) || 0;
  const calculatedChange = previousValue
    ? ((numericValue - previousValue) / (previousValue || 1)) * 100
    : 0;

  const trendValue = overrideTrendValue ?? Math.abs(calculatedChange);
  const trend = overrideTrend ?? (
    calculatedChange > 0 ? 'up' : calculatedChange < 0 ? 'down' : 'neutral'
  );

  const displayValue = typeof value === 'number' ? formatNumber(value) : value;

  const content = (
    <Card
      className={cn(
        'transition-all duration-200',
        href && 'cursor-pointer hover:border-[var(--color-accent)] hover:shadow-md'
      )}
    >
      <CardBody className="flex flex-col gap-4">
        <div className="flex items-start justify-between">
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--color-muted)] truncate">
              {title}
            </p>
            <p className="mt-1 text-2xl font-semibold text-[var(--color-foreground)]">
              {displayValue}
            </p>
          </div>
          {icon && (
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--color-primary)]/10 text-[var(--color-primary)]">
              {icon}
            </div>
          )}
        </div>

        <div className="flex items-center justify-between gap-4">
          {/* Trend indicator */}
          <div className="flex items-center gap-1.5">
            <TrendArrow direction={trend} />
            <span
              className={cn(
                'text-sm font-medium',
                trend === 'up' && 'text-[var(--color-success)]',
                trend === 'down' && 'text-[var(--color-error)]',
                trend === 'neutral' && 'text-[var(--color-muted)]'
              )}
            >
              {trendValue > 0 ? `${trendValue.toFixed(1)}%` : 'No change'}
            </span>
            <span className="text-xs text-[var(--color-muted)]">vs last period</span>
          </div>

          {/* Sparkline */}
          {sparklineData && sparklineData.length > 0 && (
            <Sparkline
              data={sparklineData}
              trend={trend}
              width={80}
              height={24}
            />
          )}
        </div>
      </CardBody>
    </Card>
  );

  if (href) {
    return (
      <Link href={href} className="block">
        {content}
      </Link>
    );
  }

  return content;
}

interface TrendArrowProps {
  direction: 'up' | 'down' | 'neutral';
}

function TrendArrow({ direction }: TrendArrowProps) {
  if (direction === 'neutral') {
    return (
      <svg
        className="h-4 w-4 text-[var(--color-muted)]"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M5 12h14"
        />
      </svg>
    );
  }

  return (
    <svg
      className={cn(
        'h-4 w-4',
        direction === 'up' && 'text-[var(--color-success)]',
        direction === 'down' && 'text-[var(--color-error)] rotate-180'
      )}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M5 10l7-7m0 0l7 7m-7-7v18"
      />
    </svg>
  );
}

export interface StatsRowProps {
  /** Model statistics from API */
  stats?: readonly ModelStats[] | undefined;
  /** Total records count */
  totalRecords?: number | undefined;
  /** Total models count */
  totalModels?: number | undefined;
  /** Whether data is loading */
  isLoading?: boolean;
  /** Additional CSS classes */
  className?: string;
}

/**
 * A row of stat cards showing model counts and trends.
 * Displays aggregate stats plus per-model breakdowns.
 */
export function StatsRow({
  stats,
  totalRecords = 0,
  totalModels = 0,
  isLoading = false,
  className,
}: StatsRowProps) {
  if (isLoading) {
    return <StatsRowSkeleton />;
  }

  // Generate mock sparkline data for demo (in production, this would come from API)
  const generateSparklineData = (count: number): number[] => {
    const baseValue = count / 7;
    return Array.from({ length: 7 }, (_, i) => {
      const variation = (Math.random() - 0.5) * baseValue * 0.4;
      return Math.max(0, Math.floor(baseValue + variation + i * (baseValue * 0.05)));
    });
  };

  return (
    <div className={cn('grid gap-4 sm:grid-cols-2 lg:grid-cols-4', className)}>
      {/* Total Models stat */}
      <StatItem
        title="Total Models"
        value={totalModels}
        trend="neutral"
        icon={<ModelsIcon />}
      />

      {/* Total Records stat */}
      <StatItem
        title="Total Records"
        value={totalRecords}
        sparklineData={generateSparklineData(totalRecords)}
        trend={totalRecords > 0 ? 'up' : 'neutral'}
        trendValue={12.5}
        icon={<RecordsIcon />}
      />

      {/* Show first two model stats if available */}
      {stats?.slice(0, 2).map((model) => (
        <StatItem
          key={model.name}
          title={model.name}
          value={model.count}
          sparklineData={generateSparklineData(model.count)}
          trend={model.count > 0 ? 'up' : 'neutral'}
          trendValue={Math.random() * 15}
          href={`/models/${model.model_name}`}
          icon={<ModelIcon />}
        />
      ))}
    </div>
  );
}

function StatsRowSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <Card key={i}>
          <CardBody className="flex flex-col gap-4">
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <Skeleton variant="text" width="60%" className="mb-2" />
                <Skeleton variant="text" width="40%" height={28} />
              </div>
              <Skeleton variant="circular" width={40} height={40} />
            </div>
            <div className="flex items-center justify-between">
              <Skeleton variant="text" width="50%" />
              <SparklineSkeleton />
            </div>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}

function ModelsIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
      />
    </svg>
  );
}

function RecordsIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
      />
    </svg>
  );
}

function ModelIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
      />
    </svg>
  );
}
