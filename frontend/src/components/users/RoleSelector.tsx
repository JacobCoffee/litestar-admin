"use client";

import { useState, useCallback, useRef, useEffect, useId, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";

// ============================================================================
// Types
// ============================================================================

export interface RoleSelectorProps {
  /** Currently selected roles */
  value: readonly string[];
  /** Callback when selection changes */
  onChange: (roles: string[]) => void;
  /** Available role options */
  options?: readonly string[];
  /** Placeholder text when nothing is selected */
  placeholder?: string;
  /** Whether the selector is disabled */
  disabled?: boolean;
  /** Whether there's an error state */
  error?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// Default role options
const DEFAULT_ROLES = ["admin", "editor", "viewer", "moderator"] as const;

// ============================================================================
// Icons
// ============================================================================

function ChevronDownIcon({ className }: { className?: string }) {
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
      <path d="m6 9 6 6 6-6" />
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
      <path d="M18 6 6 18" />
      <path d="m6 6 12 12" />
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
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function RoleSelector({
  value,
  onChange,
  options = DEFAULT_ROLES,
  placeholder = "Select roles...",
  disabled = false,
  error = false,
  className,
}: RoleSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownId = useId();
  const containerRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return;

    const handleClickOutside = (event: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const toggleOption = useCallback(
    (role: string) => {
      const currentRoles = [...value];
      const index = currentRoles.indexOf(role);
      if (index === -1) {
        currentRoles.push(role);
      } else {
        currentRoles.splice(index, 1);
      }
      onChange(currentRoles);
    },
    [value, onChange],
  );

  const removeRole = useCallback(
    (role: string, e: React.MouseEvent) => {
      e.stopPropagation();
      onChange(value.filter((r) => r !== role));
    },
    [value, onChange],
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLButtonElement>) => {
      if (e.key === "Escape") {
        setIsOpen(false);
      } else if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        if (!disabled) {
          setIsOpen(!isOpen);
        }
      }
    },
    [disabled, isOpen],
  );

  const displayText = value.length === 0 ? placeholder : null;

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-controls={dropdownId}
        aria-haspopup="listbox"
        disabled={disabled}
        className={cn(
          "w-full min-h-[40px] px-3 py-2",
          "flex items-center justify-between gap-2",
          "rounded-[var(--radius-md)]",
          "bg-[var(--color-card)] text-[var(--color-foreground)]",
          "border border-[var(--color-border)]",
          "text-sm text-left",
          "transition-colors duration-150",
          "hover:border-[var(--color-muted)]",
          "focus:border-[var(--color-accent)] focus:ring-1 focus:ring-[var(--color-accent)]",
          "focus:outline-none",
          "disabled:cursor-not-allowed disabled:opacity-50",
          error && "border-[var(--color-error)] focus:border-[var(--color-error)] focus:ring-[var(--color-error)]",
        )}
      >
        <div className="flex flex-wrap gap-1.5 flex-1">
          {displayText ? (
            <span className="text-[var(--color-muted)]">{displayText}</span>
          ) : (
            value.map((role) => (
              <span
                key={role}
                className={cn(
                  "inline-flex items-center gap-1",
                  "h-6 px-2 pr-1",
                  "rounded-[var(--radius-sm)]",
                  "bg-[var(--color-primary)]/10 text-[var(--color-primary)]",
                  "text-xs font-medium",
                )}
              >
                {role}
                <button
                  type="button"
                  onClick={(e) => removeRole(role, e)}
                  className={cn(
                    "p-0.5 rounded-[var(--radius-xs)]",
                    "hover:bg-[var(--color-primary)]/20",
                    "transition-colors duration-150",
                  )}
                  aria-label={`Remove ${role}`}
                  disabled={disabled}
                >
                  <XIcon className="h-3 w-3" />
                </button>
              </span>
            ))
          )}
        </div>
        <ChevronDownIcon
          className={cn(
            "h-4 w-4 shrink-0 text-[var(--color-muted)]",
            "transition-transform duration-150",
            isOpen && "rotate-180",
          )}
        />
      </button>

      {isOpen && !disabled && (
        <div
          id={dropdownId}
          role="listbox"
          aria-multiselectable="true"
          className={cn(
            "absolute z-50 w-full mt-1",
            "max-h-[200px] overflow-auto",
            "rounded-[var(--radius-md)]",
            "border border-[var(--color-border)]",
            "bg-[var(--color-card)]",
            "shadow-lg shadow-black/20",
            "py-1",
          )}
        >
          {options.map((role) => {
            const isSelected = value.includes(role);
            return (
              <button
                key={role}
                type="button"
                role="option"
                aria-selected={isSelected}
                onClick={() => toggleOption(role)}
                className={cn(
                  "w-full px-3 py-2",
                  "flex items-center gap-2",
                  "text-sm text-left",
                  "transition-colors duration-150",
                  "hover:bg-[var(--color-card-hover)]",
                  "focus-visible:outline-none focus-visible:bg-[var(--color-card-hover)]",
                )}
              >
                <span
                  className={cn(
                    "flex h-4 w-4 items-center justify-center shrink-0",
                    "rounded-[var(--radius-sm)]",
                    "border border-[var(--color-border)]",
                    "transition-colors duration-150",
                    isSelected && "bg-[var(--color-primary)] border-[var(--color-primary)]",
                  )}
                >
                  {isSelected && <CheckIcon className="h-3 w-3 text-white" />}
                </span>
                <span className="capitalize">{role}</span>
              </button>
            );
          })}
          {options.length === 0 && (
            <div className="px-3 py-2 text-sm text-[var(--color-muted)]">No roles available</div>
          )}
        </div>
      )}
    </div>
  );
}

RoleSelector.displayName = "RoleSelector";
