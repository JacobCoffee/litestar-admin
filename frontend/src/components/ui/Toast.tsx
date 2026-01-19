"use client";

import {
  createContext,
  useContext,
  useCallback,
  useState,
  useEffect,
  forwardRef,
  type ReactNode,
  type HTMLAttributes,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  variant: ToastVariant;
  title: string;
  description?: string;
  duration?: number;
}

interface ToastContextValue {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => string;
  removeToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error("useToast must be used within a ToastProvider");
  }
  return context;
}

export interface ToastProviderProps {
  children: ReactNode;
  defaultDuration?: number;
  maxToasts?: number;
}

export function ToastProvider({
  children,
  defaultDuration = 5000,
  maxToasts = 5,
}: ToastProviderProps) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback(
    (toast: Omit<Toast, "id">) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
      const newToast: Toast = {
        ...toast,
        id,
        duration: toast.duration ?? defaultDuration,
      };

      setToasts((prev) => {
        const updated = [...prev, newToast];
        if (updated.length > maxToasts) {
          return updated.slice(-maxToasts);
        }
        return updated;
      });

      return id;
    },
    [defaultDuration, maxToasts],
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onRemove={removeToast} />
    </ToastContext.Provider>
  );
}

interface ToastContainerProps {
  toasts: Toast[];
  onRemove: (id: string) => void;
}

function ToastContainer({ toasts, onRemove }: ToastContainerProps) {
  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className={cn(
        "fixed bottom-4 right-4 z-[100]",
        "flex flex-col gap-2",
        "max-w-sm w-full",
        "pointer-events-none",
      )}
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body,
  );
}

const variantStyles: Record<ToastVariant, string> = {
  success: "border-l-[var(--color-success)] [--toast-icon-color:var(--color-success)]",
  error: "border-l-[var(--color-error)] [--toast-icon-color:var(--color-error)]",
  warning: "border-l-[var(--color-warning)] [--toast-icon-color:var(--color-warning)]",
  info: "border-l-[var(--color-info)] [--toast-icon-color:var(--color-info)]",
};

const variantIcons: Record<ToastVariant, ReactNode> = {
  success: (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M20 6L9 17l-5-5" />
    </svg>
  ),
  error: (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M15 9l-6 6M9 9l6 6" />
    </svg>
  ),
  warning: (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
    </svg>
  ),
  info: (
    <svg
      className="h-5 w-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4M12 8h.01" />
    </svg>
  ),
};

interface ToastItemProps {
  toast: Toast;
  onRemove: (id: string) => void;
}

function ToastItem({ toast, onRemove }: ToastItemProps) {
  const [isExiting, setIsExiting] = useState(false);

  useEffect(() => {
    if (toast.duration && toast.duration > 0) {
      const exitTimer = setTimeout(() => {
        setIsExiting(true);
      }, toast.duration - 150);

      const removeTimer = setTimeout(() => {
        onRemove(toast.id);
      }, toast.duration);

      return () => {
        clearTimeout(exitTimer);
        clearTimeout(removeTimer);
      };
    }
  }, [toast.id, toast.duration, onRemove]);

  const handleClose = () => {
    setIsExiting(true);
    setTimeout(() => onRemove(toast.id), 150);
  };

  return (
    <div
      className={cn(
        "pointer-events-auto",
        "bg-[var(--color-card)]",
        "border border-[var(--color-border)] border-l-4",
        "rounded-[var(--radius-md)]",
        "shadow-lg shadow-black/30",
        "p-4",
        variantStyles[toast.variant],
        isExiting
          ? "animate-[slideOut_150ms_ease-in_forwards]"
          : "animate-[slideIn_150ms_ease-out]",
      )}
      role="alert"
    >
      <div className="flex gap-3">
        <div className="flex-shrink-0 text-[var(--toast-icon-color)]">
          {variantIcons[toast.variant]}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-[var(--color-foreground)]">{toast.title}</p>
          {toast.description && (
            <p className="mt-1 text-sm text-[var(--color-muted)]">{toast.description}</p>
          )}
        </div>
        <button
          type="button"
          onClick={handleClose}
          className={cn(
            "flex-shrink-0 p-1 rounded-[var(--radius-sm)]",
            "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
            "hover:bg-[var(--color-card-hover)]",
            "transition-colors duration-150",
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
          )}
          aria-label="Dismiss notification"
        >
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export interface ToastProps extends HTMLAttributes<HTMLDivElement> {
  variant?: ToastVariant;
  title: string;
  description?: string;
  onClose?: () => void;
}

export const ToastComponent = forwardRef<HTMLDivElement, ToastProps>(
  ({ variant = "info", title, description, onClose, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "bg-[var(--color-card)]",
          "border border-[var(--color-border)] border-l-4",
          "rounded-[var(--radius-md)]",
          "shadow-lg shadow-black/30",
          "p-4",
          variantStyles[variant],
          className,
        )}
        role="alert"
        {...props}
      >
        <div className="flex gap-3">
          <div className="flex-shrink-0 text-[var(--toast-icon-color)]">
            {variantIcons[variant]}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-[var(--color-foreground)]">{title}</p>
            {description && <p className="mt-1 text-sm text-[var(--color-muted)]">{description}</p>}
          </div>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className={cn(
                "flex-shrink-0 p-1 rounded-[var(--radius-sm)]",
                "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
                "hover:bg-[var(--color-card-hover)]",
                "transition-colors duration-150",
                "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
              )}
              aria-label="Dismiss notification"
            >
              <svg
                className="h-4 w-4"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                aria-hidden="true"
              >
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
      </div>
    );
  },
);

ToastComponent.displayName = "Toast";
