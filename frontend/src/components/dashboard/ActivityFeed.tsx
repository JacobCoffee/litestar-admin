"use client";

import Link from "next/link";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Loading";
import { cn } from "@/lib/utils";
import type { ActivityItem } from "@/types";

export interface ActivityFeedProps {
  /** List of activity items */
  activities?: readonly ActivityItem[] | undefined;
  /** Whether data is loading */
  isLoading?: boolean;
  /** Maximum number of items to display */
  maxItems?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Displays a feed of recent activity/audit log entries.
 * Shows create, update, and delete actions with timestamps.
 */
export function ActivityFeed({
  activities,
  isLoading = false,
  maxItems = 10,
  className,
}: ActivityFeedProps) {
  if (isLoading) {
    return <ActivityFeedSkeleton count={5} />;
  }

  const displayActivities = activities?.slice(0, maxItems) ?? [];

  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-[var(--color-foreground)]">
            Recent Activity
          </h2>
          <p className="mt-0.5 text-sm text-[var(--color-muted)]">
            Latest changes across all models
          </p>
        </div>
        <Link
          href="/audit"
          className="text-sm font-medium text-[var(--color-accent)] hover:text-[var(--color-accent)]/80"
        >
          View all
        </Link>
      </CardHeader>
      <CardBody className="p-0">
        {displayActivities.length === 0 ? (
          <EmptyActivityState />
        ) : (
          <ul className="divide-y divide-[var(--color-border)]">
            {displayActivities.map((activity, index) => (
              <ActivityRow
                key={`${activity.model}-${activity.record_id}-${index}`}
                activity={activity}
              />
            ))}
          </ul>
        )}
      </CardBody>
    </Card>
  );
}

interface ActivityRowProps {
  activity: ActivityItem;
}

function ActivityRow({ activity }: ActivityRowProps) {
  const relativeTime = getRelativeTime(activity.timestamp);
  const actionConfig = getActionConfig(activity.action);

  return (
    <li className="flex items-start gap-4 px-6 py-4 hover:bg-[var(--color-card-hover)] transition-colors">
      {/* Action icon */}
      <div
        className={cn(
          "mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          actionConfig.bgColor,
        )}
      >
        <actionConfig.Icon className={cn("h-4 w-4", actionConfig.iconColor)} />
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[var(--color-foreground)]">
          <span className="font-medium">{activity.user ?? "System"}</span>
          <span className="text-[var(--color-muted)]"> {actionConfig.verb} </span>
          <Link
            href={`/models/${activity.model}${activity.record_id ? `/${activity.record_id}` : ""}`}
            className="font-medium text-[var(--color-accent)] hover:underline"
          >
            {activity.model}
            {activity.record_id && ` #${activity.record_id}`}
          </Link>
        </p>
        {activity.details && Object.keys(activity.details).length > 0 && (
          <p className="mt-0.5 text-xs text-[var(--color-muted)] truncate">
            {formatDetails(activity.details)}
          </p>
        )}
      </div>

      {/* Timestamp */}
      <time
        dateTime={activity.timestamp}
        className="shrink-0 text-xs text-[var(--color-muted)]"
        title={new Date(activity.timestamp).toLocaleString()}
      >
        {relativeTime}
      </time>
    </li>
  );
}

function EmptyActivityState() {
  return (
    <div className="flex flex-col items-center justify-center px-6 py-12 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--color-card-hover)]">
        <ActivityIcon className="h-6 w-6 text-[var(--color-muted)]" />
      </div>
      <p className="mt-4 text-sm font-medium text-[var(--color-foreground)]">No recent activity</p>
      <p className="mt-1 text-sm text-[var(--color-muted)]">
        Activity will appear here when changes are made
      </p>
    </div>
  );
}

interface ActivityFeedSkeletonProps {
  count?: number;
}

function ActivityFeedSkeleton({ count = 5 }: ActivityFeedSkeletonProps) {
  return (
    <Card>
      <CardHeader>
        <Skeleton variant="text" width="40%" height={20} />
        <Skeleton variant="text" width="60%" height={16} className="mt-1" />
      </CardHeader>
      <CardBody className="p-0">
        <ul className="divide-y divide-[var(--color-border)]">
          {Array.from({ length: count }).map((_, i) => (
            <li key={i} className="flex items-start gap-4 px-6 py-4">
              <Skeleton variant="circular" width={32} height={32} />
              <div className="flex-1">
                <Skeleton variant="text" width="70%" />
                <Skeleton variant="text" width="40%" className="mt-1" />
              </div>
              <Skeleton variant="text" width={60} />
            </li>
          ))}
        </ul>
      </CardBody>
    </Card>
  );
}

// Action configuration for icons and colors
type ActionType = "create" | "update" | "delete" | string;

interface ActionConfig {
  Icon: React.FC<{ className?: string }>;
  verb: string;
  bgColor: string;
  iconColor: string;
}

function getActionConfig(action: ActionType): ActionConfig {
  switch (action.toLowerCase()) {
    case "create":
      return {
        Icon: CreateIcon,
        verb: "created",
        bgColor: "bg-[var(--color-success)]/10",
        iconColor: "text-[var(--color-success)]",
      };
    case "update":
      return {
        Icon: UpdateIcon,
        verb: "updated",
        bgColor: "bg-[var(--color-accent)]/10",
        iconColor: "text-[var(--color-accent)]",
      };
    case "delete":
      return {
        Icon: DeleteIcon,
        verb: "deleted",
        bgColor: "bg-[var(--color-error)]/10",
        iconColor: "text-[var(--color-error)]",
      };
    default:
      return {
        Icon: ActivityIcon,
        verb: action,
        bgColor: "bg-[var(--color-muted)]/10",
        iconColor: "text-[var(--color-muted)]",
      };
  }
}

function getRelativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "Just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  }
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  }
  if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  }
  return then.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function formatDetails(details: Record<string, unknown>): string {
  const entries = Object.entries(details);
  if (entries.length === 0) return "";

  return entries
    .slice(0, 3)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(", ");
}

// Icon components
function CreateIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
    </svg>
  );
}

function UpdateIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"
      />
    </svg>
  );
}

function DeleteIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
      />
    </svg>
  );
}

function ActivityIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}
