"use client";

import { useState, useCallback } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, FormField } from "@/components/ui/Form";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuthContext } from "@/contexts/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

// Icons
const UserIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

const ShieldIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

const KeyIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
  </svg>
);

const MailIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <rect x="2" y="4" width="20" height="16" rx="2" />
    <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
  </svg>
);

const CheckIcon = ({ className }: { className?: string }) => (
  <svg
    className={className}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

export default function ProfilePage() {
  const { user } = useAuthContext();
  const { addToast } = useToast();

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [passwordErrors, setPasswordErrors] = useState<Record<string, string>>({});

  const validatePasswords = useCallback(() => {
    const errors: Record<string, string> = {};

    if (!currentPassword) {
      errors["currentPassword"] = "Current password is required";
    }

    if (!newPassword) {
      errors["newPassword"] = "New password is required";
    } else if (newPassword.length < 8) {
      errors["newPassword"] = "Password must be at least 8 characters";
    }

    if (!confirmPassword) {
      errors["confirmPassword"] = "Please confirm your new password";
    } else if (newPassword !== confirmPassword) {
      errors["confirmPassword"] = "Passwords do not match";
    }

    setPasswordErrors(errors);
    return Object.keys(errors).length === 0;
  }, [currentPassword, newPassword, confirmPassword]);

  const handleChangePassword = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();

      if (!validatePasswords()) {
        return;
      }

      setIsChangingPassword(true);

      try {
        await api.changePassword(currentPassword, newPassword);

        addToast({
          variant: "success",
          title: "Password Changed",
          description: "Your password has been updated successfully.",
        });

        // Clear form
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setPasswordErrors({});
      } catch (error) {
        addToast({
          variant: "error",
          title: "Password Change Failed",
          description:
            error instanceof Error
              ? error.message
              : "Failed to change password. Please check your current password.",
        });
      } finally {
        setIsChangingPassword(false);
      }
    },
    [currentPassword, newPassword, validatePasswords, addToast],
  );

  // Derive display name from email
  const displayName = user?.email?.split("@")[0] ?? "User";
  const initials = displayName.substring(0, 2).toUpperCase();

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <PageHeader
            title="Profile"
            subtitle="Manage your account settings"
            breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Profile" }]}
          />

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Profile Info Card */}
            <div className="lg:col-span-2 space-y-6">
              {/* User Details */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <UserIcon className="h-5 w-5 text-[var(--color-accent)]" />
                    <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                      Account Details
                    </h2>
                  </div>
                </CardHeader>
                <CardBody>
                  <div className="flex items-start gap-6">
                    {/* Avatar */}
                    <div
                      className={cn(
                        "flex h-20 w-20 shrink-0 items-center justify-center rounded-full",
                        "bg-[var(--color-primary)] text-white text-2xl font-bold",
                      )}
                    >
                      {initials}
                    </div>

                    {/* Details */}
                    <div className="flex-1 space-y-4">
                      <div>
                        <p className="text-sm text-[var(--color-muted)]">Display Name</p>
                        <p className="text-lg font-medium text-[var(--color-foreground)]">
                          {displayName}
                        </p>
                      </div>

                      <div className="flex items-center gap-2">
                        <MailIcon className="h-4 w-4 text-[var(--color-muted)]" />
                        <div>
                          <p className="text-sm text-[var(--color-muted)]">Email Address</p>
                          <p className="text-[var(--color-foreground)]">{user?.email}</p>
                        </div>
                      </div>

                      <div>
                        <p className="text-sm text-[var(--color-muted)]">User ID</p>
                        <p className="text-[var(--color-foreground)] font-mono text-sm">
                          {user?.id}
                        </p>
                      </div>
                    </div>
                  </div>
                </CardBody>
              </Card>

              {/* Change Password */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <KeyIcon className="h-5 w-5 text-[var(--color-accent)]" />
                    <div>
                      <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                        Change Password
                      </h2>
                      <p className="text-sm text-[var(--color-muted)]">
                        Update your password to keep your account secure
                      </p>
                    </div>
                  </div>
                </CardHeader>
                <CardBody>
                  <form onSubmit={handleChangePassword} className="space-y-4 max-w-md">
                    <FormField
                      label="Current Password"
                      htmlFor="current-password"
                      required
                      {...(passwordErrors["currentPassword"]
                        ? { error: passwordErrors["currentPassword"] }
                        : {})}
                    >
                      <Input
                        id="current-password"
                        type="password"
                        value={currentPassword}
                        onChange={(e) => setCurrentPassword(e.target.value)}
                        placeholder="Enter current password"
                        error={!!passwordErrors["currentPassword"]}
                        autoComplete="current-password"
                      />
                    </FormField>

                    <FormField
                      label="New Password"
                      htmlFor="new-password"
                      required
                      {...(passwordErrors["newPassword"]
                        ? { error: passwordErrors["newPassword"] }
                        : {})}
                      hint="Must be at least 8 characters"
                    >
                      <Input
                        id="new-password"
                        type="password"
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                        placeholder="Enter new password"
                        error={!!passwordErrors["newPassword"]}
                        autoComplete="new-password"
                      />
                    </FormField>

                    <FormField
                      label="Confirm New Password"
                      htmlFor="confirm-password"
                      required
                      {...(passwordErrors["confirmPassword"]
                        ? { error: passwordErrors["confirmPassword"] }
                        : {})}
                    >
                      <Input
                        id="confirm-password"
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Confirm new password"
                        error={!!passwordErrors["confirmPassword"]}
                        autoComplete="new-password"
                      />
                    </FormField>

                    <div className="pt-2">
                      <Button
                        type="submit"
                        variant="primary"
                        loading={isChangingPassword}
                        disabled={isChangingPassword}
                      >
                        Change Password
                      </Button>
                    </div>
                  </form>
                </CardBody>
              </Card>
            </div>

            {/* Sidebar */}
            <div className="space-y-6">
              {/* Roles Card */}
              <Card>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <ShieldIcon className="h-5 w-5 text-[var(--color-accent)]" />
                    <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                      Roles
                    </h2>
                  </div>
                </CardHeader>
                <CardBody>
                  {user?.roles && user.roles.length > 0 ? (
                    <div className="flex flex-wrap gap-2">
                      {user.roles.map((role) => (
                        <span
                          key={role}
                          className={cn(
                            "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full",
                            "text-sm font-medium",
                            "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                          )}
                        >
                          <CheckIcon className="h-3.5 w-3.5" />
                          {role.charAt(0).toUpperCase() + role.slice(1)}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-muted)]">No roles assigned</p>
                  )}
                </CardBody>
              </Card>

              {/* Permissions Card */}
              <Card>
                <CardHeader>
                  <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                    Permissions
                  </h2>
                </CardHeader>
                <CardBody>
                  {user?.permissions && user.permissions.length > 0 ? (
                    <div className="space-y-2">
                      {user.permissions.map((permission) => (
                        <div key={permission} className="flex items-center gap-2 text-sm">
                          <CheckIcon className="h-4 w-4 text-green-500" />
                          <span className="text-[var(--color-foreground)]">
                            {permission.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-[var(--color-muted)]">No specific permissions</p>
                  )}
                </CardBody>
              </Card>

              {/* Security Tips */}
              <Card>
                <CardHeader>
                  <h2 className="text-base font-semibold text-[var(--color-foreground)]">
                    Security Tips
                  </h2>
                </CardHeader>
                <CardBody>
                  <ul className="space-y-2 text-sm text-[var(--color-muted)]">
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--color-accent)]">•</span>
                      Use a strong, unique password
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--color-accent)]">•</span>
                      Never share your credentials
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--color-accent)]">•</span>
                      Log out when using shared computers
                    </li>
                    <li className="flex items-start gap-2">
                      <span className="text-[var(--color-accent)]">•</span>
                      Change password periodically
                    </li>
                  </ul>
                </CardBody>
              </Card>
            </div>
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
