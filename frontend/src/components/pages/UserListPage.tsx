"use client";

import { useState, useCallback, useMemo } from "react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useUsers, useDeleteUser, useActivateUser, useDeactivateUser } from "@/hooks/useApi";
import { DataTable, type Column } from "@/components/data/DataTable";
import { SearchFilter, type FilterState } from "@/components/data/SearchFilter";
import { Button } from "@/components/ui/Button";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { UserStatusBadge, RoleBadge } from "@/components/users/UserStatusBadge";
import type { UserResponse, UserListParams } from "@/types";

// ============================================================================
// Icons
// ============================================================================

function PlusIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="12" y1="5" x2="12" y2="19" />
      <line x1="5" y1="12" x2="19" y2="12" />
    </svg>
  );
}

function UsersIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="9" cy="7" r="4" />
      <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
      <path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}

function EditIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}

function TrashIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="3,6 5,6 21,6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <line x1="10" y1="11" x2="10" y2="17" />
      <line x1="14" y1="11" x2="14" y2="17" />
    </svg>
  );
}

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="20,6 9,17 4,12" />
    </svg>
  );
}

function XIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function MoreVerticalIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="1" />
      <circle cx="12" cy="5" r="1" />
      <circle cx="12" cy="19" r="1" />
    </svg>
  );
}

// ============================================================================
// Action Dropdown Component
// ============================================================================

interface UserActionDropdownProps {
  user: UserResponse;
  onEdit: () => void;
  onDelete: () => void;
  onActivate: () => void;
  onDeactivate: () => void;
}

function UserActionDropdown({
  user,
  onEdit,
  onDelete,
  onActivate,
  onDeactivate,
}: UserActionDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "p-1.5 rounded-[var(--radius-md)]",
          "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
          "hover:bg-[var(--color-card-hover)]",
          "transition-colors duration-150",
        )}
        aria-label="Actions"
      >
        <MoreVerticalIcon className="h-4 w-4" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
            aria-hidden="true"
          />
          <div
            className={cn(
              "absolute right-0 top-full z-50 mt-1",
              "min-w-[160px] py-1",
              "rounded-[var(--radius-md)]",
              "border border-[var(--color-border)]",
              "bg-[var(--color-card)]",
              "shadow-lg shadow-black/20",
            )}
          >
            <button
              type="button"
              onClick={() => {
                onEdit();
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-3 py-2",
                "flex items-center gap-2",
                "text-sm text-left text-[var(--color-foreground)]",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
              )}
            >
              <EditIcon className="h-4 w-4" />
              Edit
            </button>

            {user.is_active ? (
              <button
                type="button"
                onClick={() => {
                  onDeactivate();
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full px-3 py-2",
                  "flex items-center gap-2",
                  "text-sm text-left text-[var(--color-warning)]",
                  "hover:bg-[var(--color-card-hover)]",
                  "transition-colors duration-150",
                )}
              >
                <XIcon className="h-4 w-4" />
                Deactivate
              </button>
            ) : (
              <button
                type="button"
                onClick={() => {
                  onActivate();
                  setIsOpen(false);
                }}
                className={cn(
                  "w-full px-3 py-2",
                  "flex items-center gap-2",
                  "text-sm text-left text-[var(--color-success)]",
                  "hover:bg-[var(--color-card-hover)]",
                  "transition-colors duration-150",
                )}
              >
                <CheckIcon className="h-4 w-4" />
                Activate
              </button>
            )}

            <div className="my-1 border-t border-[var(--color-border)]" />

            <button
              type="button"
              onClick={() => {
                onDelete();
                setIsOpen(false);
              }}
              className={cn(
                "w-full px-3 py-2",
                "flex items-center gap-2",
                "text-sm text-left text-[var(--color-error)]",
                "hover:bg-[var(--color-error)]/10",
                "transition-colors duration-150",
              )}
            >
              <TrashIcon className="h-4 w-4" />
              Delete
            </button>
          </div>
        </>
      )}
    </div>
  );
}

