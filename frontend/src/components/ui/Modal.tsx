"use client";

import {
  forwardRef,
  useEffect,
  useCallback,
  useRef,
  useId,
  useState,
  type HTMLAttributes,
  type ReactNode,
  type MouseEvent,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

export interface ModalProps extends HTMLAttributes<HTMLDivElement> {
  isOpen: boolean;
  onClose: () => void;
  closeOnOverlayClick?: boolean;
  closeOnEscape?: boolean;
  children?: ReactNode;
  /** Accessible label for the modal (used if no ModalHeader is present) */
  "aria-label"?: string;
}

/**
 * Get all focusable elements within a container.
 */
function getFocusableElements(container: HTMLElement): HTMLElement[] {
  const focusableSelectors = [
    "button:not([disabled])",
    "a[href]",
    "input:not([disabled])",
    "select:not([disabled])",
    "textarea:not([disabled])",
    '[tabindex]:not([tabindex="-1"])',
  ].join(", ");

  return Array.from(container.querySelectorAll(focusableSelectors)) as HTMLElement[];
}

export const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
    {
      isOpen,
      onClose,
      closeOnOverlayClick = true,
      closeOnEscape = true,
      className,
      children,
      "aria-label": ariaLabel,
      ...props
    },
    ref,
  ) => {
    const modalId = useId();
    const titleId = `${modalId}-title`;
    const modalRef = useRef<HTMLDivElement>(null);
    const previousActiveElement = useRef<HTMLElement | null>(null);

    const handleEscape = useCallback(
      (e: KeyboardEvent) => {
        if (closeOnEscape && e.key === "Escape") {
          onClose();
        }
      },
      [closeOnEscape, onClose],
    );

    const handleOverlayClick = (e: MouseEvent<HTMLDivElement>) => {
      if (closeOnOverlayClick && e.target === e.currentTarget) {
        onClose();
      }
    };

    // Focus trap handler
    const handleKeyDown = useCallback((e: KeyboardEvent) => {
      if (e.key !== "Tab" || !modalRef.current) return;

      const focusableElements = getFocusableElements(modalRef.current);
      if (focusableElements.length === 0) return;

      const firstElement = focusableElements[0];
      const lastElement = focusableElements[focusableElements.length - 1];

      // Safety check
      if (!firstElement || !lastElement) return;

      if (e.shiftKey) {
        // Shift + Tab: moving backwards
        if (document.activeElement === firstElement) {
          e.preventDefault();
          lastElement.focus();
        }
      } else {
        // Tab: moving forwards
        if (document.activeElement === lastElement) {
          e.preventDefault();
          firstElement.focus();
        }
      }
    }, []);

    useEffect(() => {
      if (isOpen) {
        // Store the currently focused element to restore later
        previousActiveElement.current = document.activeElement as HTMLElement;

        document.addEventListener("keydown", handleEscape);
        document.addEventListener("keydown", handleKeyDown);
        document.body.style.overflow = "hidden";

        // Focus the modal or first focusable element
        requestAnimationFrame(() => {
          if (modalRef.current) {
            const focusableElements = getFocusableElements(modalRef.current);
            const firstFocusable = focusableElements[0];
            if (firstFocusable) {
              firstFocusable.focus();
            } else {
              modalRef.current.focus();
            }
          }
        });
      }

      return () => {
        document.removeEventListener("keydown", handleEscape);
        document.removeEventListener("keydown", handleKeyDown);
        document.body.style.overflow = "";

        // Restore focus to the previously focused element
        if (
          previousActiveElement.current &&
          typeof previousActiveElement.current.focus === "function"
        ) {
          previousActiveElement.current.focus();
        }
      };
    }, [isOpen, handleEscape, handleKeyDown]);

    if (!isOpen) return null;

    const modalContent = (
      <div
        className={cn(
          "fixed inset-0 z-50",
          "flex items-center justify-center p-4",
          "animate-[fadeIn_150ms_ease-out]",
        )}
        onClick={handleOverlayClick}
        role="dialog"
        aria-modal="true"
        aria-labelledby={ariaLabel ? undefined : titleId}
        aria-label={ariaLabel}
      >
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" aria-hidden="true" />
        <div
          ref={(node) => {
            // Handle both refs using type assertion for mutable ref
            (modalRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
            if (typeof ref === "function") {
              ref(node);
            } else if (ref) {
              (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
            }
          }}
          tabIndex={-1}
          className={cn(
            "relative z-10 w-full max-w-lg",
            "bg-[var(--color-card)] rounded-[var(--radius-lg)]",
            "border border-[var(--color-border)]",
            "shadow-2xl shadow-black/40",
            "animate-[scaleIn_150ms_ease-out]",
            "focus:outline-none",
            className,
          )}
          data-modal-title-id={titleId}
          {...props}
        >
          {children}
        </div>
      </div>
    );

    if (typeof document === "undefined") return null;

    return createPortal(modalContent, document.body);
  },
);

Modal.displayName = "Modal";

export interface ModalHeaderProps extends HTMLAttributes<HTMLDivElement> {
  onClose?: () => void;
  children?: ReactNode;
}

export const ModalHeader = forwardRef<HTMLDivElement, ModalHeaderProps>(
  ({ onClose, className, children, ...props }, ref) => {
    const headerRef = useRef<HTMLDivElement>(null);
    const [titleId, setTitleId] = useState<string | undefined>(undefined);

    useEffect(() => {
      // Get the title ID from parent modal via data attribute
      if (headerRef.current) {
        const modal = headerRef.current.closest("[data-modal-title-id]");
        const id = modal?.getAttribute("data-modal-title-id");
        if (id) {
          setTitleId(id);
        }
      }
    }, []);

    return (
      <div
        ref={(node) => {
          (headerRef as React.MutableRefObject<HTMLDivElement | null>).current = node;
          if (typeof ref === "function") {
            ref(node);
          } else if (ref) {
            (ref as React.MutableRefObject<HTMLDivElement | null>).current = node;
          }
        }}
        className={cn(
          "flex items-center justify-between",
          "px-6 py-4",
          "border-b border-[var(--color-border)]",
          className,
        )}
        {...props}
      >
        <h2 id={titleId} className="text-lg font-semibold text-[var(--color-foreground)]">
          {children}
        </h2>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className={cn(
              "p-1 rounded-[var(--radius-md)]",
              "text-[var(--color-muted)] hover:text-[var(--color-foreground)]",
              "hover:bg-[var(--color-card-hover)]",
              "transition-colors duration-150",
              "focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-accent)]",
            )}
            aria-label="Close modal"
          >
            <svg
              className="h-5 w-5"
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
    );
  },
);

ModalHeader.displayName = "ModalHeader";

export interface ModalBodyProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export const ModalBody = forwardRef<HTMLDivElement, ModalBodyProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("px-6 py-4", className)} {...props}>
        {children}
      </div>
    );
  },
);

ModalBody.displayName = "ModalBody";

export interface ModalFooterProps extends HTMLAttributes<HTMLDivElement> {
  children?: ReactNode;
}

export const ModalFooter = forwardRef<HTMLDivElement, ModalFooterProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "flex items-center justify-end gap-3",
          "px-6 py-4",
          "border-t border-[var(--color-border)]",
          "bg-[var(--color-background)]/50",
          className,
        )}
        {...props}
      >
        {children}
      </div>
    );
  },
);

ModalFooter.displayName = "ModalFooter";
