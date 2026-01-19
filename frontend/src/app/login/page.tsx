"use client";

import { useState, useCallback, type FormEvent, useEffect } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import { useAuthContext } from "@/contexts/AuthContext";
import { Card, CardBody } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Checkbox, FormField } from "@/components/ui/Form";
import { cn } from "@/lib/utils";
import { isApiError } from "@/hooks/useApi";

interface DevCredential {
  email: string;
  password: string;
  role: string;
}

interface AdminConfig {
  title: string;
  debug: boolean;
  theme: string;
  dev_credentials: DevCredential[];
}

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
 * Alert icon for error messages.
 */
function AlertIcon({ className }: { className?: string }) {
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
      <circle cx="12" cy="12" r="10" />
      <path d="M12 8v4M12 16h.01" />
    </svg>
  );
}

/**
 * Login page component.
 * Provides email/password authentication with dark theme Cloudflare-style aesthetic.
 */
export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isLoggingIn, isAuthenticated, error: authError } = useAuthContext();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState<{ email: boolean; password: boolean }>({
    email: false,
    password: false,
  });
  const [config, setConfig] = useState<AdminConfig | null>(null);

  // Fetch admin config on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const baseUrl = process.env["NEXT_PUBLIC_ADMIN_API_URL"] ?? "/admin";
        const response = await fetch(`${baseUrl}/api/config`);
        if (response.ok) {
          const data = await response.json();
          setConfig(data as AdminConfig);
        }
      } catch (err) {
        // Config fetch failed, assume production mode
        console.warn("Failed to fetch admin config:", err);
      }
    };
    fetchConfig();
  }, []);

  const isDebugMode = config?.debug ?? false;

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      const returnUrl = searchParams.get("returnUrl") ?? "/";
      router.replace(returnUrl);
    }
  }, [isAuthenticated, router, searchParams]);

  // Update error state from auth context
  useEffect(() => {
    if (authError) {
      if (isApiError(authError)) {
        if (authError.status === 401) {
          setError("Invalid email or password. Please try again.");
        } else if (authError.status === 429) {
          setError("Too many login attempts. Please try again later.");
        } else {
          setError(authError.detail ?? "An error occurred during login. Please try again.");
        }
      } else {
        setError("An unexpected error occurred. Please try again.");
      }
    }
  }, [authError]);

  const validateEmail = useCallback((value: string): string | null => {
    if (!value) return "Email is required";
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "Please enter a valid email address";
    return null;
  }, []);

  const validatePassword = useCallback(
    (value: string): string | null => {
      if (!value) return "Password is required";
      // Skip length validation in debug mode to allow simple dev passwords
      if (!isDebugMode && value.length < 6) return "Password must be at least 6 characters";
      return null;
    },
    [isDebugMode],
  );

  // Quick login handler for dev mode
  const handleQuickLogin = useCallback(
    async (credential: DevCredential) => {
      setEmail(credential.email);
      setPassword(credential.password);
      setError(null);
      try {
        await login(credential.email, credential.password, false);
      } catch (err) {
        console.error("Quick login failed:", err);
      }
    },
    [login],
  );

  const emailError = touched.email ? validateEmail(email) : null;
  const passwordError = touched.password ? validatePassword(password) : null;

  const handleSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();

      // Mark all fields as touched
      setTouched({ email: true, password: true });

      // Validate all fields
      const emailValidation = validateEmail(email);
      const passwordValidation = validatePassword(password);

      if (emailValidation || passwordValidation) {
        return;
      }

      // Clear previous error
      setError(null);

      try {
        await login(email, password, rememberMe);
      } catch (err) {
        // Error is handled by the auth context
        console.error("Login failed:", err);
      }
    },
    [email, password, rememberMe, login, validateEmail, validatePassword],
  );

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
          <h1 className="text-2xl font-bold text-[var(--color-foreground)]">Litestar Admin</h1>
          <p className="mt-2 text-sm text-[var(--color-muted)]">
            Sign in to your account to continue
          </p>
        </div>

        {/* Login card */}
        <Card variant="default" className="shadow-lg shadow-black/30">
          <CardBody className="p-6">
            {/* Error alert */}
            {error && (
              <div
                className={cn(
                  "mb-6 flex items-start gap-3 rounded-[var(--radius-md)] p-4",
                  "bg-[var(--color-error)]/10 border border-[var(--color-error)]/20",
                )}
                role="alert"
              >
                <AlertIcon className="h-5 w-5 flex-shrink-0 text-[var(--color-error)]" />
                <p className="text-sm text-[var(--color-error)]">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Email field */}
              <FormField
                label="Email address"
                htmlFor="email"
                required
                {...(emailError ? { error: emailError } : {})}
              >
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, email: true }))}
                  placeholder="you@litestar.dev"
                  autoComplete="email"
                  autoFocus
                  error={!!emailError}
                  disabled={isLoggingIn}
                />
              </FormField>

              {/* Password field */}
              <FormField
                label="Password"
                htmlFor="password"
                required
                {...(passwordError ? { error: passwordError } : {})}
              >
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  onBlur={() => setTouched((prev) => ({ ...prev, password: true }))}
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  error={!!passwordError}
                  disabled={isLoggingIn}
                />
              </FormField>

              {/* Remember me and forgot password */}
              <div className="flex items-center justify-between">
                <Checkbox
                  id="remember-me"
                  label="Remember me"
                  checked={rememberMe}
                  onChange={(e) => setRememberMe(e.target.checked)}
                  disabled={isLoggingIn}
                />
                <Link
                  href="/forgot-password"
                  className={cn(
                    "text-sm text-[var(--color-accent)]",
                    "hover:text-[var(--color-accent)]/80 hover:underline",
                    "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)] focus-visible:ring-offset-2",
                    "focus-visible:ring-offset-[var(--color-card)]",
                    "rounded-[var(--radius-sm)]",
                  )}
                >
                  Forgot password?
                </Link>
              </div>

              {/* Submit button */}
              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={isLoggingIn}
                disabled={isLoggingIn}
                className="w-full"
              >
                {isLoggingIn ? "Signing in..." : "Sign in"}
              </Button>
            </form>
          </CardBody>
        </Card>

        {/* Dev Mode Quick Login */}
        {isDebugMode && config?.dev_credentials && config.dev_credentials.length > 0 && (
          <div
            className={cn(
              "mt-6 rounded-[var(--radius-md)] border-2 border-dashed",
              "border-[var(--color-warning)]/40 bg-[var(--color-warning)]/5",
              "p-4",
            )}
          >
            <div className="mb-3 flex items-center gap-2">
              <span className="text-[var(--color-warning)] text-lg">⚠️</span>
              <span className="text-sm font-semibold text-[var(--color-warning)]">
                Development Mode
              </span>
            </div>
            <p className="mb-3 text-xs text-[var(--color-muted)]">
              Quick login with test accounts:
            </p>
            <div className="flex flex-wrap gap-2">
              {config.dev_credentials.map((cred) => (
                <Button
                  key={cred.email}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => handleQuickLogin(cred)}
                  disabled={isLoggingIn}
                  className={cn(
                    "text-xs capitalize",
                    "border border-[var(--color-warning)]/30",
                    "hover:bg-[var(--color-warning)]/10",
                    "hover:border-[var(--color-warning)]/50",
                  )}
                >
                  {cred.role}
                </Button>
              ))}
            </div>
          </div>
        )}

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