// ============================================================================
// Delete Confirmation Modal
// ============================================================================

interface DeleteConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  isLoading: boolean;
  userEmail: string;
}

function DeleteConfirmModal({
  isOpen,
  onClose,
  onConfirm,
  isLoading,
  userEmail,
}: DeleteConfirmModalProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={!isLoading}>
      <ModalHeader onClose={isLoading ? () => {} : onClose}>Delete User</ModalHeader>
      <ModalBody>
        <p className="text-sm text-[var(--color-foreground)]">
          Are you sure you want to delete the user <strong>{userEmail}</strong>?
        </p>
        <p className="text-sm text-[var(--color-muted)] mt-2">
          This action cannot be undone.
        </p>
      </ModalBody>
      <ModalFooter>
        <Button variant="secondary" onClick={onClose} disabled={isLoading}>
          Cancel
        </Button>
        <Button variant="danger" onClick={onConfirm} loading={isLoading}>
          Delete User
        </Button>
      </ModalFooter>
    </Modal>
  );
}

// ============================================================================
// Filter Configuration
// ============================================================================

const filterColumns = [
  { key: "email", label: "Email", type: "string" as const },
  {
    key: "active",
    label: "Status",
    type: "enum" as const,
    enumValues: ["true", "false"],
  },
  {
    key: "role",
    label: "Role",
    type: "enum" as const,
    enumValues: ["admin", "editor", "viewer", "moderator"],
  },
];

// ============================================================================
// Main Component
// ============================================================================

