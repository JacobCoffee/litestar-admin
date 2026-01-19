"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Modal, ModalHeader, ModalBody, ModalFooter } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { Input, FormField, Label } from "@/components/ui/Form";

// ============================================================================
// Types
// ============================================================================

export interface PasswordChangeModalProps {
  /** Whether the modal is open */
  isOpen: boolean;
  /** Callback to close the modal */
  onClose: () => void;
  /** Callback when password change is submitted */
  onSubmit: (newPassword: string) => Promise<void>;
  /** User's email for display */
  userEmail?: string;
  /** Minimum password length */
  minLength?: number;
}

// ============================================================================
// Icons
// ============================================================================

function KeyIcon({ className }: { className?: string }) {
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
      <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
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
// Main Component
// ============================================================================

export function PasswordChangeModal({
  isOpen,
  onClose,
  onSubmit,
  userEmail,
  minLength = 8,
}: PasswordChangeModalProps) {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ password: string | undefined; confirm: string | undefined }>({
    password: undefined,
    confirm: undefined,
  });

  const resetForm = useCallback(() => {
    setPassword("");
    setConfirmPassword("");
    setShowPassword(false);
    setShowConfirmPassword(false);
    setErrors({ password: undefined, confirm: undefined });
  }, []);

  const handleClose = useCallback(() => {
    if (!isSubmitting) {
      resetForm();
      onClose();
    }
  }, [isSubmitting, onClose, resetForm]);

  const validateForm = useCallback((): boolean => {
    let passwordError: string | undefined;
    let confirmError: string | undefined;

    if (!password) {
      passwordError = "Password is required";
    } else if (password.length < minLength) {
      passwordError = `Password must be at least ${minLength} characters`;
    }

    if (!confirmPassword) {
      confirmError = "Please confirm your password";
    } else if (password !== confirmPassword) {
      confirmError = "Passwords do not match";
    }

    setErrors({ password: passwordError, confirm: confirmError });
    return !passwordError && !confirmError;
  }, [password, confirmPassword, minLength]);

  const handleSubmit = useCallback(async () => {
    if (!validateForm()) return;

    setIsSubmitting(true);
    try {
      await onSubmit(password);
      resetForm();
      onClose();
    } catch {
      // Error handling is done by the parent component
    } finally {
      setIsSubmitting(false);
    }
  }, [validateForm, onSubmit, password, resetForm, onClose]);

  return (
    <Modal isOpen={isOpen} onClose={handleClose} closeOnOverlayClick={!isSubmitting}>
      <ModalHeader onClose={isSubmitting ? () => {} : handleClose}>
        <div className="flex items-center gap-3">
          <div
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-full",
              "bg-[var(--color-primary)]/10",
            )}
          >
            <KeyIcon className="h-5 w-5 text-[var(--color-primary)]" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-[var(--color-foreground)]">Change Password</h2>
            {userEmail && (
              <p className="text-sm text-[var(--color-muted)]">{userEmail}</p>
            )}
          </div>
        </div>
      </ModalHeader>

      <ModalBody>
        <div className="space-y-4">
          <FormField
            label="New Password"
            htmlFor="new-password"
            required
            error={errors.password}
            hint={`Minimum ${minLength} characters`}
          >
            <div className="relative">
              <Input
                id="new-password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  if (errors.password) setErrors({ password: undefined, confirm: errors.confirm });
                }}
                placeholder="Enter new password"
                error={!!errors.password}
                disabled={isSubmitting}
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
            htmlFor="confirm-password"
            required
            error={errors.confirm}
          >
            <div className="relative">
              <Input
                id="confirm-password"
                type={showConfirmPassword ? "text" : "password"}
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  if (errors.confirm) setErrors({ password: errors.password, confirm: undefined });
                }}
                placeholder="Confirm new password"
                error={!!errors.confirm}
                disabled={isSubmitting}
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
      </ModalBody>

      <ModalFooter>
        <Button variant="secondary" onClick={handleClose} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button variant="primary" onClick={handleSubmit} loading={isSubmitting}>
          Change Password
        </Button>
      </ModalFooter>
    </Modal>
  );
}

PasswordChangeModal.displayName = "PasswordChangeModal";
