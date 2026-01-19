"use client";

import {
  forwardRef,
  useState,
  useCallback,
  useId,
  useRef,
  useEffect,
  type HTMLAttributes,
  type ReactNode,
} from "react";
import { cn } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

export interface FieldsetProps extends Omit<HTMLAttributes<HTMLFieldSetElement>, "title"> {
  /** The title/legend of the fieldset section */
  title: string;
  /** Optional description text below the title */
  description?: string;
  /** Whether the fieldset is expanded by default */
  defaultOpen?: boolean;
  /** Controlled open state (makes component controlled) */
  open?: boolean;
  /** Callback when open state changes */
  onOpenChange?: (open: boolean) => void;
  /** Whether the fieldset can be collapsed */
  collapsible?: boolean;
  /** Content to render inside the fieldset */
  children: ReactNode;
}

// ============================================================================
// ChevronIcon Component
// ============================================================================

interface ChevronIconProps {
  isOpen: boolean;
  className?: string;
}

function ChevronIcon({ isOpen, className }: ChevronIconProps) {
  return (
    <svg
      className={cn(
        "h-5 w-5 text-[var(--color-muted)]",
        "transition-transform duration-200",
        isOpen && "rotate-180",
        className,
      )}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
    </svg>
  );
}

// ============================================================================
// Fieldset Component
// ============================================================================

/**
 * Fieldset component with optional collapsible sections for organizing form fields.
 *
 * Features:
 * - Groups form fields into logical sections with a title/legend
 * - Optional collapsible behavior with smooth height animation
 * - Visual chevron indicator for collapse state
 * - Accessible with proper ARIA attributes
 * - Supports both controlled and uncontrolled usage
 * - Dark theme styling matching the Cloudflare dashboard aesthetic
 *
 * @example
 * ```tsx
 * // Basic usage
 * <Fieldset title="Personal Information">
 *   <FormField label="Name">
 *     <Input />
 *   </FormField>
 * </Fieldset>
 *
 * // With description and collapsed by default
 * <Fieldset
 *   title="Advanced Settings"
 *   description="Configure optional advanced parameters"
 *   defaultOpen={false}
 * >
 *   <FormField label="API Key">
 *     <Input type="password" />
 *   </FormField>
 * </Fieldset>
 *
 * // Non-collapsible
 * <Fieldset title="Required Fields" collapsible={false}>
 *   <FormField label="Email" required>
 *     <Input type="email" />
 *   </FormField>
 * </Fieldset>
 * ```
 */
