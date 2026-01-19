"use client";

import { useState, useEffect, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Form";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ActivityItem } from "@/types";

// Icons
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

const SearchIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.35-4.35" />
  </svg>
);

const RefreshIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8" />
    <path d="M21 3v5h-5" />
  </svg>
);

const FilterIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3" />
  </svg>
);

// Action type badge colors
function getActionBadgeClass(action: string): string {
  switch (action.toLowerCase()) {
    case "create":
      return "bg-green-500/10 text-green-400 border-green-500/20";
    case "update":
      return "bg-blue-500/10 text-blue-400 border-blue-500/20";
    case "delete":
      return "bg-red-500/10 text-red-400 border-red-500/20";
    case "login":
      return "bg-purple-500/10 text-purple-400 border-purple-500/20";
    case "logout":
      return "bg-gray-500/10 text-gray-400 border-gray-500/20";
    case "export":
      return "bg-yellow-500/10 text-yellow-400 border-yellow-500/20";
    default:
      return "bg-[var(--color-muted)]/10 text-[var(--color-muted)] border-[var(--color-border)]";
  }
}

// Format timestamp
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: date.getFullYear() !== now.getFullYear() ? "numeric" : undefined,
  });
}

// Format full timestamp for tooltip
function formatFullTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  });
}

export default function AuditPage() {
  const [entries, setEntries] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [actionFilter, setActionFilter] = useState<string>("");
  const [modelFilter, setModelFilter] = useState<string>("");
  const [showFilters, setShowFilters] = useState(false);

  const fetchAuditLog = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getActivity(200);
      setEntries(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAuditLog();
  }, [fetchAuditLog]);

  // Get unique values for filters
  const uniqueActions = [...new Set(entries.map((e) => e.action))].sort();
  const uniqueModels = [...new Set(entries.map((e) => e.model).filter(Boolean))].sort();

  // Filter entries
  const filteredEntries = entries.filter((entry) => {
    const matchesSearch =
      !searchTerm ||
      entry.model?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.user?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      entry.action.toLowerCase().includes(searchTerm.toLowerCase()) ||
      String(entry.record_id).includes(searchTerm);

    const matchesAction = !actionFilter || entry.action === actionFilter;
    const matchesModel = !modelFilter || entry.model === modelFilter;

    return matchesSearch && matchesAction && matchesModel;
  });

  const hasActiveFilters = actionFilter || modelFilter || searchTerm;

  const clearFilters = () => {
    setSearchTerm("");
    setActionFilter("");
    setModelFilter("");
  };

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
            <CardHeader>
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div className="flex items-center gap-3">
                  <ClipboardIcon className="h-5 w-5 text-[var(--color-accent)]" />
                  <div>
                    <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                      Activity History
                    </h2>
                    <p className="text-sm text-[var(--color-muted)]">
                      {filteredEntries.length} {filteredEntries.length === 1 ? "entry" : "entries"}
                      {hasActiveFilters ? " (filtered)" : ""}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setShowFilters(!showFilters)}
                    className={cn(showFilters && "bg-[var(--color-card-hover)]")}
                  >
                    <FilterIcon className="h-4 w-4 mr-2" />
                    Filters
                    {hasActiveFilters && (
                      <span className="ml-1.5 px-1.5 py-0.5 text-xs rounded-full bg-[var(--color-primary)] text-white">
                        {[actionFilter, modelFilter, searchTerm].filter(Boolean).length}
                      </span>
                    )}
                  </Button>
                  <Button variant="ghost" size="sm" onClick={fetchAuditLog} disabled={loading}>
                    <RefreshIcon className={cn("h-4 w-4", loading && "animate-spin")} />
                  </Button>
                </div>
              </div>

              {/* Filters Panel */}
              {showFilters && (
                <div className="mt-4 pt-4 border-t border-[var(--color-border)]">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {/* Search */}
                    <div className="relative">
                      <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--color-muted)]" />
                      <Input
                        type="text"
                        placeholder="Search..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-9"
                      />
                    </div>

                    {/* Action Filter */}
                    <select
                      value={actionFilter}
                      onChange={(e) => setActionFilter(e.target.value)}
                      className={cn(
                        "w-full px-3 py-2 rounded-md border transition-colors text-sm",
                        "bg-[var(--color-background)] border-[var(--color-border)]",
                        "text-[var(--color-foreground)]",
                        "focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50",
                      )}
                    >
                      <option value="">All Actions</option>
                      {uniqueActions.map((action) => (
                        <option key={action} value={action}>
                          {action.charAt(0).toUpperCase() + action.slice(1)}
                        </option>
                      ))}
                    </select>

                    {/* Model Filter */}
                    <select
                      value={modelFilter}
                      onChange={(e) => setModelFilter(e.target.value)}
                      className={cn(
                        "w-full px-3 py-2 rounded-md border transition-colors text-sm",
                        "bg-[var(--color-background)] border-[var(--color-border)]",
                        "text-[var(--color-foreground)]",
                        "focus:outline-none focus:ring-2 focus:ring-[var(--color-primary)]/50",
                      )}
                    >
                      <option value="">All Models</option>
                      {uniqueModels.map((model) => (
                        <option key={model} value={model}>
                          {model}
                        </option>
                      ))}
                    </select>
                  </div>

                  {hasActiveFilters && (
                    <div className="mt-3 flex justify-end">
                      <Button variant="ghost" size="sm" onClick={clearFilters}>
                        Clear Filters
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </CardHeader>

            <CardBody className="p-0">
              {loading && entries.length === 0 ? (
                <div className="py-16 text-center">
                  <RefreshIcon className="h-8 w-8 mx-auto mb-4 text-[var(--color-muted)] animate-spin" />
                  <p className="text-sm text-[var(--color-muted)]">Loading audit log...</p>
                </div>
              ) : error ? (
                <div className="py-16 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/10 flex items-center justify-center">
                    <ClipboardIcon className="h-8 w-8 text-red-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                    Failed to Load
                  </h3>
                  <p className="text-sm text-[var(--color-muted)] mb-4">{error}</p>
                  <Button variant="secondary" size="sm" onClick={fetchAuditLog}>
                    Try Again
                  </Button>
                </div>
              ) : filteredEntries.length === 0 ? (
                <div className="py-16 text-center">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--color-card-hover)] flex items-center justify-center">
                    <ClipboardIcon className="h-8 w-8 text-[var(--color-muted)]" />
                  </div>
                  <h3 className="text-lg font-semibold text-[var(--color-foreground)] mb-2">
                    {hasActiveFilters ? "No Matching Entries" : "No Activity Yet"}
                  </h3>
                  <p className="text-sm text-[var(--color-muted)]">
                    {hasActiveFilters
                      ? "Try adjusting your filters to see more results."
                      : "Activity will appear here as users interact with the admin panel."}
                  </p>
                  {hasActiveFilters && (
                    <Button variant="secondary" size="sm" onClick={clearFilters} className="mt-4">
                      Clear Filters
                    </Button>
                  )}
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead>
                      <tr className="border-b border-[var(--color-border)] bg-[var(--color-card-hover)]/50">
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          Time
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          Action
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          Model
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          Record
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          User
                        </th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-[var(--color-muted)] uppercase tracking-wider">
                          Details
                        </th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--color-border)]">
                      {filteredEntries.map((entry, index) => (
                        <tr
                          key={`${entry.timestamp}-${index}`}
                          className="hover:bg-[var(--color-card-hover)] transition-colors"
                        >
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className="text-sm text-[var(--color-foreground)]"
                              title={formatFullTimestamp(entry.timestamp)}
                            >
                              {formatTimestamp(entry.timestamp)}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={cn(
                                "inline-flex items-center px-2 py-1 text-xs font-medium rounded border",
                                getActionBadgeClass(entry.action),
                              )}
                            >
                              {entry.action.charAt(0).toUpperCase() + entry.action.slice(1)}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-sm text-[var(--color-foreground)]">
                              {entry.model || "-"}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-sm font-mono text-[var(--color-muted)]">
                              {entry.record_id ?? "-"}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className="text-sm text-[var(--color-foreground)]">
                              {entry.user || "System"}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            {entry.details && Object.keys(entry.details).length > 0 ? (
                              <details className="group">
                                <summary className="text-sm text-[var(--color-primary)] cursor-pointer hover:underline">
                                  {Object.keys(entry.details).length} field
                                  {Object.keys(entry.details).length !== 1 ? "s" : ""} changed
                                </summary>
                                <div className="mt-2 p-2 bg-[var(--color-background)] rounded text-xs">
                                  <pre className="overflow-x-auto text-[var(--color-muted)]">
                                    {JSON.stringify(entry.details, null, 2)}
                                  </pre>
                                </div>
                              </details>
                            ) : (
                              <span className="text-sm text-[var(--color-muted)]">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardBody>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