export function UserListPage() {
  // Pagination state
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);

  // Filter state
  const [filters, setFilters] = useState<FilterState>({ search: "", filters: [] });

  // Delete modal state
  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; user: UserResponse | null }>({
    isOpen: false,
    user: null,
  });

  // Build query params from filters
  const queryParams: UserListParams = useMemo(() => {
    const params: UserListParams = {
      page,
      page_size: pageSize,
    };

    // Apply search filter
    if (filters.search) {
      return { ...params, email: filters.search };
    }

    // Apply column filters
    let email: string | undefined;
    let active: string | undefined;
    let role: string | undefined;
    for (const filter of filters.filters) {
      if (filter.column === "email" && typeof filter.value === "string") {
        email = filter.value;
      } else if (filter.column === "active" && typeof filter.value === "string") {
        active = filter.value;
      } else if (filter.column === "role" && typeof filter.value === "string") {
        role = filter.value;
      }
    }

    const result: UserListParams = { ...params };
    if (email) {
      return { ...result, email, ...(active && { active }), ...(role && { role }) };
    }
    if (active) {
      return { ...result, active, ...(role && { role }) };
    }
    if (role) {
      return { ...result, role };
    }

    return result;
  }, [page, pageSize, filters]);

  // Fetch users
  const { data, isLoading, error, refetch } = useUsers(queryParams);

  // Mutations
  const deleteUser = useDeleteUser({
    onSuccess: () => {
      setDeleteModal({ isOpen: false, user: null });
      refetch();
    },
  });

  const activateUser = useActivateUser({
    onSuccess: () => refetch(),
  });

  const deactivateUser = useDeactivateUser({
    onSuccess: () => refetch(),
  });

  // Event handlers
  const handleFilterChange = useCallback((newFilters: FilterState) => {
    setFilters(newFilters);
    setPage(1);
  }, []);

  const handleDelete = useCallback((user: UserResponse) => {
    setDeleteModal({ isOpen: true, user });
  }, []);

  const handleConfirmDelete = useCallback(() => {
    if (deleteModal.user) {
      deleteUser.mutate(deleteModal.user.id);
    }
  }, [deleteModal.user, deleteUser]);

  const handleActivate = useCallback(
    (userId: string) => {
      activateUser.mutate(userId);
    },
    [activateUser],
  );

  const handleDeactivate = useCallback(
    (userId: string) => {
      deactivateUser.mutate(userId);
    },
    [deactivateUser],
  );

  // Table columns
  const columns: Column<UserResponse>[] = useMemo(
    () => [
      {
        key: "email",
        header: "Email",
        render: (_value: unknown, row: UserResponse) => (
          <div>
            <Link
              href={`/users/${row.id}`}
              className="text-[var(--color-primary)] hover:underline font-medium"
            >
              {row.email}
            </Link>
            {row.name && (
              <p className="text-xs text-[var(--color-muted)]">{row.name}</p>
            )}
          </div>
        ),
      },
      {
        key: "roles",
        header: "Roles",
        render: (_value: unknown, row: UserResponse) => (
          <div className="flex flex-wrap gap-1">
            {row.roles.length > 0 ? (
              row.roles.slice(0, 3).map((r: string) => <RoleBadge key={r} role={r} size="sm" />)
            ) : (
              <span className="text-xs text-[var(--color-muted)]">No roles</span>
            )}
            {row.roles.length > 3 && (
              <span className="text-xs text-[var(--color-muted)]">
                +{row.roles.length - 3} more
              </span>
            )}
          </div>
        ),
      },
      {
        key: "status",
        header: "Status",
        render: (_value: unknown, row: UserResponse) => (
          <UserStatusBadge isActive={row.is_active} isSuperuser={row.is_superuser} size="sm" />
        ),
      },
      {
        key: "created_at",
        header: "Created",
        render: (_value: unknown, row: UserResponse) => (
          <span className="text-sm text-[var(--color-muted)]">
            {new Date(row.created_at).toLocaleDateString()}
          </span>
        ),
      },
      {
        key: "last_login",
        header: "Last Login",
        render: (_value: unknown, row: UserResponse) => (
          <span className="text-sm text-[var(--color-muted)]">
            {row.last_login
              ? new Date(row.last_login).toLocaleDateString()
              : "Never"}
          </span>
        ),
      },
      {
        key: "actions",
        header: "",
        render: (_value: unknown, row: UserResponse) => (
          <UserActionDropdown
            user={row}
            onEdit={() => {
              window.location.href = `/users/${row.id}`;
            }}
            onDelete={() => handleDelete(row)}
            onActivate={() => handleActivate(row.id)}
            onDeactivate={() => handleDeactivate(row.id)}
          />
        ),
      },
    ],
    [handleDelete, handleActivate, handleDeactivate],
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)]",
              "bg-[var(--color-primary)]/10",
            )}
          >
            <UsersIcon className="h-5 w-5 text-[var(--color-primary)]" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-foreground)]">Users</h1>
            <p className="text-sm text-[var(--color-muted)]">
              Manage admin users and their permissions
            </p>
          </div>
        </div>

        <Link href="/users/new">
          <Button leftIcon={<PlusIcon className="h-4 w-4" />}>New User</Button>
        </Link>
      </div>

      {/* Search and Filters */}
      <SearchFilter
        columns={filterColumns}
        onFilterChange={handleFilterChange}
        searchPlaceholder="Search by email..."
        syncToUrl={false}
      />

      {/* Error State */}
      {error && (
        <div
          className={cn(
            "p-4 rounded-[var(--radius-lg)]",
            "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
          )}
        >
          <p className="text-sm text-[var(--color-error)]">
            Failed to load users. Please try again.
          </p>
        </div>
      )}

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={[...(data?.items ?? [])]}
        getRowId={(row) => row.id}
        isLoading={isLoading}
        emptyMessage="No users found"
        className="rounded-[var(--radius-lg)] border border-[var(--color-border)]"
      />

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-[var(--color-muted)]">
            Showing {((page - 1) * pageSize) + 1} to {Math.min(page * pageSize, data.total)} of{" "}
            {data.total} users
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
            >
              Previous
            </Button>
            <span className="text-sm text-[var(--color-muted)]">
              Page {page} of {data.total_pages}
            </span>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages}
            >
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteModal.isOpen}
        onClose={() => setDeleteModal({ isOpen: false, user: null })}
        onConfirm={handleConfirmDelete}
        isLoading={deleteUser.isPending}
        userEmail={deleteModal.user?.email ?? ""}
      />
    </div>
  );
}