export const Fieldset = forwardRef<HTMLFieldSetElement, FieldsetProps>(
  (
    {
      title,
      description,
      defaultOpen = true,
      open: controlledOpen,
      onOpenChange,
      collapsible = true,
      className,
      children,
      ...props
    },
    ref,
  ) => {
    // Generate unique IDs for ARIA attributes
    const baseId = useId();
    const contentId = `${baseId}-content`;
    const headerId = `${baseId}-header`;

    // Manage open state (supports both controlled and uncontrolled)
    const isControlled = controlledOpen !== undefined;
    const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen);
    const isOpen = isControlled ? controlledOpen : uncontrolledOpen;

    // Ref for content measurement
    const contentRef = useRef<HTMLDivElement>(null);
    const [contentHeight, setContentHeight] = useState<number | "auto">("auto");

    // Measure content height for animation
    useEffect(() => {
      if (!collapsible) return;

      const content = contentRef.current;
      if (!content) return;

      if (isOpen) {
        // Measure actual height when open
        const height = content.scrollHeight;
        setContentHeight(height);

        // After animation completes, set to auto to handle dynamic content
        const timer = setTimeout(() => {
          setContentHeight("auto");
        }, 200); // Match transition duration

        return () => clearTimeout(timer);
      } else {
        // When closing, first set explicit height then animate to 0
        const height = content.scrollHeight;
        setContentHeight(height);

        // Force reflow then set to 0
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            setContentHeight(0);
          });
        });
      }
    }, [isOpen, collapsible]);

    const handleToggle = useCallback(() => {
      if (!collapsible) return;

      const newValue = !isOpen;
      if (!isControlled) {
        setUncontrolledOpen(newValue);
      }
      onOpenChange?.(newValue);
    }, [collapsible, isControlled, isOpen, onOpenChange]);

    const handleKeyDown = useCallback(
      (event: React.KeyboardEvent) => {
        if (!collapsible) return;

        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          handleToggle();
        }
      },
      [collapsible, handleToggle],
    );

    return (
      <fieldset
        ref={ref}
        className={cn(
          "rounded-[var(--radius-lg)]",
          "border border-[var(--color-border)]",
          "bg-[var(--color-card)]",
          className,
        )}
        {...props}
      >
        {/* Legend/Header */}
        <legend className="sr-only">{title}</legend>

        <div
          id={headerId}
          role={collapsible ? "button" : undefined}
          tabIndex={collapsible ? 0 : undefined}
          aria-expanded={collapsible ? isOpen : undefined}
          aria-controls={collapsible ? contentId : undefined}
          onClick={collapsible ? handleToggle : undefined}
          onKeyDown={collapsible ? handleKeyDown : undefined}
          className={cn(
            "flex items-center justify-between",
            "px-4 py-3",
            collapsible && [
              "cursor-pointer",
              "transition-colors duration-150",
              "hover:bg-[var(--color-card-hover)]",
              "focus-visible:outline-none focus-visible:ring-2",
              "focus-visible:ring-[var(--color-accent)] focus-visible:ring-inset",
              "rounded-t-[var(--radius-lg)]",
              !isOpen && "rounded-b-[var(--radius-lg)]",
            ],
          )}
        >
          <div className="flex flex-col gap-0.5">
            <span className="text-sm font-medium text-[var(--color-foreground)]">{title}</span>
            {description && (
              <span className="text-xs text-[var(--color-muted)]">{description}</span>
            )}
          </div>

          {collapsible && <ChevronIcon isOpen={isOpen} />}
        </div>

        {/* Collapsible Content */}
        <div
          id={contentId}
          ref={contentRef}
          role="region"
          aria-labelledby={headerId}
          aria-hidden={collapsible && !isOpen}
          style={{
            height: collapsible ? contentHeight : "auto",
            overflow: collapsible ? "hidden" : undefined,
          }}
          className={cn(
            "transition-[height] duration-200 ease-in-out",
            collapsible && !isOpen && "invisible",
          )}
        >
          <div
            className={cn(
              "px-4 pb-4 pt-2",
              "border-t border-[var(--color-border)]",
              // Fade in/out content for smoother animation
              "transition-opacity duration-150",
              collapsible && !isOpen && "opacity-0",
            )}
          >
            {children}
          </div>
        </div>
      </fieldset>
    );
  },
);

Fieldset.displayName = "Fieldset";

// ============================================================================
// FieldsetGroup Component
// ============================================================================

export interface FieldsetGroupProps extends HTMLAttributes<HTMLDivElement> {
  /** Content to render (typically multiple Fieldset components) */
  children: ReactNode;
}

/**
 * Container component for grouping multiple Fieldset components.
 * Provides consistent spacing between fieldsets.
 *
 * @example
 * ```tsx
 * <FieldsetGroup>
 *   <Fieldset title="Personal Information">
 *     ...
 *   </Fieldset>
 *   <Fieldset title="Address">
 *     ...
 *   </Fieldset>
 * </FieldsetGroup>
 * ```
 */
export const FieldsetGroup = forwardRef<HTMLDivElement, FieldsetGroupProps>(
  ({ className, children, ...props }, ref) => {
    return (
      <div ref={ref} className={cn("space-y-4", className)} {...props}>
        {children}
      </div>
    );
  },
);

FieldsetGroup.displayName = "FieldsetGroup";
