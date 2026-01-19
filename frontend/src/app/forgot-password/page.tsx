"use client";

import Link from "next/link";

import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";

/**
 * Litestar logo component.
 */
function LitestarLogo({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M16 2L3 9.5V22.5L16 30L29 22.5V9.5L16 2Z"
        fill="var(--color-primary)"
        stroke="var(--color-primary)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M16 8L8 12.5V21.5L16 26L24 21.5V12.5L16 8Z"
        fill="var(--color-background)"
        stroke="var(--color-primary)"
        strokeWidth="1"
        strokeLinejoin="round"
      />
      <path
        d="M16 13L12 15.5V20.5L16 23L20 20.5V15.5L16 13Z"
        fill="var(--color-primary)"
        stroke="var(--color-primary)"
        strokeWidth="0.5"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/**
 * Mail icon for the page.
 */
function MailIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect width="20" height="16" x="2" y="4" rx="2" />
      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
    </svg>
  );
}

/**
 * Forgot password page.
 * Displays a message that password reset is not yet implemented.
 */
export default function ForgotPasswordPage() {
  return (
    <div
      className={cn(
        "flex min-h-screen flex-col items-center justify-center",
        "bg-[var(--color-background)]",
        "px-4 py-12",
      )}
    >
      <div className="w-full max-w-sm">
        {/* Logo and branding */}
        <div className="mb-8 text-center">
          <div className="flex justify-center mb-4">
            <LitestarLogo className="h-12 w-12" />
          </div>
          <h1 className="text-2xl font-bold text-[var(--color-foreground)]">Reset Password</h1>
          <p className="mt-2 text-sm text-[var(--color-muted)]">
            Recover access to your account
          </p>
        </div>

        {/* Card */}
        <Card variant="default" className="shadow-lg shadow-black/30">
          <CardBody className="p-6">
            <div className="text-center">
              {/* Icon */}
              <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-[var(--color-primary)]/10">
                <MailIcon className="h-8 w-8 text-[var(--color-primary)]" />
              </div>

              {/* Message */}
              <h2 className="mb-2 text-lg font-semibold text-[var(--color-foreground)]">
                Coming Soon
              </h2>
              <p className="mb-6 text-sm text-[var(--color-muted)]">
                Password reset functionality is not yet available. Please contact your administrator
                if you need to reset your password.
              </p>

              {/* Back to login button */}
              <Link href="/login">
                <Button variant="primary" size="md" className="w-full">
                  Back to Login
                </Button>
              </Link>
            </div>
          </CardBody>
        </Card>

        {/* Footer text */}
        <p className="mt-6 text-center text-xs text-[var(--color-muted)]">
          Protected by Litestar Admin.{" "}
          <a
            href="https://litestar.dev"
            target="_blank"
            rel="noopener noreferrer"
            className={cn("text-[var(--color-accent)]", "hover:underline")}
          >
            Learn more
          </a>
        </p>
      </div>
    </div>
  );
}
