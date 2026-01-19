"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { useCreateUser } from "@/hooks/useApi";
import { Button } from "@/components/ui/Button";
import { Input, FormField, Checkbox } from "@/components/ui/Form";
import { RoleSelector } from "@/components/users/RoleSelector";
import type { UserCreateRequest } from "@/types";

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

function UserPlusIcon({ className }: { className?: string }) {
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
      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
      <circle cx="8.5" cy="7" r="4" />
      <line x1="20" y1="8" x2="20" y2="14" />
      <line x1="23" y1="11" x2="17" y2="11" />
    </svg>
  );
}

function EyeIcon({ className }: { className?: string }) {
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
      <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
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
      <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24" />
      <line x1="1" y1="1" x2="23" y2="23" />
    </svg>
  );
}

// ============================================================================
// Form Data Interface
// ============================================================================

interface FormData {
  email: string;
  password: string;
  confirmPassword: string;
  name: string;
  roles: string[];
  is_active: boolean;
  is_superuser: boolean;
}

const initialFormData: FormData = {
  email: "",
  password: "",
  confirmPassword: "",
  name: "",
  roles: [],
  is_active: true,
  is_superuser: false,
};

// ============================================================================
// Main Component
// ============================================================================

export function UserCreatePage() {
  const router = useRouter();

  // Form state
  const [formData, setFormData] = useState<FormData>(initialFormData);
  const [errors, setErrors] = useState<Partial<Record<keyof FormData, string>>>({});
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Create mutation
  const createUser = useCreateUser({
    onSuccess: (data) => {
      router.push(`/users/${data.id}`);
    },
  });

  // Form change handler
  const handleChange = useCallback(
    <K extends keyof FormData>(field: K, value: FormData[K]) => {
      setFormData((prev) => ({ ...prev, [field]: value }));
      if (errors[field]) {
        setErrors((prev) => ({ ...prev, [field]: undefined }));
      }
    },
    [errors],
  );

  // Validation
  const validateForm = useCallback((): boolean => {
    const newErrors: Partial<Record<keyof FormData, string>> = {};

    // Email validation
    if (!formData.email) {
      newErrors.email = "Email is required";
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = "Invalid email address";
    }

    // Password validation
    if (!formData.password) {
      newErrors.password = "Password is required";
    } else if (formData.password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (formData.password !== formData.confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [formData]);

  // Submit handler
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!validateForm()) return;

      const data: UserCreateRequest = {
        email: formData.email,
        password: formData.password,
        ...(formData.name ? { name: formData.name } : {}),
        roles: formData.roles,
        is_active: formData.is_active,
        is_superuser: formData.is_superuser,
      };

      createUser.mutate(data);
    },
    [validateForm, formData, createUser],
  );

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
      <div className="flex items-center gap-4">
        <div
          className={cn(
            "flex h-14 w-14 items-center justify-center rounded-full",
            "bg-[var(--color-primary)]/10",
          )}
        >
          <UserPlusIcon className="h-7 w-7 text-[var(--color-primary)]" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-[var(--color-foreground)]">Create New User</h1>
          <p className="text-sm text-[var(--color-muted)]">
            Add a new admin user to the system
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Account Information */}
        <div
          className={cn(
            "p-6 rounded-[var(--radius-lg)]",
            "bg-[var(--color-card)] border border-[var(--color-border)]",
          )}
        >
          <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-6">
            Account Information
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
                placeholder="user@example.com"
                error={!!errors.email}
                autoComplete="email"
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

            <FormField
              label="Password"
              htmlFor="password"
              required
              error={errors.password}
              hint="Minimum 8 characters"
            >
              <div className="relative">
                <Input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => handleChange("password", e.target.value)}
                  placeholder="Enter password"
                  error={!!errors.password}
                  autoComplete="new-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={cn(
                    "absolute right-3 top-1/2 -translate-y-1/2",
                    "p-1 rounded-[var(--radius-sm)]",
                    "text-[var(--color-muted)]",
                    "hover:text-[var(--color-foreground)]",
                    "transition-colors duration-150",
                  )}
                  tabIndex={-1}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? (
                    <EyeOffIcon className="h-4 w-4" />
                  ) : (
                    <EyeIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </FormField>

            <FormField
              label="Confirm Password"
              htmlFor="confirmPassword"
              required
              error={errors.confirmPassword}
            >
              <div className="relative">
                <Input
                  id="confirmPassword"
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.confirmPassword}
                  onChange={(e) => handleChange("confirmPassword", e.target.value)}
                  placeholder="Confirm password"
                  error={!!errors.confirmPassword}
                  autoComplete="new-password"
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className={cn(
                    "absolute right-3 top-1/2 -translate-y-1/2",
                    "p-1 rounded-[var(--radius-sm)]",
                    "text-[var(--color-muted)]",
                    "hover:text-[var(--color-foreground)]",
                    "transition-colors duration-150",
                  )}
                  tabIndex={-1}
                  aria-label={showConfirmPassword ? "Hide password" : "Show password"}
                >
                  {showConfirmPassword ? (
                    <EyeOffIcon className="h-4 w-4" />
                  ) : (
                    <EyeIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </FormField>
          </div>
        </div>

        {/* Roles and Permissions */}
        <div
          className={cn(
            "p-6 rounded-[var(--radius-lg)]",
            "bg-[var(--color-card)] border border-[var(--color-border)]",
          )}
        >
          <h2 className="text-lg font-semibold text-[var(--color-foreground)] mb-6">
            Roles and Permissions
          </h2>

          <div className="space-y-6">
            <FormField label="Roles" htmlFor="roles">
              <RoleSelector
                value={formData.roles}
                onChange={(roles) => handleChange("roles", roles)}
              />
            </FormField>

            <div className="space-y-4">
              <Checkbox
                id="is_active"
                label="Active (user can log in)"
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

        {/* Form Actions */}
        <div className="flex items-center justify-end gap-3">
          <Link href="/users">
            <Button variant="secondary" type="button">
              Cancel
            </Button>
          </Link>
          <Button type="submit" loading={createUser.isPending}>
            Create User
          </Button>
        </div>

        {/* Error message */}
        {createUser.isError && (
          <div
            className={cn(
              "p-4 rounded-[var(--radius-md)]",
              "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
            )}
          >
            <p className="text-sm text-[var(--color-error)]">
              Failed to create user. The email may already be in use.
            </p>
          </div>
        )}
      </form>
    </div>
  );
}
