"use client";

import { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useUser, useUpdateUser, useDeleteUser, useActivateUser, useDeactivateUser } from "@/hooks/useApi";
import { Button } from "@/components/ui/Button";
import { Input, FormField, Checkbox } from "@/components/ui/Form";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { RoleSelector } from "@/components/users/RoleSelector";
import { UserStatusBadge } from "@/components/users/UserStatusBadge";
import type { UserUpdateRequest } from "@/types";

// ============================================================================
// Icons
// ============================================================================

function ArrowLeftIcon({ className }: { className?: string }) {
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
      <line x1="19" y1="12" x2="5" y2="12" />
      <polyline points="12,19 5,12 12,5" />
    </svg>
  );
}

function UserIcon({ className }: { className?: string }) {
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
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
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

function SaveIcon({ className }: { className?: string }) {
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
      <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z" />
      <polyline points="17,21 17,13 7,13 7,21" />
      <polyline points="7,3 7,8 15,8" />
    </svg>
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
// Loading Skeleton
// ============================================================================

function LoadingSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="flex items-center gap-4">
        <div className="h-6 w-24 bg-[var(--color-card-hover)] rounded" />
      </div>
      <div className="h-12 w-64 bg-[var(--color-card-hover)] rounded" />
      <div className="grid gap-6 md:grid-cols-2">
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="space-y-2">
              <div className="h-4 w-20 bg-[var(--color-card-hover)] rounded" />
              <div className="h-10 w-full bg-[var(--color-card-hover)] rounded" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Form Data Interface
// ============================================================================

interface FormData {
  email: string;
  name: string;
  roles: string[];
  is_active: boolean;
  is_superuser: boolean;
}

// ============================================================================
// Props
// ============================================================================

export interface UserDetailPageProps {
  userId: string;
}

// ============================================================================
// Main Component
// ============================================================================

export function UserDetailPage({ userId }: UserDetailPageProps) {
  const router = useRouter();

  // Fetch user data
  const { data: user, isLoading, error } = useUser(userId);

  // Form state
  const [formData, setFormData] = useState<FormData>({
    email: "",
    name: "",
    roles: [],
    is_active: true,
    is_superuser: false,
  });

  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [isDirty, setIsDirty] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);

  // Mutations
  const updateUser = useUpdateUser({
    onSuccess: () => {
      setIsDirty(false);
    },
  });

  const deleteUser = useDeleteUser({
    onSuccess: () => {
      router.push("/users");
    },
  });

  const activateUser = useActivateUser();
  const deactivateUser = useDeactivateUser();

  // Initialize form data when user loads
  useEffect(() => {
    if (user) {
      setFormData({
        email: user.email,
        name: user.name ?? "",
        roles: [...user.roles],
        is_active: user.is_active,
        is_superuser: user.is_superuser,
      });
    }
  }, [user]);

  // Form change handler
  const handleChange = useCallback(
    <K extends keyof FormData>(field: K, value: FormData[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      setIsDirty(true);
      if (errors[field]) {
        setErrors((prev) => ({ ...prev, [field]: undefined }));
      }
    },
    [errors],
  );

  // Validation
  const validateForm = useCallback((): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    if (!formData.email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Invalid email address";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  // Submit handler
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!validateForm()) return;

      const data: UserUpdateRequest = {
        email: formData.email,
        name: formData.name || null,
        roles: formData.roles,
        is_active: formData.is_active,
        is_superuser: formData.is_superuser,
      };

      updateUser.mutate({ userId, data });
    },
    [validateForm, formData, updateUser, userId],
  );

  // Delete handler
  const handleDelete = useCallback(() => {
    deleteUser.mutate(userId);
  }, [deleteUser, userId]);

  // Toggle active status
  const handleToggleActive = useCallback(() => {
    if (user?.is_active) {
      deactivateUser.mutate(userId);
    } else {
      activateUser.mutate(userId);
    }
  }, [user, userId, activateUser, deactivateUser]);

  // Loading state
  if (isLoading) {
    return <LoadingSkeleton />;
  }

  // Error state
  if (error || !user) {
    return (
      <div className="p-6">
        <div
          className={cn(
            "p-6 rounded-[var(--radius-lg)]",
            "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
          )}
        >
          <h2 className="text-lg font-semibold text-[var(--color-error)]">User Not Found</h2>
          <p className="text-sm text-[var(--color-muted)] mt-2">
            The user you are looking for does not exist or has been deleted.
          </p>
          <Link href="/users">
            <Button variant="secondary" className="mt-4">
              Back to Users
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/users"
        className={cn(
          "inline-flex items-center gap-2 text-sm",
          "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
          "transition-colors duration-150",
        )}
      >
        <ArrowLeftIcon className="h-4 w-4" />
        Back to Users
      </Link>

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="flex items-center gap-4">
          <div
            className={cn(
              "flex h-14 w-14 items-center justify-center rounded-full",
              "bg-[var(--color-primary)]/10",
            )}
          >
            <UserIcon className="h-7 w-7 text-[var(--color-primary)]" />
          </div>
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-foreground)]">
              {user.name || user.email}
            </h1>
            {user.name && (
              <p className="text-sm text-[var(--color-muted)]">{user.email}</p>
            )}
            <div className="mt-1">
              <UserStatusBadge isActive={user.is_active} isSuperuser={user.is_superuser} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            onClick={handleToggleActive}
            loading={activateUser.isPending || deactivateUser.isPending}
          >
            {user.is_active ? "Deactivate" : "Activate"}
          </Button>
          <Button
            variant="danger"
            leftIcon={<TrashIcon className="h-4 w-4" />}
            onClick={() => setDeleteModalOpen(true)}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div
          className={cn(
            "p-6 rounded-[var(--radius-lg)]",
            "bg-[var(--color-card)] border border-[var(--color-border)]",
          )}
        >
          <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-6">
            User Information
          </h2>

          <div className="grid gap-6 md:grid-cols-2">
            <FormField
              label="Email"
              htmlFor="email"
              required
              error={errors.email}
            >
              <Input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleChange("email", e.target.value)}
                error={!!errors.email}
              />
            </FormField>

            <FormField label="Name" htmlFor="name">
              <Input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => handleChange("name", e.target.value)}
                placeholder="Display name (optional)"
              />
            </FormField>

            <FormField label="Roles" htmlFor="roles" className="md:col-span-2">
              <RoleSelector
                value={formData.roles}
                onChange={(roles) => handleChange("roles", roles)}
              />
            </FormField>

            <div className="space-y-4 md:col-span-2">
              <Checkbox
                id="is_active"
                label="Active"
                checked={formData.is_active}
                onChange={(e) => handleChange("is_active", e.target.checked)}
              />

              <Checkbox
                id="is_superuser"
                label="Superuser (bypasses all permission checks)"
                checked={formData.is_superuser}
                onChange={(e) => handleChange("is_superuser", e.target.checked)}
              />
            </div>
          </div>
        </div>

        {/* Metadata */}
        <div
          className={cn(
            "p-6 rounded-[var(--radius-lg)]",
            "bg-[var(--color-card)] border border-[var(--color-border)]",
          )}
        >
          <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-4">
            Account Details
          </h2>

          <dl className="grid gap-4 sm:grid-cols-2 md:grid-cols-4">
            <div>
              <dt className="text-xs text-[var(--color-muted)] uppercase tracking-wide">User ID</dt>
              <dd className="mt-1 text-sm text-[var(--color-foreground)] font-mono">{user.id}</dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-muted)] uppercase tracking-wide">Created</dt>
              <dd className="mt-1 text-sm text-[var(--color-foreground)]">
                {new Date(user.created_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-muted)] uppercase tracking-wide">Updated</dt>
              <dd className="mt-1 text-sm text-[var(--color-foreground)]">
                {new Date(user.updated_at).toLocaleString()}
              </dd>
            </div>
            <div>
              <dt className="text-xs text-[var(--color-muted)] uppercase tracking-wide">
                Last Login
              </dt>
              <dd className="mt-1 text-sm text-[var(--color-foreground)]">
                {user.last_login ? new Date(user.last_login).toLocaleString() : "Never"}
              </dd>
            </div>
          </dl>
        </div>

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-3">
          <Link href="/users">
            <Button variant="secondary" type="button">
              Cancel
            </Button>
          </Link>
          <Button
            type="submit"
            leftIcon={<SaveIcon className="h-4 w-4" />}
            loading={updateUser.isPending}
            disabled={!isDirty}
          >
            Save Changes
          </Button>
        </div>

        {/* Success/Error messages */}
        {updateUser.isSuccess && (
          <div
            className={cn(
              "p-4 rounded-[var(--radius-md)]",
              "bg-[var(--color-success)]/10 border border-[var(--color-success)]/20",
            )}
          >
            <p className="text-sm text-[var(--color-success)]">User updated successfully.</p>
          </div>
        )}

        {updateUser.isError && (
          <div
            className={cn(
              "p-4 rounded-[var(--radius-md)]",
              "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
            )}
          >
            <p className="text-sm text-[var(--color-error)]">
              Failed to update user. Please try again.
            </p>
          </div>
        )}
      </form>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        onClose={() => setDeleteModalOpen(false)}
        onConfirm={handleDelete}
        isLoading={deleteUser.isPending}
        userEmail={user.email}
      />
    </div>
  );
}
